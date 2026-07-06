"""ML-based Probability-of-Default model.

Trained at startup on a synthetic population of ~500 MSMEs where ground-truth
default outcomes come from a hidden logistic function of the persona knobs
(see `ml_data.true_default_probability`). The model has to learn to
approximate that hidden ground truth using only the *observable* features
that come out of GST / AA / EPFO / UPI data.

Design choices:

- Feature extraction goes through `Features` — the same dataclass production
  code builds from real `DataPack`s. Training runs each sampled persona
  through the FULL production pipeline (data-pack generation → feature
  extraction), eliminating the old train/serve skew. The analytic shortcut
  `_features_from_persona` is kept behind `production_features=False` for
  fast experimentation.
- PD probabilities are calibrated (Platt/sigmoid via CalibratedClassifierCV;
  isotonic needs more than a few hundred points) and reported with a holdout
  Brier score alongside the AUC.
- Monotonic constraints on every direction-known feature: the booster
  provably cannot learn "more bounces → safer" from sampling noise.
- Explainability: local counterfactual. For each feature we replace it with
  the population median, re-predict, and attribute the PD delta. Top-3 up
  and top-3 down give "drivers" (increase PD) and "supports" (decrease PD).
  Simpler than SHAP, cheap, and matches how a human would reason.
- Model version is a hash of (feature list, constraints, sample count, seed,
  training mode) so downstream consumers can invalidate cached scores if the
  model changes. The trained artifact is persisted under `.model_cache/`
  keyed by that hash — a warm boot loads in milliseconds instead of
  regenerating 500 data packs.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import joblib
import numpy as np
from sklearn.calibration import CalibratedClassifierCV
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import brier_score_loss, roc_auc_score

from .ml_data import SampledMsme, sample_population
from .personas import L_PAISE, Persona
from .scoring.features import Features


# Trained-model cache: keyed by the version hash, so any change to the
# feature list, sample count or training mode retrains instead of loading a
# stale artifact. Gitignored — models are reproducible from the seed.
_CACHE_DIR = Path(__file__).resolve().parent.parent / ".model_cache"


# ─── Canonical feature list ─────────────────────────────────────────────────
# Order matters — the trained model expects this exact layout.


@dataclass(frozen=True)
class FeatureSpec:
    key: str
    label: str
    extract: Callable[[Features], float]
    # Enforced direction of effect on PD: +1 = more of this can only raise
    # PD, -1 = more can only lower it, 0 = unconstrained. Passed to the
    # gradient booster as `monotonic_cst`, so the model provably cannot
    # learn e.g. "more bounces is safer" from sampling noise — a property a
    # lending-model validator can sign off on.
    monotonic: int = 0


FEATURE_SPECS: list[FeatureSpec] = [
    FeatureSpec("turnover_lakhs", "Monthly turnover",
                lambda f: f.avg_monthly_turnover_paise / L_PAISE, monotonic=-1),
    FeatureSpec("turnover_growth", "Turnover growth (YoY)",
                lambda f: f.turnover_growth_pct if f.turnover_growth_pct is not None else 0.0,
                monotonic=-1),
    FeatureSpec("turnover_cov", "Turnover volatility",
                lambda f: f.turnover_cov, monotonic=1),
    FeatureSpec("gst_on_time_pct", "GST filing timeliness",
                lambda f: f.gst_filing_on_time_pct, monotonic=-1),
    FeatureSpec("gst_avg_delay_days", "Avg GST filing delay",
                lambda f: f.gst_avg_delay_days, monotonic=1),
    FeatureSpec("epfo_active", "EPFO coverage",
                lambda f: 1.0 if f.epfo_active else 0.0, monotonic=-1),
    FeatureSpec("epfo_on_time_pct", "EPFO deposit regularity",
                lambda f: f.epfo_filing_on_time_pct or 0.0, monotonic=-1),
    FeatureSpec("headcount_trend", "Headcount trend",
                lambda f: f.headcount_trend_pct if f.headcount_trend_pct is not None else 0.0,
                monotonic=-1),
    FeatureSpec("headcount", "Employee count",
                lambda f: float(f.latest_headcount), monotonic=0),
    FeatureSpec("inflow_outflow_ratio", "Inflow/outflow ratio",
                lambda f: f.inflow_outflow_ratio, monotonic=-1),
    FeatureSpec("monthly_surplus_lakhs", "Monthly cash surplus",
                lambda f: f.monthly_surplus_paise / L_PAISE, monotonic=-1),
    FeatureSpec("bank_balance_lakhs", "Avg bank balance",
                lambda f: f.avg_daily_balance_paise / L_PAISE, monotonic=-1),
    FeatureSpec("bounce_count", "Bounces / returns (12m)",
                lambda f: float(f.bounce_count), monotonic=1),
    FeatureSpec("emi_lakhs", "Monthly EMI",
                lambda f: f.monthly_emi_paise / L_PAISE, monotonic=1),
    FeatureSpec("dscr_proxy", "Debt-service coverage",
                lambda f: f.dscr_proxy if f.dscr_proxy is not None else 5.0, monotonic=-1),
    FeatureSpec("upi_inflow_lakhs", "UPI monthly inflow",
                lambda f: f.upi_monthly_inflow_paise / L_PAISE, monotonic=-1),
    FeatureSpec("upi_payers", "UPI unique payers",
                lambda f: float(f.upi_unique_payers), monotonic=-1),
    FeatureSpec("upi_p2m_share", "UPI P2M share",
                lambda f: f.upi_p2m_share, monotonic=-1),
]


def feature_vector(features: Features) -> np.ndarray:
    return np.array([spec.extract(features) for spec in FEATURE_SPECS], dtype=np.float64)


# ─── Fast training-side features (skip bank txn generation) ─────────────────


def _features_from_persona(p: Persona) -> Features:
    """Approximate a `Features` instance directly from persona knobs.

    Production features come from AA transaction streams. During training we
    generate hundreds of samples and don't want to pay the cost of building
    12 months of txns per sample. We instead compute the expected values of
    the features analytically from the same knobs the txn generator uses,
    which keeps training features distributionally close to production ones.

    Known train/serve skew: these are expectations, not realizations — e.g.
    turnover_cov is approximated as seasonality + noise floor, and GST history
    is fixed at 24 months. Scoring-time features come from the full generated
    series, so individual explanations can occasionally rank a feature oddly
    (a production concern to solve by training on the full pipeline).
    """
    turnover_paise = int(p.monthly_turnover_lakhs * L_PAISE)
    inflow = turnover_paise
    outflow = int(turnover_paise / p.inflow_outflow_ratio)
    emi = int(p.monthly_emi_lakhs * L_PAISE)
    surplus = inflow - outflow
    dscr = ((surplus + emi) / emi) if emi > 0 else None
    epfo_pct = p.salary_regularity if p.epfo_active else None
    # simplified headcount trend from growth
    trend = p.growth_yoy * 0.7 if p.epfo_active else None
    upi_inflow = int(p.upi_inflow_lakhs * L_PAISE)
    balance = int(p.avg_bank_balance_lakhs * L_PAISE)

    return Features(
        months_of_gst_history=24,
        avg_monthly_turnover_paise=turnover_paise,
        latest_3m_turnover_paise=turnover_paise,
        oldest_3m_turnover_paise=int(turnover_paise / (1 + p.growth_yoy)),
        turnover_growth_pct=p.growth_yoy,
        turnover_cov=p.seasonality_amplitude + 0.15,
        gst_filing_on_time_pct=p.filing_discipline,
        gst_avg_delay_days=(1 - p.filing_discipline) * 30,
        epfo_filing_on_time_pct=epfo_pct,
        gst_on_time_trend_pct=0.0,
        monthly_inflow_paise=inflow,
        monthly_outflow_paise=outflow,
        inflow_outflow_ratio=p.inflow_outflow_ratio,
        avg_daily_balance_paise=balance,
        min_balance_paise=int(balance * (1 - p.balance_volatility)),
        bounce_count=p.bounce_incidents_12m,
        monthly_emi_paise=emi,
        balance_trend_pct=p.growth_yoy * 0.5,
        emi_trend_pct=0.0 if emi > 0 else None,
        dscr_proxy=dscr,
        monthly_surplus_paise=surplus,
        upi_monthly_inflow_paise=upi_inflow,
        upi_unique_payers=p.upi_unique_payers,
        upi_p2m_share=p.upi_p2m_share,
        upi_growth_pct=p.upi_growth_yoy,
        epfo_active=p.epfo_active,
        latest_headcount=p.employee_count if p.epfo_active else 0,
        headcount_trend_pct=trend,
        monthly_wage_bill_paise=int(p.employee_count * p.monthly_wage_per_employee_lakhs * L_PAISE),
    )


def _features_via_production_pipeline(pop: list[SampledMsme]) -> list[Features]:
    """Run each sampled persona through the real data-pack → features path.

    This is exactly what serving does, so training and scoring see identically
    distributed features (no skew). Personas are registered only for the
    duration of their pack build so the ML population never leaks into the
    demo registry.
    """
    from . import personas as personas_mod
    from .scoring.features import extract_features

    out: list[Features] = []
    for s in pop:
        p = s.persona
        already = p.gstin in personas_mod.PERSONAS_BY_GSTIN
        if not already:
            personas_mod.PERSONAS_BY_GSTIN[p.gstin] = p
        try:
            pack = personas_mod.build_data_pack(p.gstin)
            assert pack is not None
            out.append(extract_features(pack))
        finally:
            if not already:
                del personas_mod.PERSONAS_BY_GSTIN[p.gstin]
    return out


# ─── The model ──────────────────────────────────────────────────────────────


@dataclass
class MlDriver:
    feature_key: str
    feature_label: str
    contribution: float  # signed PD delta vs population median
    detail: str


@dataclass
class MlPrediction:
    probability_of_default: float
    confidence: str  # "high" / "medium" / "low"
    drivers: list[MlDriver]   # push PD up, sorted worst first
    supports: list[MlDriver]  # pull PD down, sorted best first
    model_version: str


class PdModel:
    """Trained probability-of-default estimator with local explanations."""

    def __init__(self) -> None:
        self._clf: CalibratedClassifierCV | None = None
        self._medians: np.ndarray | None = None
        self._version: str = ""
        self._train_pd_std: float = 0.0
        self._train_pd_mean: float = 0.0
        self._trained_on_n: int = 0
        self._holdout_auc: float | None = None
        self._holdout_brier: float | None = None

    @staticmethod
    def _make_clf(seed: int) -> CalibratedClassifierCV:
        # HistGradientBoosting is fast, handles NaNs, and stays shallow so it
        # doesn't memorize a few hundred synthetic points. `monotonic_cst`
        # enforces the sign of every direction-known feature. The sigmoid
        # calibration wrapper turns raw booster scores into usable
        # probabilities (isotonic would overfit at n=500).
        base = HistGradientBoostingClassifier(
            max_iter=180,
            max_depth=4,
            learning_rate=0.05,
            l2_regularization=0.1,
            random_state=seed,
            monotonic_cst=[s.monotonic for s in FEATURE_SPECS],
        )
        return CalibratedClassifierCV(base, method="sigmoid", cv=5)

    def train(
        self,
        n_samples: int = 500,
        seed: int = 42,
        *,
        production_features: bool = True,
    ) -> None:
        pop: list[SampledMsme] = sample_population(n_samples, seed)
        y = np.array([1 if s.defaulted else 0 for s in pop], dtype=np.int32)

        # Version first: it keys the persisted artifact, so a cached model can
        # be loaded before paying for 500 data-pack builds.
        mode = "prod" if production_features else "fast"
        sig = (
            f"{[(s.key, s.monotonic) for s in FEATURE_SPECS]}"
            f"|{n_samples}|{seed}|{mode}|{int(y.sum())}|cal-sigmoid"
        )
        self._version = "m-" + hashlib.sha256(sig.encode()).hexdigest()[:8]
        if self._load_cached():
            return

        if production_features:
            feats = _features_via_production_pipeline(pop)
        else:
            feats = [_features_from_persona(s.persona) for s in pop]
        X = np.stack([feature_vector(f) for f in feats])

        # Holdout evaluation: fit on 80%, report AUC (rank quality) and Brier
        # (probability quality) on the held-out 20%, then refit on the full
        # population for serving.
        idx = np.random.default_rng(seed).permutation(n_samples)
        cut = max(1, int(n_samples * 0.8))
        tr, te = idx[:cut], idx[cut:]
        self._holdout_auc = None
        self._holdout_brier = None
        if len(te) > 0 and len(np.unique(y[te])) == 2:
            eval_clf = self._make_clf(seed)
            eval_clf.fit(X[tr], y[tr])
            proba_te = eval_clf.predict_proba(X[te])[:, 1]
            self._holdout_auc = float(roc_auc_score(y[te], proba_te))
            self._holdout_brier = float(brier_score_loss(y[te], proba_te))

        self._clf = self._make_clf(seed)
        self._clf.fit(X, y)
        self._trained_on_n = n_samples

        self._medians = np.median(X, axis=0)

        # Store the training PD distribution for the confidence heuristic
        probs = self._clf.predict_proba(X)[:, 1]
        self._train_pd_mean = float(probs.mean())
        self._train_pd_std = float(probs.std())

        self._save_cached()

    # ── Persistence: warm boots load instead of regenerating 500 packs ─────

    def _cache_path(self) -> Path:
        return _CACHE_DIR / f"{self._version}.joblib"

    def _load_cached(self) -> bool:
        path = self._cache_path()
        if not path.exists():
            return False
        try:
            art = joblib.load(path)
        except Exception:
            return False  # corrupt/incompatible artifact → retrain
        self._clf = art["clf"]
        self._medians = art["medians"]
        self._train_pd_mean = art["pd_mean"]
        self._train_pd_std = art["pd_std"]
        self._trained_on_n = art["n"]
        self._holdout_auc = art["auc"]
        self._holdout_brier = art["brier"]
        return True

    def _save_cached(self) -> None:
        try:
            _CACHE_DIR.mkdir(parents=True, exist_ok=True)
            joblib.dump({
                "clf": self._clf,
                "medians": self._medians,
                "pd_mean": self._train_pd_mean,
                "pd_std": self._train_pd_std,
                "n": self._trained_on_n,
                "auc": self._holdout_auc,
                "brier": self._holdout_brier,
            }, self._cache_path())
        except Exception:
            pass  # persistence is an optimization, never a boot blocker

    def _predict_proba(self, x: np.ndarray) -> float:
        assert self._clf is not None
        return float(self._clf.predict_proba(x.reshape(1, -1))[0, 1])

    def predict(self, features: Features) -> MlPrediction:
        if self._clf is None or self._medians is None:
            raise RuntimeError("PdModel is untrained")

        x = feature_vector(features)
        base_pd = self._predict_proba(x)

        # Counterfactual explanation: replace each feature with population median
        contributions: list[MlDriver] = []
        for i, spec in enumerate(FEATURE_SPECS):
            x_cf = x.copy()
            x_cf[i] = self._medians[i]
            cf_pd = self._predict_proba(x_cf)
            delta = base_pd - cf_pd
            actual = spec.extract(features)
            contributions.append(MlDriver(
                feature_key=spec.key,
                feature_label=spec.label,
                contribution=delta,
                detail=_fmt_feature_value(spec.key, actual),
            ))

        contributions.sort(key=lambda d: d.contribution, reverse=True)
        drivers = [d for d in contributions if d.contribution > 0.005][:3]
        supports = sorted(
            [d for d in contributions if d.contribution < -0.005],
            key=lambda d: d.contribution,
        )[:3]

        return MlPrediction(
            probability_of_default=base_pd,
            confidence=_confidence(base_pd, self._train_pd_mean, self._train_pd_std),
            drivers=drivers,
            supports=supports,
            model_version=self._version,
        )

    @property
    def version(self) -> str:
        return self._version

    @property
    def trained_on_n(self) -> int:
        return self._trained_on_n

    @property
    def holdout_auc(self) -> float | None:
        return self._holdout_auc

    @property
    def holdout_brier(self) -> float | None:
        return self._holdout_brier


def _confidence(pd: float, mean: float, std: float) -> str:
    """Loose confidence heuristic: how "typical" is this PD?"""
    z = abs(pd - mean) / max(std, 0.01)
    if pd < 0.05 or pd > 0.60:
        return "high"    # extreme predictions the model is confident about
    if z > 2.0:
        return "low"     # far outside the training PD distribution
    return "medium"


def _fmt_feature_value(key: str, val: float) -> str:
    if "pct" in key or "share" in key:
        return f"{val * 100:.1f}%"
    if "growth" in key or "trend" in key:
        return f"{val * 100:+.1f}%"
    if "lakhs" in key:
        return f"₹{val:.1f}L"
    if key == "bounce_count" or key == "headcount" or key == "upi_payers":
        return f"{int(val)}"
    if key == "dscr_proxy":
        return f"{val:.2f}×"
    if key == "gst_avg_delay_days":
        return f"{val:.0f} days"
    if key == "epfo_active":
        return "yes" if val > 0.5 else "no"
    return f"{val:.2f}"


# ─── Singleton wiring ───────────────────────────────────────────────────────

import threading

_MODEL: PdModel | None = None
_MODEL_LOCK = threading.Lock()


def get_model() -> PdModel:
    """Lazily train (or load) the singleton model. Lock-guarded so the
    background warmup thread and an early request can't double-train."""
    global _MODEL
    if _MODEL is None:
        with _MODEL_LOCK:
            if _MODEL is None:
                model = PdModel()
                model.train()
                _MODEL = model
    return _MODEL
