import { Link, Route, Routes, useLocation } from "react-router-dom";
import LandingPage from "./pages/Landing";
import ConsentPage from "./pages/Consent";
import HealthCardPage from "./pages/HealthCard";

export default function App() {
  return (
    <div className="min-h-screen flex flex-col">
      <TopBar />
      <main className="flex-1">
        <Routes>
          <Route path="/" element={<LandingPage />} />
          <Route path="/consent/:gstin" element={<ConsentPage />} />
          <Route path="/msme/:gstin" element={<HealthCardPage />} />
        </Routes>
      </main>
      <Footer />
    </div>
  );
}

function TopBar() {
  const loc = useLocation();
  const isHome = loc.pathname === "/";
  return (
    <header className="border-b border-ink-100 bg-white/70 backdrop-blur">
      <div className="mx-auto max-w-7xl px-6 py-4 flex items-center justify-between">
        <Link to="/" className="flex items-center gap-3 group">
          <Logo />
          <div>
            <div className="text-sm font-semibold tracking-tight text-ink-900 group-hover:text-brand-600 transition">
              MSME Financial Health Card
            </div>
            <div className="text-[11px] text-ink-500 -mt-0.5">
              ULI · OCEN · AA · GST · UPI · EPFO
            </div>
          </div>
        </Link>
        <div className="flex items-center gap-3 text-xs text-ink-500">
          {!isHome && (
            <Link to="/" className="btn-ghost !py-1 !px-2 text-xs">
              ← Back to portfolio
            </Link>
          )}
          <span className="hidden md:inline">Demo build · Track 03</span>
        </div>
      </div>
    </header>
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
