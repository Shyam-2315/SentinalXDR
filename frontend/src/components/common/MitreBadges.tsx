export function MitreBadges({
  techniques,
}: {
  techniques?: (string | { id?: string; name?: string })[] | null;
}) {
  if (!techniques || techniques.length === 0) {
    return <span className="text-xs text-muted-foreground">—</span>;
  }
  return (
    <div className="flex flex-wrap gap-1">
      {techniques.slice(0, 6).map((t, i) => {
        const label = typeof t === "string" ? t : (t.id ?? t.name ?? "T?");
        return (
          <span
            key={`${label}-${i}`}
            className="rounded border border-border/60 bg-background/40 px-1.5 py-0.5 font-mono text-[10px] text-blue-300"
          >
            {label}
          </span>
        );
      })}
      {techniques.length > 6 ? (
        <span className="text-[10px] text-muted-foreground">+{techniques.length - 6}</span>
      ) : null}
    </div>
  );
}
