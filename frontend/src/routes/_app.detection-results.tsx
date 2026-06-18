import { createFileRoute } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { ShieldCheck } from "lucide-react";
import { api } from "@/lib/api";
import { toArray, fmtRelative } from "@/lib/format";
import { SeverityBadge } from "@/components/common/SeverityBadge";
import { MitreBadges } from "@/components/common/MitreBadges";
import { EmptyState } from "@/components/common/EmptyState";
import { ErrorState, LoadingState } from "@/components/common/PageState";
import { JsonViewer } from "@/components/common/JsonViewer";
import { Card, CardContent } from "@/components/ui/card";
import { Sheet, SheetContent, SheetHeader, SheetTitle } from "@/components/ui/sheet";

export const Route = createFileRoute("/_app/detection-results")({
  component: DetectionResultsPage,
});

type DetectionResult = {
  id?: string;
  result_id?: string;
  rule_id?: string;
  rule_name?: string;
  severity?: string;
  title?: string;
  description?: string;
  event_id?: string;
  agent_id?: string;
  mitre_tactics?: string[];
  mitre_techniques?: string[];
  matched_fields?: unknown;
  created_at?: string;
};

function DetectionResultsPage() {
  const [selected, setSelected] = useState<DetectionResult | null>(null);
  const selectedId = selected?.id ?? selected?.result_id ?? "";
  const query = useQuery({
    queryKey: ["detections", "results"],
    queryFn: () => api.get<unknown>("/api/detections/results"),
  });
  const detail = useQuery({
    queryKey: ["detections", "results", selectedId],
    queryFn: () => api.get<DetectionResult>(`/api/detections/results/${selectedId}`),
    enabled: !!selectedId,
  });
  const rows = toArray<DetectionResult>(query.data);
  const selectedResult = detail.data ?? selected;

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-xl font-semibold tracking-tight">Detection Results</h1>
        <p className="text-sm text-muted-foreground">
          Rule matches created from backend detection evaluation.
        </p>
      </div>
      <Card className="border-border/60 bg-card/60">
        <CardContent className="p-0">
          {query.isLoading ? (
            <LoadingState label="Loading detection results" />
          ) : query.isError ? (
            <div className="p-6">
              <ErrorState error={query.error} onRetry={() => void query.refetch()} />
            </div>
          ) : rows.length === 0 ? (
            <div className="p-6">
              <EmptyState icon={ShieldCheck} title="No detection results" />
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="bg-muted/40 text-xs uppercase tracking-wide text-muted-foreground">
                  <tr>
                    <th className="px-3 py-2 text-left">Rule</th>
                    <th className="px-3 py-2 text-left">Severity</th>
                    <th className="px-3 py-2 text-left">Event</th>
                    <th className="px-3 py-2 text-left">Agent</th>
                    <th className="px-3 py-2 text-left">MITRE</th>
                    <th className="px-3 py-2 text-left">Created</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border/60">
                  {rows.map((result) => {
                    const id = result.id ?? result.result_id ?? "";
                    return (
                      <tr
                        key={id}
                        className="cursor-pointer hover:bg-muted/20"
                        onClick={() => setSelected(result)}
                      >
                        <td className="px-3 py-2 font-medium">
                          {result.rule_name ?? result.title ?? "—"}
                        </td>
                        <td className="px-3 py-2">
                          <SeverityBadge severity={result.severity} />
                        </td>
                        <td className="px-3 py-2 font-mono text-xs text-muted-foreground">
                          {result.event_id ?? "—"}
                        </td>
                        <td className="px-3 py-2 font-mono text-xs text-muted-foreground">
                          {result.agent_id ?? "—"}
                        </td>
                        <td className="px-3 py-2">
                          <MitreBadges techniques={result.mitre_techniques} />
                        </td>
                        <td className="px-3 py-2 text-xs text-muted-foreground">
                          {fmtRelative(result.created_at)}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>
      <Sheet open={!!selected} onOpenChange={(open) => !open && setSelected(null)}>
        <SheetContent className="w-full overflow-y-auto sm:max-w-xl">
          <SheetHeader>
            <SheetTitle>
              {selectedResult?.title ?? selectedResult?.rule_name ?? "Result"}
            </SheetTitle>
          </SheetHeader>
          {selectedResult ? (
            <div className="space-y-4 p-4 pt-2">
              <div className="flex items-center gap-2">
                <SeverityBadge severity={selectedResult.severity} />
                <span className="text-xs text-muted-foreground">
                  {fmtRelative(selectedResult.created_at)}
                </span>
              </div>
              {selectedResult.description ? (
                <p className="text-sm">{selectedResult.description}</p>
              ) : null}
              <MitreBadges techniques={selectedResult.mitre_techniques} />
              <JsonViewer data={selectedResult.matched_fields ?? selectedResult} />
            </div>
          ) : null}
        </SheetContent>
      </Sheet>
    </div>
  );
}
