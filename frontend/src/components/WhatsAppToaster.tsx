import { useEffect, useState } from "react";
import clsx from "clsx";

type Tone = "good" | "warn" | "bad" | "info";

interface Toast {
  id: number;
  title: string;
  body: string;
  tone: Tone;
}

type Listener = (toast: Toast) => void;

let listeners: Listener[] = [];
let nextId = 1;

/**
 * Fire a WhatsApp-styled toast bubble in the bottom-right corner. Used at
 * key demo events (consent granted, sanction issued, decline) to simulate the
 * borrower-side WhatsApp notification a real deployment would push.
 */
export function showToast(t: Omit<Toast, "id">): void {
  const toast: Toast = { ...t, id: nextId++ };
  for (const l of listeners) l(toast);
}

export function WhatsAppToaster() {
  const [items, setItems] = useState<Toast[]>([]);

  useEffect(() => {
    const listener: Listener = (t) => {
      setItems((prev) => [...prev, t]);
      // Auto-dismiss after 6s
      setTimeout(() => {
        setItems((prev) => prev.filter((x) => x.id !== t.id));
      }, 6000);
    };
    listeners.push(listener);
    return () => {
      listeners = listeners.filter((l) => l !== listener);
    };
  }, []);

  if (items.length === 0) return null;

  return (
    <div className="fixed bottom-4 right-4 z-50 flex flex-col gap-2 max-w-xs pointer-events-none print:hidden">
      {items.map((t) => (
        <div
          key={t.id}
          className={clsx(
            "pointer-events-auto rounded-2xl shadow-pop border overflow-hidden animate-[slidein_240ms_ease-out]",
            "bg-white",
          )}
        >
          <div className="flex items-start gap-2.5 p-3">
            <WhatsAppGlyph />
            <div className="min-w-0">
              <div className="flex items-baseline gap-1.5">
                <span className="text-[11px] font-semibold text-emerald-700">
                  IDBI Bank
                </span>
                <span className="text-[10px] text-ink-400">via WhatsApp</span>
              </div>
              <div className={clsx("text-sm font-semibold text-ink-900 mt-0.5", toneAccent(t.tone))}>
                {t.title}
              </div>
              <div className="text-xs text-ink-700 mt-0.5 leading-snug">
                {t.body}
              </div>
            </div>
          </div>
        </div>
      ))}
      <style>{`
        @keyframes slidein {
          from { transform: translateY(12px); opacity: 0 }
          to { transform: translateY(0); opacity: 1 }
        }
      `}</style>
    </div>
  );
}

function toneAccent(t: Tone): string {
  switch (t) {
    case "good":
      return "text-brand-700";
    case "warn":
      return "text-amber-700";
    case "bad":
      return "text-red-700";
    default:
      return "text-ink-900";
  }
}

function WhatsAppGlyph() {
  return (
    <div className="h-8 w-8 rounded-full grid place-items-center shrink-0"
         style={{ background: "#25D366" }}>
      <svg viewBox="0 0 24 24" className="h-5 w-5 text-white" fill="currentColor">
        <path d="M12.04 2C6.58 2 2.16 6.42 2.16 11.88c0 1.75.46 3.47 1.34 4.98L2 22l5.31-1.39c1.46.79 3.1 1.21 4.72 1.21h.01c5.46 0 9.88-4.42 9.88-9.88C21.92 6.44 17.5 2 12.04 2zm5.75 14.14c-.24.67-1.4 1.28-1.95 1.36-.5.07-1.13.1-1.82-.11-.42-.13-.96-.31-1.65-.61-2.9-1.25-4.79-4.17-4.94-4.36-.14-.19-1.18-1.57-1.18-3 0-1.42.75-2.13 1.02-2.42.27-.29.58-.36.77-.36s.39.01.55.02c.18 0 .42-.07.66.51.24.58.82 2.01.9 2.15.07.14.12.3.02.49-.1.19-.14.31-.29.48-.14.17-.31.38-.44.51-.14.14-.29.3-.13.59.16.29.72 1.19 1.55 1.93 1.07.96 1.98 1.26 2.27 1.4.29.14.46.12.63-.07.17-.19.72-.84.91-1.13.19-.29.39-.24.65-.14.26.1 1.65.78 1.93.92.29.14.48.22.55.34.07.11.07.66-.17 1.33z" />
      </svg>
    </div>
  );
}
