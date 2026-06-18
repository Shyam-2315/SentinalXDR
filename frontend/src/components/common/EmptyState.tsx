import type { LucideIcon } from "lucide-react";
import { SEED_COMMAND } from "@/lib/page-state";

export function EmptyState({
  icon: Icon,
  title,
  description,
}: {
  icon?: LucideIcon;
  title: string;
  description?: string;
}) {
  return (
    <div className="flex flex-col items-center justify-center gap-2 rounded-md border border-dashed border-border/70 bg-card/30 py-10 text-center">
      {Icon ? <Icon className="h-8 w-8 text-muted-foreground" /> : null}
      <p className="text-sm font-medium text-foreground">{title}</p>
      <p className="max-w-md text-xs text-muted-foreground">
        {description ?? `Seed demo data with: ${SEED_COMMAND}`}
      </p>
    </div>
  );
}
