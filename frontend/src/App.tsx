import { Link, NavLink, Route, Routes, useLocation } from "react-router-dom";
import clsx from "clsx";
import LandingPage from "./pages/Landing";
import ConsentPage from "./pages/Consent";
import HealthCardPage from "./pages/HealthCard";
import PortfolioPage from "./pages/Portfolio";
import ImpactPage from "./pages/Impact";
import EcosystemPage from "./pages/Ecosystem";
import SanctionLetterPage from "./pages/SanctionLetter";
import ConsentLogPage from "./pages/ConsentLog";
import { WhatsAppToaster } from "./components/WhatsAppToaster";
import { LangProvider, useLang } from "./i18n";

export default function App() {
  return (
    <LangProvider>
      <div className="min-h-screen flex flex-col">
        <TopBar />
        <main className="flex-1">
          <Routes>
            <Route path="/" element={<LandingPage />} />
            <Route path="/portfolio" element={<PortfolioPage />} />
            <Route path="/impact" element={<ImpactPage />} />
            <Route path="/ecosystem" element={<EcosystemPage />} />
            <Route path="/consent-log" element={<ConsentLogPage />} />
            <Route path="/applications/:applicationId" element={<SanctionLetterPage />} />
            <Route path="/consent/:gstin" element={<ConsentPage />} />
            <Route path="/msme/:gstin" element={<HealthCardPage />} />
          </Routes>
        </main>
        <Footer />
        <WhatsAppToaster />
      </div>
    </LangProvider>
  );
}

function TopBar() {
  const loc = useLocation();
  const showBack = loc.pathname.startsWith("/consent") || loc.pathname.startsWith("/msme/");
  return (
    <header className="border-b border-ink-100 bg-white/70 backdrop-blur">
      <div className="mx-auto max-w-7xl px-6 py-4 flex items-center justify-between gap-4">
        <Link to="/" className="flex items-center gap-3 group shrink-0">
          <Logo />
          <div>
            <div className="text-sm font-semibold tracking-tight text-ink-900 group-hover:text-brand-600 transition">
              MSME Financial Health Card
            </div>
            <div className="text-[11px] text-ink-500 -mt-0.5">
              AA consent-first · ULI/OCEN-ready · GST · UPI · EPFO
            </div>
          </div>
        </Link>
        <NavBar />
        <div className="flex-1" />
        <div className="flex items-center gap-3 text-xs text-ink-500">
          <LangSwitch />
          {showBack && (
            <Link to="/portfolio" className="btn-ghost !py-1 !px-2 text-xs">
              ← Portfolio
            </Link>
          )}
        </div>
      </div>
    </header>
  );
}

function NavBar() {
  const { t } = useLang();
  return (
    <nav className="flex items-center gap-1 rounded-xl bg-ink-50/70 p-1 text-xs">
      <TabLink to="/" label={t("Onboarding")} end />
      <TabLink to="/portfolio" label={t("Portfolio")} />
      <TabLink to="/impact" label={t("Impact")} />
      <TabLink to="/ecosystem" label={t("ULI/OCEN")} />
      <TabLink to="/consent-log" label={t("Consent log")} />
    </nav>
  );
}

function LangSwitch() {
  const { lang, setLang } = useLang();
  return (
    <div className="flex items-center gap-1 rounded-lg border border-ink-200 bg-white p-0.5 text-[11px]">
      {(["en", "hi"] as const).map((k) => (
        <button
          key={k}
          onClick={() => setLang(k)}
          className={clsx(
            "px-2 py-0.5 rounded-md transition",
            lang === k ? "bg-brand-600 text-white" : "text-ink-500 hover:text-ink-800",
          )}
        >
          {k === "en" ? "EN" : "हिं"}
        </button>
      ))}
    </div>
  );
}

function TabLink({ to, label, end }: { to: string; label: string; end?: boolean }) {
  return (
    <NavLink
      to={to}
      end={end}
      className={({ isActive }) =>
        clsx(
          "px-3 py-1.5 rounded-lg transition",
          isActive
            ? "bg-white shadow-sm text-ink-900 font-medium"
            : "text-ink-500 hover:text-ink-800",
        )
      }
    >
      {label}
    </NavLink>
  );
}

function Footer() {
  return (
    <footer className="border-t border-ink-100 bg-white/60 mt-16">
      <div className="mx-auto max-w-7xl px-6 py-6 text-xs text-ink-500 flex flex-wrap items-center justify-between gap-2">
        <span>
          Built for the Financial Inclusion / Digital Lending track.
          Synthetic data — no real MSMEs used.
        </span>
        <span>Advisory scoring only. Final decision rests with the underwriter.</span>
      </div>
    </footer>
  );
}

function Logo() {
  return (
    <div className="relative h-9 w-9 rounded-xl bg-gradient-to-br from-brand-500 to-brand-700 grid place-items-center shadow-sm">
      <svg viewBox="0 0 24 24" className="h-5 w-5 text-white" fill="none">
        <path
          d="M4 15l4-6 4 3 3-5 5 8"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
        <circle cx="20" cy="6" r="1.5" fill="currentColor" />
      </svg>
    </div>
  );
}
