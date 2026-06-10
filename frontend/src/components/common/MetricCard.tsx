import type { LucideIcon } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { cn } from "@/lib/utils";

export function MetricCard({
  label,
  value,
  hint,
  icon: Icon,
  tone = "default",
  loading,
}: {
  label: string;
  value: React.ReactNode;
  hint?: string;
  icon?: LucideIcon;
  tone?: "default" | "critical" | "warning" | "info" | "success";
  loading?: boolean;
}) {
  const tones: Record<string, string> = {
    default: "text-foreground",
    critical: "text-[color:var(--sev-critical)]",
    warning: "text-[color:var(--sev-medium)]",
    info: "text-blue-400",
    success: "text-emerald-400",
  };
  return (
    <Card className="border-border/60 bg-card/60 backdrop-blur">
      <CardContent className="p-4">
        <div className="flex items-start justify-between gap-2">
          <div className="space-y-1">
            <p className="text-xs uppercase tracking-wide text-muted-foreground">{label}</p>
            <p className={cn("text-2xl font-semibold tabular-nums", tones[tone])}>
              {loading ? (
                <span className="inline-block h-7 w-16 animate-pulse rounded bg-muted" />
              ) : (
                value
              )}
            </p>
            {hint ? <p className="text-xs text-muted-foreground">{hint}</p> : null}
          </div>
          {Icon ? (
            <div
              className={cn("rounded-md border border-border/60 bg-background/50 p-2", tones[tone])}
            >
              <Icon className="h-4 w-4" />
            </div>
          ) : null}
        </div>
      </CardContent>
    </Card>
  );
}
