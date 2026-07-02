import {
  PolarAngleAxis,
  PolarGrid,
  PolarRadiusAxis,
  Radar,
  RadarChart,
  ResponsiveContainer,
  Tooltip,
} from "recharts";
import type { DimensionScore } from "../types";

export default function DimensionRadar({
  dimensions,
}: {
  dimensions: DimensionScore[];
}) {
  const data = dimensions.map((d) => ({
    dim: shortLabel(d.label),
    score: d.score,
    fullLabel: d.label,
    weight: d.weight,
    summary: d.summary,
  }));

  return (
    <div className="h-72">
      <ResponsiveContainer width="100%" height="100%">
        <RadarChart data={data} outerRadius="80%">
          <PolarGrid stroke="rgb(211 217 226)" />
          <PolarAngleAxis dataKey="dim" tick={{ fontSize: 11 }} />
          <PolarRadiusAxis
            domain={[0, 100]}
            tick={{ fontSize: 10 }}
            axisLine={false}
          />
          <Radar
            dataKey="score"
            stroke="#046046"
            fill="#0e7d5e"
            fillOpacity={0.22}
            strokeWidth={2}
            dot={{ fill: "#046046", r: 3 }}
          />
          <Tooltip
            content={({ payload }) => {
              if (!payload || !payload.length) return null;
              const p = payload[0].payload as (typeof data)[number];
              return (
                <div className="rounded-lg bg-white shadow-pop border border-ink-100 px-3 py-2 text-xs">
                  <div className="font-semibold text-ink-900">
                    {p.fullLabel}
                  </div>
                  <div className="text-ink-600">
                    Score {p.score} · weight {(p.weight * 100).toFixed(0)}%
                  </div>
                  <div className="text-ink-500 mt-1 max-w-52">{p.summary}</div>
                </div>
              );
            }}
          />
        </RadarChart>
      </ResponsiveContainer>
    </div>
  );
}

function shortLabel(l: string): string {
  return l
    .replace("Digital Transaction Vitality", "Digital Vitality")
    .replace("Compliance Discipline", "Compliance")
    .replace("Employment Stability", "Employment")
    .replace("Obligation & Leverage", "Obligation")
    .replace("Cash-Flow Strength", "Cash Flow")
    .replace("Revenue Health", "Revenue");
}
