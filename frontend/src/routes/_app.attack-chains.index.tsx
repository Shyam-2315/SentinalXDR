import { createFileRoute, Link } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import { GitBranch } from "lucide-react";
import { api } from "@/lib/api";
import { toArray, fmtRelative } from "@/lib/format";
import { SeverityBadge } from "@/components/common/SeverityBadge";
import { StatusBadge } from "@/components/common/StatusBadge";
import { MitreBadges } from "@/components/common/MitreBadges";
import { EmptyState } from "@/components/common/EmptyState";
import { ErrorState, LoadingState } from "@/components/common/PageState";
import { Card, CardContent } from "@/components/ui/card";

export const Route = createFileRoute("/_app/attack-chains/")({ component: ChainsList });

type Chain = {
  id?: string;
  chain_id?: string;
  title?: string;
  severity?: string;
  risk_score?: number;
  confidence_score?: number;
  status?: string;
  mitre_techniques?: string[];
  first_seen_at?: string;
};

function ChainsList() {
  const query = useQuery({
    queryKey: ["chains"],
    queryFn: () => api.get<unknown>("/api/attack-chains"),
  });
  const rows = toArray<Chain>(query.data);
  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-xl font-semibold tracking-tight">Attack Chains</h1>
        <p className="text-sm text-muted-foreground">
          AI-correlated attack narratives across kill-chain phases.
        </p>
      </div>
      <Card className="border-border/60 bg-card/60">
        <CardContent className="p-0">
          {query.isLoading ? (
            <LoadingState label="Loading attack chains" />
          ) : query.isError ? (
            <div className="p-6">
              <ErrorState error={query.error} onRetry={() => void query.refetch()} />
            </div>
          ) : rows.length === 0 ? (
            <div className="p-6">
              <EmptyState icon={GitBranch} title="No attack chains" />
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="bg-muted/40 text-xs uppercase tracking-wide text-muted-foreground">
                  <tr>
                    <th className="px-3 py-2 text-left">Title</th>
                    <th className="px-3 py-2 text-left">Severity</th>
                    <th className="px-3 py-2 text-right">Risk</th>
                    <th className="px-3 py-2 text-right">Confidence</th>
                    <th className="px-3 py-2 text-left">Status</th>
                    <th className="px-3 py-2 text-left">MITRE</th>
                    <th className="px-3 py-2 text-left">First Seen</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border/60">
                  {rows.map((c) => {
                    const id = c.id ?? c.chain_id ?? "";
                    return (
                      <tr key={id} className="hover:bg-muted/20">
                        <td className="px-3 py-2">
                          <Link
                            to="/attack-chains/$id"
                            params={{ id }}
                            className="font-medium hover:text-primary"
                          >
                            {c.title ?? "—"}
                          </Link>
                        </td>
                        <td className="px-3 py-2">
                          <SeverityBadge severity={c.severity} />
                        </td>
                        <td className="px-3 py-2 text-right font-mono text-xs">
                          {c.risk_score ?? 0}
                        </td>
                        <td className="px-3 py-2 text-right font-mono text-xs">
                          {c.confidence_score ?? 0}
                        </td>
                        <td className="px-3 py-2">
                          <StatusBadge status={c.status} />
                        </td>
                        <td className="px-3 py-2">
                          <MitreBadges techniques={c.mitre_techniques} />
                        </td>
                        <td className="px-3 py-2 text-xs text-muted-foreground">
                          {fmtRelative(c.first_seen_at)}
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
