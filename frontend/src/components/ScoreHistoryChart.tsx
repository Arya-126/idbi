import {
  Area,
  CartesianGrid,
  ComposedChart,
  Line,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { ScoreHistoryPoint } from "../types";

const BAND_LINES = [
  { y: 750, label: "A", color: "#046046" },
  { y: 600, label: "B", color: "#10b981" },
  { y: 450, label: "C", color: "#f59e0b" },
];

export default function ScoreHistoryChart({
  points,
}: {
  points: ScoreHistoryPoint[];
}) {
  if (points.length < 2) {
    return (
      <div className="text-xs text-ink-500 italic">
        Not enough history yet — score trend appears after a few months of
        signals.
      </div>
    );
  }

  const data = points.map((p) => ({
    period: p.period.slice(2), // "YY-MM"
    score: p.composite_score,
    band: p.risk_band,
    observed: p.observed,
  }));

  const first = points[0].composite_score;
  const last = points[points.length - 1].composite_score;
  const delta = last - first;
  const trendColor =
    delta > 20 ? "#046046" : delta < -20 ? "#dc2626" : "#586582";

  return (
    <div>
      <div className="flex items-baseline justify-between mb-2">
        <div className="text-[10px] uppercase tracking-wider text-ink-500">
          Composite score, last {points.length} months
        </div>
        <div className="text-xs font-mono tabular-nums" style={{ color: trendColor }}>
          {first} → {last} ({delta >= 0 ? "+" : ""}{delta})
        </div>
      </div>
      <div className="h-40">
        <ResponsiveContainer width="100%" height="100%">
          <ComposedChart data={data} margin={{ top: 8, right: 10, left: -20, bottom: 0 }}>
            <CartesianGrid stroke="rgb(236 238 242)" strokeDasharray="2 3" />
            <XAxis dataKey="period" tick={{ fontSize: 10 }} axisLine={false} />
            <YAxis
              domain={[300, 1000]}
              tick={{ fontSize: 10 }}
              axisLine={false}
              width={40}
            />
            {BAND_LINES.map((b) => (
              <ReferenceLine
                key={b.y}
                y={b.y}
                stroke={b.color}
                strokeOpacity={0.2}
                strokeDasharray="4 4"
                label={{
                  value: b.label,
                  fill: b.color,
                  fontSize: 9,
                  position: "right",
                }}
              />
            ))}
            <Area
              type="monotone"
              dataKey="score"
              stroke="none"
              fill="#0e7d5e"
              fillOpacity={0.12}
            />
            <Line
              type="monotone"
              dataKey="score"
              stroke="#046046"
              strokeWidth={2}
              // Observed points (real recorded runs) render solid; the
              // reconstructed approximation renders hollow.
              dot={(props: { cx?: number; cy?: number; payload?: { observed?: boolean }; index?: number }) => {
                const { cx, cy, payload, index } = props;
                if (cx == null || cy == null) return <g key={index} />;
                return payload?.observed ? (
                  <circle key={index} cx={cx} cy={cy} r={4} fill="#046046" />
                ) : (
                  <circle
                    key={index}
                    cx={cx}
                    cy={cy}
                    r={3}
                    fill="#ffffff"
                    stroke="#046046"
                    strokeWidth={1.5}
                  />
                );
              }}
            />
            <Tooltip
              content={({ payload }) => {
                if (!payload || !payload.length) return null;
                const p = payload[0].payload;
                return (
                  <div className="rounded-lg bg-white shadow-pop border border-ink-100 px-3 py-2 text-xs">
                    <div className="font-semibold text-ink-900">
                      20{p.period}
                    </div>
                    <div className="text-ink-600">
                      Composite {p.score} · Band {p.band}
                    </div>
                    <div className="text-[10px] text-ink-400">
                      {p.observed
                        ? "observed — recorded scoring run"
                        : "reconstructed from windowed re-scoring"}
                    </div>
                  </div>
                );
              }}
            />
          </ComposedChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
