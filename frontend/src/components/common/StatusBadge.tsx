import { cn } from "@/lib/utils";

const map: Record<string, string> = {
  open: "bg-blue-500/15 text-blue-300 border-blue-500/40",
  investigating: "bg-amber-500/15 text-amber-300 border-amber-500/40",
  resolved: "bg-emerald-500/15 text-emerald-300 border-emerald-500/40",
  closed: "bg-emerald-500/15 text-emerald-300 border-emerald-500/40",
  false_positive: "bg-zinc-500/15 text-zinc-300 border-zinc-500/40",
  active: "bg-red-500/15 text-red-300 border-red-500/40",
  contained: "bg-emerald-500/15 text-emerald-300 border-emerald-500/40",
  online: "bg-emerald-500/15 text-emerald-300 border-emerald-500/40",
  offline: "bg-zinc-500/15 text-zinc-300 border-zinc-500/40",
  disabled: "bg-zinc-500/15 text-zinc-300 border-zinc-500/40",
  enabled: "bg-emerald-500/15 text-emerald-300 border-emerald-500/40",
  pending: "bg-amber-500/15 text-amber-300 border-amber-500/40",
};

export function StatusBadge({ status, className }: { status?: string | null; className?: string }) {
  const key = (status ?? "open").toLowerCase();
  const style = map[key] ?? "bg-zinc-500/15 text-zinc-300 border-zinc-500/40";
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-md border px-2 py-0.5 text-[11px] font-medium",
        style,
        className,
      )}
    >
      {key.replace(/_/g, " ")}
    </span>
  );
}
