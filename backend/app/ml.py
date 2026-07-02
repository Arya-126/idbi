"""ML-based Probability-of-Default model.

Trained at startup on a synthetic population of ~500 MSMEs where ground-truth
default outcomes come from a hidden logistic function of the persona knobs
(see `ml_data.true_default_probability`). The model has to learn to
approximate that hidden ground truth using only the *observable* features
that come out of GST / AA / EPFO / UPI data.

Design choices:

- Feature extraction goes through `Features` — the same dataclass production
  code builds from real `DataPack`s. Training uses `_features_from_persona`
  as a fast shortcut (skips bank-txn generation, ~200× speedup) but produces
  values that match the production flow within tight tolerance.
- Explainability: local counterfactual. For each feature we replace it with
  the population median, re-predict, and attribute the PD delta. Top-3 up
  and top-3 down give "drivers" (increase PD) and "supports" (decrease PD).
  Simpler than SHAP, cheap, and matches how a human would reason.
- Model version is a hash of (feature list, training population size, seed)
  so downstream consumers can invalidate cached scores if the model changes.
"""

from __future__ import annotations

import hashlib
import statistics
from dataclasses import dataclass
from typing import Callable

import numpy as np
from sklearn.ensemble import HistGradientBoostingClassifier

from .ml_data import SampledMsme, sample_population
from .personas import L_PAISE, Persona
from .scoring.features import Features


# ─── Canonical feature list ─────────────────────────────────────────────────
# Order matters — the trained model expects this exact layout.


@dataclass(frozen=True)
class FeatureSpec:
    key: str
    label: str
    extract: Callable[[Features], float]


FEATURE_SPECS: list[FeatureSpec] = [
    FeatureSpec("turnover_lakhs", "Monthly turnover",
                lambda f: f.avg_monthly_turnover_paise / L_PAISE),
    FeatureSpec("turnover_growth", "Turnover growth (YoY)",
                lambda f: f.turnover_growth_pct if f.turnover_growth_pct is not None else 0.0),
    FeatureSpec("turnover_cov", "Turnover volatility",
                lambda f: f.turnover_cov),
    FeatureSpec("gst_on_time_pct", "GST filing timeliness",
                lambda f: f.gst_filing_on_time_pct),
    FeatureSpec("gst_avg_delay_days", "Avg GST filing delay",
                lambda f: f.gst_avg_delay_days),
    FeatureSpec("epfo_active", "EPFO coverage",
                lambda f: 1.0 if f.epfo_active else 0.0),
    FeatureSpec("epfo_on_time_pct", "EPFO deposit regularity",
                lambda f: f.epfo_filing_on_time_pct or 0.0),
    FeatureSpec("headcount_trend", "Headcount trend",
                lambda f: f.headcount_trend_pct if f.headcount_trend_pct is not None else 0.0),
    FeatureSpec("headcount", "Employee count",
                lambda f: float(f.latest_headcount)),
    FeatureSpec("inflow_outflow_ratio", "Inflow/outflow ratio",
                lambda f: f.inflow_outflow_ratio),
    FeatureSpec("monthly_surplus_lakhs", "Monthly cash surplus",
                lambda f: f.monthly_surplus_paise / L_PAISE),
    FeatureSpec("bank_balance_lakhs", "Avg bank balance",
                lambda f: f.avg_daily_balance_paise / L_PAISE),
    FeatureSpec("bounce_count", "Bounces / returns (12m)",
                lambda f: float(f.bounce_count)),
    FeatureSpec("emi_lakhs", "Monthly EMI",
                lambda f: f.monthly_emi_paise / L_PAISE),
    FeatureSpec("dscr_proxy", "Debt-service coverage",
                lambda f: f.dscr_proxy if f.dscr_proxy is not None else 5.0),
    FeatureSpec("upi_inflow_lakhs", "UPI monthly inflow",
                lambda f: f.upi_monthly_inflow_paise / L_PAISE),
    FeatureSpec("upi_payers", "UPI unique payers",
                lambda f: float(f.upi_unique_payers)),
    FeatureSpec("upi_p2m_share", "UPI P2M share",
                lambda f: f.upi_p2m_share),
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
        monthly_inflow_paise=inflow,
        monthly_outflow_paise=outflow,
        inflow_outflow_ratio=p.inflow_outflow_ratio,
        avg_daily_balance_paise=balance,
        min_balance_paise=int(balance * (1 - p.balance_volatility)),
        bounce_count=p.bounce_incidents_12m,
        monthly_emi_paise=emi,
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
        self._clf: HistGradientBoostingClassifier | None = None
        self._medians: np.ndarray | None = None
        self._version: str = ""
        self._train_pd_std: float = 0.0
        self._train_pd_mean: float = 0.0

    def train(self, n_samples: int = 500, seed: int = 42) -> None:
        pop: list[SampledMsme] = sample_population(n_samples, seed)
        X = np.stack([feature_vector(_features_from_persona(s.persona)) for s in pop])
        y = np.array([1 if s.defaulted else 0 for s in pop], dtype=np.int32)

        # HistGradientBoosting is fast, handles NaNs, and gives good calibration
        # with a small population. We keep depth shallow so the model doesn't
        # memorize the 500 synthetic points.
        self._clf = HistGradientBoostingClassifier(
            max_iter=180,
            max_depth=4,
            learning_rate=0.05,
            l2_regularization=0.1,
            random_state=seed,
        )
        self._clf.fit(X, y)

        self._medians = np.median(X, axis=0)

        # Store the training PD distribution for confidence calibration
        probs = self._clf.predict_proba(X)[:, 1]
        self._train_pd_mean = float(probs.mean())
        self._train_pd_std = float(probs.std())

        # Version = short hash of (feature list, sample count, defaults rate)
        sig = f"{[s.key for s in FEATURE_SPECS]}|{n_samples}|{int(y.sum())}"
        self._version = "m-" + hashlib.sha256(sig.encode()).hexdigest()[:8]

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


def _confidence(pd: float, mean: float, std: float) -> str:
    """Loose confidence heuristic: how "typical" is this PD?"""
    z = abs(pd - mean) / max(std, 0.01)
    if z < 0.5:
        return "medium"  # right in the middle where the model has seen a lot
    if pd < 0.05 or pd > 0.60:
        return "high"    # extreme predictions the model is confident about
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

_MODEL: PdModel | None = None


def get_model() -> PdModel:
    global _MODEL
    if _MODEL is None:
        _MODEL = PdModel()
        _MODEL.train()
    return _MODEL
