import { cn } from "@/lib/utils";

const map: Record<string, string> = {
  critical:
    "bg-[color:var(--sev-critical)]/15 text-[color:var(--sev-critical)] border-[color:var(--sev-critical)]/40",
  high: "bg-[color:var(--sev-high)]/15 text-[color:var(--sev-high)] border-[color:var(--sev-high)]/40",
  medium:
    "bg-[color:var(--sev-medium)]/15 text-[color:var(--sev-medium)] border-[color:var(--sev-medium)]/40",
  low: "bg-[color:var(--sev-low)]/15 text-[color:var(--sev-low)] border-[color:var(--sev-low)]/40",
  info: "bg-[color:var(--sev-info)]/15 text-[color:var(--sev-info)] border-[color:var(--sev-info)]/40",
};

export function SeverityBadge({
  severity,
  className,
}: {
  severity?: string | null;
  className?: string;
}) {
  const key = (severity ?? "info").toLowerCase();
  const style = map[key] ?? map.info;
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-md border px-2 py-0.5 text-[11px] font-semibold uppercase tracking-wide",
        style,
        className,
      )}
    >
      {key}
    </span>
  );
}
