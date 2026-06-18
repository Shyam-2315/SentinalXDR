import { RefreshCw } from "lucide-react";
import { getErrorMessage, SEED_COMMAND } from "@/lib/page-state";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";

export function LoadingState({ label = "Loading data" }: { label?: string }) {
  return (
    <div className="space-y-3 p-6">
      <p className="text-sm text-muted-foreground">{label}...</p>
      <Skeleton className="h-8 w-full" />
      <Skeleton className="h-8 w-11/12" />
      <Skeleton className="h-8 w-10/12" />
    </div>
  );
}

export function ErrorState({ error, onRetry }: { error: unknown; onRetry?: () => void }) {
  return (
    <div className="rounded-md border border-[color:var(--sev-critical)]/40 bg-[color:var(--sev-critical)]/10 p-4">
      <p className="text-sm font-medium text-[color:var(--sev-critical)]">Backend request failed</p>
      <p className="mt-1 text-sm text-foreground/90">{getErrorMessage(error)}</p>
      <p className="mt-2 text-xs text-muted-foreground">Demo data: {SEED_COMMAND}</p>
      {onRetry ? (
        <Button size="sm" variant="outline" className="mt-3" onClick={onRetry}>
          <RefreshCw className="mr-1 h-3.5 w-3.5" /> Retry
        </Button>
      ) : null}
    </div>
  );
}
