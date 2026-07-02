export function paiseToInr(p: number): string {
  const rupees = p / 100;
  if (Math.abs(rupees) >= 1_00_00_000) {
    return `₹${(rupees / 1_00_00_000).toFixed(2)} Cr`;
  }
  if (Math.abs(rupees) >= 1_00_000) {
    return `₹${(rupees / 1_00_000).toFixed(1)} L`;
  }
  if (Math.abs(rupees) >= 1000) {
    return `₹${(rupees / 1000).toFixed(1)}K`;
  }
  return `₹${rupees.toFixed(0)}`;
}

export function bandColor(band: string): string {
  switch (band) {
    case "A":
      return "text-brand-700 bg-brand-100 border-brand-200";
    case "B":
      return "text-emerald-800 bg-emerald-50 border-emerald-200";
    case "C":
      return "text-amber-800 bg-amber-50 border-amber-200";
    case "D":
      return "text-red-800 bg-red-50 border-red-200";
    default:
      return "text-ink-700 bg-ink-100 border-ink-200";
  }
}

export function recommendationStyle(r: string): {
  chip: string;
  label: string;
} {
  switch (r) {
    case "APPROVE":
      return { chip: "bg-brand-600 text-white", label: "Approve" };
    case "REFER":
      return { chip: "bg-amber-500 text-white", label: "Refer to Underwriter" };
    case "DECLINE":
      return { chip: "bg-red-600 text-white", label: "Decline" };
    default:
      return { chip: "bg-ink-500 text-white", label: r };
  }
}

export function trendGlyph(t: string): string {
  switch (t) {
    case "IMPROVING":
      return "↑";
    case "DECLINING":
      return "↓";
    case "STABLE":
      return "→";
    default:
      return "·";
  }
}

export function trendColor(t: string): string {
  switch (t) {
    case "IMPROVING":
      return "text-emerald-600";
    case "DECLINING":
      return "text-red-600";
    case "STABLE":
      return "text-ink-500";
    default:
      return "text-ink-400";
  }
}

export function factorKindColor(k: string): string {
  switch (k) {
    case "STRENGTH":
      return "border-l-emerald-500 bg-emerald-50/40";
    case "RISK":
      return "border-l-red-500 bg-red-50/40";
    default:
      return "border-l-ink-300 bg-ink-50/60";
  }
}
