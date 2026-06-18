import { createFileRoute, Link } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import { AlertOctagon } from "lucide-react";
import { api } from "@/lib/api";
import { toArray, fmtRelative } from "@/lib/format";
import { SeverityBadge } from "@/components/common/SeverityBadge";
import { StatusBadge } from "@/components/common/StatusBadge";
import { MitreBadges } from "@/components/common/MitreBadges";
import { EmptyState } from "@/components/common/EmptyState";
import { ErrorState, LoadingState } from "@/components/common/PageState";
import { Card, CardContent } from "@/components/ui/card";

export const Route = createFileRoute("/_app/incidents/")({ component: IncidentsList });

type Incident = {
  id?: string;
  incident_id?: string;
  severity?: string;
  status?: string;
  title?: string;
  alert_count?: number;
  alert_ids?: string[];
  mitre_techniques?: string[];
  first_seen_at?: string;
  last_seen_at?: string;
};

function IncidentsList() {
  const query = useQuery({
    queryKey: ["incidents"],
    queryFn: () => api.get<unknown>("/api/incidents"),
  });
  const rows = toArray<Incident>(query.data);
  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-xl font-semibold tracking-tight">Incidents</h1>
        <p className="text-sm text-muted-foreground">
          Correlated cases combining related alerts and entities.
        </p>
      </div>
      <Card className="border-border/60 bg-card/60">
        <CardContent className="p-0">
          {query.isLoading ? (
            <LoadingState label="Loading incidents" />
          ) : query.isError ? (
            <div className="p-6">
              <ErrorState error={query.error} onRetry={() => void query.refetch()} />
            </div>
          ) : rows.length === 0 ? (
            <div className="p-6">
              <EmptyState icon={AlertOctagon} title="No incidents" />
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="bg-muted/40 text-xs uppercase tracking-wide text-muted-foreground">
                  <tr>
                    <th className="px-3 py-2 text-left">Severity</th>
                    <th className="px-3 py-2 text-left">Status</th>
                    <th className="px-3 py-2 text-left">Title</th>
                    <th className="px-3 py-2 text-left">Alerts</th>
                    <th className="px-3 py-2 text-left">MITRE</th>
                    <th className="px-3 py-2 text-left">First Seen</th>
                    <th className="px-3 py-2 text-left">Last Seen</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border/60">
                  {rows.map((i) => {
                    const id = i.id ?? i.incident_id ?? "";
                    return (
                      <tr key={id} className="hover:bg-muted/20">
                        <td className="px-3 py-2">
                          <SeverityBadge severity={i.severity} />
                        </td>
                        <td className="px-3 py-2">
                          <StatusBadge status={i.status} />
                        </td>
                        <td className="px-3 py-2">
                          <Link
                            to="/incidents/$id"
                            params={{ id }}
                            className="font-medium text-foreground hover:text-primary"
                          >
                            {i.title ?? "—"}
                          </Link>
                        </td>
                        <td className="px-3 py-2 tabular-nums">
                          {i.alert_count ?? i.alert_ids?.length ?? 0}
                        </td>
                        <td className="px-3 py-2">
                          <MitreBadges techniques={i.mitre_techniques} />
                        </td>
                        <td className="px-3 py-2 text-xs text-muted-foreground">
                          {fmtRelative(i.first_seen_at)}
                        </td>
                        <td className="px-3 py-2 text-xs text-muted-foreground">
                          {fmtRelative(i.last_seen_at)}
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
    </div>
  );
}
