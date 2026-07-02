export default function StrengthsRisks({
  strengths,
  risks,
}: {
  strengths: string[];
  risks: string[];
}) {
  return (
    <section className="grid gap-4 md:grid-cols-2">
      <Column
        title="Top strengths"
        items={strengths}
        icon="✓"
        colorClass="text-emerald-700"
        chipClass="bg-emerald-50 border-emerald-200"
      />
      <Column
        title="Top risks"
        items={risks}
        icon="!"
        colorClass="text-red-700"
        chipClass="bg-red-50 border-red-200"
        emptyMsg="No material risks detected across scored dimensions."
      />
    </section>
  );
}

function Column({
  title,
  items,
  icon,
  colorClass,
  chipClass,
  emptyMsg,
}: {
  title: string;
  items: string[];
  icon: string;
  colorClass: string;
  chipClass: string;
  emptyMsg?: string;
}) {
  return (
    <div className="card p-5">
      <div className="flex items-center justify-between mb-3">
        <h3 className={"text-sm font-semibold " + colorClass}>{title}</h3>
        <span className="text-[11px] text-ink-500">{items.length}</span>
      </div>
      {items.length === 0 ? (
        <p className="text-xs text-ink-500 italic">
          {emptyMsg ?? "None to report."}
        </p>
      ) : (
        <ul className="space-y-2">
          {items.map((s, i) => (
            <li key={i} className="flex items-start gap-3">
              <span
                className={
                  "shrink-0 h-6 w-6 rounded-full border grid place-items-center text-xs font-bold " +
                  chipClass +
                  " " +
                  colorClass
                }
              >
                {icon}
              </span>
              <span className="text-sm text-ink-700 leading-snug">{s}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
