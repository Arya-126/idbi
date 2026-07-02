// A SVG dial for the composite score.
// The arc fills proportionally to score/1000 and the colour follows the band.

export default function ScoreDial({
  score,
  band,
}: {
  score: number;
  band: string;
}) {
  const pct = Math.max(0, Math.min(1, score / 1000));
  const size = 152;
  const stroke = 14;
  const cx = size / 2;
  const cy = size / 2;
  const r = (size - stroke) / 2;

  // Draw a 3/4 arc (from 135° to 405° = 45°) so it has a nice open bottom.
  const startAngle = 135;
  const endAngle = 405;
  const arcTotal = endAngle - startAngle;

  const bg = describeArc(cx, cy, r, startAngle, endAngle);
  const fg = describeArc(cx, cy, r, startAngle, startAngle + arcTotal * pct);

  const color = bandStroke(band);

  return (
    <div className="relative" style={{ width: size, height: size }}>
      <svg width={size} height={size}>
        <path
          d={bg}
          fill="none"
          stroke="rgb(236 238 242)"
          strokeWidth={stroke}
          strokeLinecap="round"
        />
        <path
          d={fg}
          fill="none"
          stroke={color}
          strokeWidth={stroke}
          strokeLinecap="round"
          style={{
            transition: "all 700ms cubic-bezier(0.22, 1, 0.36, 1)",
          }}
        />
      </svg>
      <div className="absolute inset-0 grid place-items-center text-center">
        <div>
          <div className="text-3xl font-display font-semibold text-ink-900 leading-none">
            {score}
          </div>
          <div className="text-[10px] uppercase tracking-wider text-ink-500 mt-1">
            of 1000
          </div>
        </div>
      </div>
    </div>
  );
}

function polar(cx: number, cy: number, r: number, angleDeg: number) {
  const a = ((angleDeg - 90) * Math.PI) / 180.0;
  return { x: cx + r * Math.cos(a), y: cy + r * Math.sin(a) };
}

function describeArc(
  cx: number,
  cy: number,
  r: number,
  startAngle: number,
  endAngle: number,
): string {
  const start = polar(cx, cy, r, startAngle);
  const end = polar(cx, cy, r, endAngle);
  const largeArc = endAngle - startAngle <= 180 ? "0" : "1";
  return [
    "M",
    start.x,
    start.y,
    "A",
    r,
    r,
    0,
    largeArc,
    1,
    end.x,
    end.y,
  ].join(" ");
}

function bandStroke(b: string): string {
  switch (b) {
    case "A":
      return "#046046";
    case "B":
      return "#10b981";
    case "C":
      return "#f59e0b";
    case "D":
      return "#ef4444";
    default:
      return "#586582";
  }
}
