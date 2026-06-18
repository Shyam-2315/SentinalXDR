import { createFileRoute } from "@tanstack/react-router";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Bell } from "lucide-react";
import { toast } from "sonner";
import { api } from "@/lib/api";
import { toArray, fmtRelative } from "@/lib/format";
import { SeverityBadge } from "@/components/common/SeverityBadge";
import { StatusBadge } from "@/components/common/StatusBadge";
import { MitreBadges } from "@/components/common/MitreBadges";
import { EmptyState } from "@/components/common/EmptyState";
import { ErrorState, LoadingState } from "@/components/common/PageState";
import { JsonViewer } from "@/components/common/JsonViewer";
import { Card, CardContent } from "@/components/ui/card";
import { Sheet, SheetContent, SheetHeader, SheetTitle } from "@/components/ui/sheet";

export const Route = createFileRoute("/_app/alerts")({ component: AlertsPage });

type Alert = {
  id?: string;
  alert_id?: string;
  severity?: string;
  status?: string;
  title?: string;
  mitre_techniques?: string[];
  created_at?: string;
  agent_id?: string;
  description?: string;
  details?: unknown;
};

const STATUSES = ["open", "investigating", "resolved", "false_positive"] as const;

function AlertsPage() {
  const qc = useQueryClient();
  const [selected, setSelected] = useState<Alert | null>(null);
  const selectedId = selected?.id ?? selected?.alert_id ?? "";
  const query = useQuery({
    queryKey: ["alerts"],
    queryFn: () => api.get<unknown>("/api/alerts"),
  });
  const rows = toArray<Alert>(query.data);
  const detail = useQuery({
    queryKey: ["alert", selectedId],
    queryFn: () => api.get<Alert>(`/api/alerts/${selectedId}`),
    enabled: !!selectedId,
  });
  const selectedAlert = detail.data ?? selected;

  const updateStatus = useMutation({
    mutationFn: ({ id, status }: { id: string; status: string }) =>
      api.patch(`/api/alerts/${id}/status`, { status }),
    onSuccess: () => {
      toast.success("Alert updated");
      void qc.invalidateQueries({ queryKey: ["alerts"] });
    },
  });

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-xl font-semibold tracking-tight">Alerts</h1>
        <p className="text-sm text-muted-foreground">
          Detections raised from matched rules and AI signals.
        </p>
      </div>
      <Card className="border-border/60 bg-card/60">
        <CardContent className="p-0">
          {query.isLoading ? (
            <LoadingState label="Loading alerts" />
          ) : query.isError ? (
            <div className="p-6">
              <ErrorState error={query.error} onRetry={() => void query.refetch()} />
            </div>
          ) : rows.length === 0 ? (
            <div className="p-6">
              <EmptyState icon={Bell} title="No alerts" />
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="bg-muted/40 text-xs uppercase tracking-wide text-muted-foreground">
                  <tr>
                    <th className="px-3 py-2 text-left">Severity</th>
                    <th className="px-3 py-2 text-left">Status</th>
                    <th className="px-3 py-2 text-left">Title</th>
                    <th className="px-3 py-2 text-left">MITRE</th>
                    <th className="px-3 py-2 text-left">Created</th>
                    <th className="px-3 py-2 text-left">Agent</th>
                    <th className="px-3 py-2"></th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border/60">
                  {rows.map((a) => {
                    const id = a.id ?? a.alert_id ?? "";
                    return (
                      <tr key={id} className="hover:bg-muted/20">
                        <td className="px-3 py-2">
                          <SeverityBadge severity={a.severity} />
                        </td>
                        <td className="px-3 py-2">
                          <StatusBadge status={a.status} />
                        </td>
                        <td
                          className="cursor-pointer px-3 py-2 font-medium"
                          onClick={() => setSelected(a)}
                        >
                          {a.title ?? "—"}
                        </td>
                        <td className="px-3 py-2">
                          <MitreBadges techniques={a.mitre_techniques} />
                        </td>
                        <td className="px-3 py-2 text-xs text-muted-foreground">
                          {fmtRelative(a.created_at)}
                        </td>
                        <td className="px-3 py-2 font-mono text-xs text-muted-foreground">
                          {a.agent_id ?? "—"}
                        </td>
                        <td className="px-3 py-2">
                          <select
                            value={a.status ?? "open"}
                            onChange={(e) =>
                              id && updateStatus.mutate({ id, status: e.target.value })
                            }
                            className="h-8 rounded-md border border-input bg-background px-2 text-xs"
                          >
                            {STATUSES.map((s) => (
                              <option key={s} value={s}>
                                {s.replace("_", " ")}
                              </option>
                            ))}
                          </select>
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
      <Sheet open={!!selected} onOpenChange={(o) => !o && setSelected(null)}>
        <SheetContent className="w-full overflow-y-auto sm:max-w-xl">
          <SheetHeader>
            <SheetTitle>{selectedAlert?.title ?? "Alert"}</SheetTitle>
          </SheetHeader>
          {selectedAlert && (
            <div className="space-y-4 p-4 pt-2">
              <div className="flex items-center gap-2">
                <SeverityBadge severity={selectedAlert.severity} />
                <StatusBadge status={selectedAlert.status} />
                <span className="text-xs text-muted-foreground">
                  {fmtRelative(selectedAlert.created_at)}
                </span>
              </div>
              {selectedAlert.description && <p className="text-sm">{selectedAlert.description}</p>}
              <MitreBadges techniques={selectedAlert.mitre_techniques} />
              <JsonViewer data={selectedAlert.details ?? selectedAlert} />
            </div>
          )}
        </SheetContent>
      </Sheet>
    </div>
  );
}
