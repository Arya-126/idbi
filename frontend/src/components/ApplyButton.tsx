import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { api, storedConsent } from "../api";
import { showToast } from "./WhatsAppToaster";

export default function ApplyButton({
  gstin,
  disabled,
}: {
  gstin: string;
  disabled?: boolean;
}) {
  const [busy, setBusy] = useState(false);
  const navigate = useNavigate();

  async function apply() {
    setBusy(true);
    try {
      const consent = storedConsent(gstin);
      const app = await api.applyForCredit(gstin, consent);
      if (app.status === "SANCTIONED") {
        showToast({
          title: "Sanction issued 🎉",
          body: `${app.trade_name}: ₹${(app.amount_paise / 1_00_000_00).toFixed(1)}L · ${app.tenor_months} months.`,
          tone: "good",
        });
        navigate(`/applications/${app.application_id}`);
      } else if (app.status === "UNDER_REVIEW") {
        showToast({
          title: "Sent to underwriter",
          body: `${app.trade_name}: your application is under review.`,
          tone: "warn",
        });
        navigate(`/applications/${app.application_id}`);
      } else {
        showToast({
          title: "Application declined",
          body: app.rationale,
          tone: "bad",
        });
      }
    } catch (e) {
      showToast({
        title: "Couldn't submit application",
        body: String(e),
        tone: "bad",
      });
    } finally {
      setBusy(false);
    }
  }

  return (
    <button
      onClick={apply}
      disabled={busy || disabled}
      className="btn-primary w-full justify-center mt-4 disabled:opacity-60 disabled:cursor-not-allowed"
    >
      {busy ? "Submitting application…" : disabled ? "Ineligible for auto-apply" : "Apply for credit →"}
    </button>
  );
}
