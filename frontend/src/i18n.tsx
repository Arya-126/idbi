import { createContext, useContext, useEffect, useState } from "react";

export type Lang = "en" | "hi";

/**
 * Minimal i18n dictionary — hand-curated for the borrower-facing bits and
 * the top-line nav. Anything not covered by a key just falls back to the
 * English source string.
 *
 * Financial inclusion cares about vernacular access; a full-blown i18n
 * framework was out of scope for the hackathon but the mechanism is here.
 */
const DICT: Record<Lang, Record<string, string>> = {
  en: {},
  hi: {
    Onboarding: "ऑनबोर्डिंग",
    Portfolio: "पोर्टफोलियो",
    Impact: "प्रभाव",
    "ULI/OCEN": "यूएलआई/ओसीईएन",
    "Consent log": "सहमति लॉग",
    "Grant consent to score this MSME": "इस MSME को स्कोर करने के लिए सहमति दें",
    "Grant consent & fetch data": "सहमति दें और डेटा प्राप्त करें",
    "Requesting consent…": "सहमति का अनुरोध…",
    "Consent granted ✓": "सहमति दी गई ✓",
    "Pulling data…": "डेटा प्राप्त हो रहा है…",
    "Opening health card…": "हेल्थ कार्ड खुल रहा है…",
    "Credit officer view": "क्रेडिट ऑफिसर दृश्य",
    "Borrower view": "उधारकर्ता दृश्य",
    "Apply for credit →": "क्रेडिट के लिए आवेदन करें →",
    "Improve your score": "अपना स्कोर सुधारें",
    "What this means for your business": "आपके व्यवसाय के लिए इसका क्या मतलब है",
    "Lending recommendation": "उधार की सिफारिश",
    "Approve": "स्वीकृत",
    "Refer to Underwriter": "अंडरराइटर के पास भेजें",
    "Decline": "अस्वीकृत",
    "Sanction issued 🎉": "स्वीकृति जारी 🎉",
    "Sent to underwriter": "अंडरराइटर के पास भेजा गया",
    "Application declined": "आवेदन अस्वीकृत",
  },
};

interface LangCtx {
  lang: Lang;
  setLang: (l: Lang) => void;
  t: (s: string) => string;
}

const Ctx = createContext<LangCtx | null>(null);

export function LangProvider({ children }: { children: React.ReactNode }) {
  const [lang, setLang] = useState<Lang>(() => {
    const saved = localStorage.getItem("lang");
    return saved === "hi" ? "hi" : "en";
  });
  useEffect(() => {
    localStorage.setItem("lang", lang);
    document.documentElement.lang = lang;
  }, [lang]);

  const t = (s: string): string => DICT[lang][s] ?? s;

  return <Ctx.Provider value={{ lang, setLang, t }}>{children}</Ctx.Provider>;
}

export function useLang(): LangCtx {
  const c = useContext(Ctx);
  if (!c) throw new Error("useLang must be inside LangProvider");
  return c;
}
