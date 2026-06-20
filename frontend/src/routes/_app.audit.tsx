import { createFileRoute } from "@tanstack/react-router";
import { useMutation, useQuery } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import { ClipboardList, FileDown } from "lucide-react";
import { toast } from "sonner";
import { api } from "@/lib/api";
import { fmtDate, toArray } from "@/lib/format";
import { EmptyState } from "@/components/common/EmptyState";
import { ErrorState, LoadingState } from "@/components/common/PageState";
import { JsonViewer } from "@/components/common/JsonViewer";
import { StatusBadge } from "@/components/common/StatusBadge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Sheet, SheetContent, SheetHeader, SheetTitle } from "@/components/ui/sheet";
import { saveDownload, sentinelApi } from "@/lib/sentinelxdr-api";

export const Route = createFileRoute("/_app/audit")({ component: AuditLogsPage });

type AuditLog = {
  id?: string;
  organization_id?: string | null;
  actor_user_id?: string | null;
  actor_email?: string | null;
  actor_role?: string | null;
  action?: string;
  resource_type?: string;
  resource_id?: string | null;
  status?: string;
  ip_address?: string | null;
  user_agent?: string | null;
  description?: string;
  metadata?: Record<string, unknown>;
  created_at?: string;
};

const STATUSES = ["", "success", "failure"] as const;

function AuditLogsPage() {
  const [selected, setSelected] = useState<AuditLog | null>(null);
  const [action, setAction] = useState("");
  const [resourceType, setResourceType] = useState("");
  const [status, setStatus] = useState("");
  const queryString = useMemo(() => {
    const params = new URLSearchParams();
    if (action) params.set("action", action);
    if (resourceType) params.set("resource_type", resourceType);
    if (status) params.set("status", status);
    params.set("limit", "100");
    const value = params.toString();
    return value ? `?${value}` : "";
  }, [action, resourceType, status]);

  const query = useQuery({
    queryKey: ["audit", queryString],
    queryFn: () => api.get<unknown>(`/api/audit${queryString}`),
  });
  const exportCsv = useMutation({
    mutationFn: () => sentinelApi.downloadAuditCsv(),
    onSuccess: (download) => {
      saveDownload(download);
      toast.success("Audit CSV exported");
    },
  });
  const rows = toArray<AuditLog>(query.data);
  const actions = uniqueOptions(rows.map((row) => row.action));
  const resourceTypes = uniqueOptions(rows.map((row) => row.resource_type));

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold tracking-tight">Audit Logs</h1>
          <p className="text-sm text-muted-foreground">
            Immutable user and system activity for compliance review.
          </p>
        </div>
        <Button
          size="sm"
          variant="outline"
          onClick={() => exportCsv.mutate()}
          disabled={exportCsv.isPending}
        >
          <FileDown className="h-4 w-4" />
          Export CSV
        </Button>
      </div>

      <div className="flex flex-wrap gap-2">
        <select
          value={action}
          onChange={(event) => setAction(event.target.value)}
          className="h-9 rounded-md border border-input bg-background px-2 text-sm"
        >
          <option value="">All actions</option>
          {actions.map((option) => (
            <option key={option} value={option}>
              {option}
            </option>
          ))}
        </select>
        <select
          value={resourceType}
          onChange={(event) => setResourceType(event.target.value)}
          className="h-9 rounded-md border border-input bg-background px-2 text-sm"
        >
          <option value="">All resources</option>
          {resourceTypes.map((option) => (
            <option key={option} value={option}>
              {option}
            </option>
          ))}
        </select>
        <select
          value={status}
          onChange={(event) => setStatus(event.target.value)}
          className="h-9 rounded-md border border-input bg-background px-2 text-sm"
        >
          {STATUSES.map((option) => (
            <option key={option || "all"} value={option}>
              {option || "All statuses"}
            </option>
          ))}
        </select>
      </div>

      <Card className="border-border/60 bg-card/60">
        <CardContent className="p-0">
          {query.isLoading ? (
            <LoadingState label="Loading audit logs" />
          ) : query.isError ? (
            <div className="p-6">
              <ErrorState error={query.error} onRetry={() => void query.refetch()} />
            </div>
          ) : rows.length === 0 ? (
            <div className="p-6">
              <EmptyState icon={ClipboardList} title="No audit logs" />
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="bg-muted/40 text-xs uppercase tracking-wide text-muted-foreground">
                  <tr>
                    <th className="px-3 py-2 text-left">Timestamp</th>
                    <th className="px-3 py-2 text-left">Actor</th>
                    <th className="px-3 py-2 text-left">Action</th>
                    <th className="px-3 py-2 text-left">Resource</th>
                    <th className="px-3 py-2 text-left">Status</th>
                    <th className="px-3 py-2 text-left">Description</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border/60">
                  {rows.map((row) => (
                    <tr
                      key={row.id}
                      className="cursor-pointer hover:bg-muted/20"
                      onClick={() => setSelected(row)}
                    >
                      <td className="whitespace-nowrap px-3 py-2 text-xs text-muted-foreground">
                        {fmtDate(row.created_at)}
                      </td>
                      <td className="px-3 py-2">{row.actor_email ?? "System"}</td>
                      <td className="px-3 py-2 font-mono text-xs">{row.action ?? "—"}</td>
                      <td className="px-3 py-2">{row.resource_type ?? "—"}</td>
                      <td className="px-3 py-2">
                        <StatusBadge status={row.status} />
                      </td>
                      <td className="max-w-md truncate px-3 py-2">{row.description ?? "—"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>

      <Sheet open={!!selected} onOpenChange={(open) => !open && setSelected(null)}>
        <SheetContent className="w-full overflow-y-auto sm:max-w-xl">
          <SheetHeader>
            <SheetTitle>{selected?.action ?? "Audit Log"}</SheetTitle>
          </SheetHeader>
          {selected && (
            <div className="space-y-4 p-4 pt-2">
              <div className="grid gap-2 text-sm">
                <Info label="Timestamp" value={fmtDate(selected.created_at)} />
                <Info label="Actor" value={selected.actor_email ?? "System"} />
                <Info label="Role" value={selected.actor_role ?? "—"} />
                <Info label="Resource" value={selected.resource_type ?? "—"} />
                <Info label="Resource ID" value={selected.resource_id ?? "—"} />
                <Info label="IP Address" value={selected.ip_address ?? "—"} />
                <Info label="User Agent" value={selected.user_agent ?? "—"} />
              </div>
              <div>
                <p className="mb-2 text-xs uppercase tracking-wide text-muted-foreground">
                  Metadata
                </p>
                <JsonViewer data={selected.metadata ?? {}} />
              </div>
            </div>
          )}
        </SheetContent>
      </Sheet>
    </div>
  );
}

function Info({ label, value }: { label: string; value: string }) {
  return (
    <div className="grid grid-cols-[7rem_1fr] gap-2">
      <span className="text-muted-foreground">{label}</span>
      <span className="min-w-0 break-words text-foreground">{value}</span>
    </div>
  );
}

function uniqueOptions(values: Array<string | undefined>) {
  return [...new Set(values.filter((value): value is string => Boolean(value)))].sort();
}
