import { createFileRoute } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import { Crosshair } from "lucide-react";
import { api } from "@/lib/api";
import { toArray } from "@/lib/format";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { EmptyState } from "@/components/common/EmptyState";

export const Route = createFileRoute("/_app/mitre")({ component: MitrePage });

type Technique = {
  id?: string;
  technique_id?: string;
  name?: string;
  technique_name?: string;
  tactic?: string;
  count?: number;
  severity?: string;
};

function MitrePage() {
  const { data, isLoading } = useQuery({
    queryKey: ["mitre"],
    queryFn: () => api.get<unknown>("/api/dashboard/mitre-summary"),
  });
  const rows = toArray<Technique>(data);

  const grouped = rows.reduce<Record<string, Technique[]>>((acc, t) => {
    const k = t.tactic ?? "Uncategorized";
    (acc[k] ??= []).push(t);
    return acc;
  }, {});

  const tactics = Object.keys(grouped);

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-xl font-semibold tracking-tight">MITRE ATT&amp;CK Summary</h1>
        <p className="text-sm text-muted-foreground">
          Coverage of observed adversary techniques across tactics.
        </p>
      </div>
      {isLoading ? (
        <p className="text-sm text-muted-foreground">Loading…</p>
      ) : tactics.length === 0 ? (
        <EmptyState icon={Crosshair} title="No MITRE data" />
      ) : (
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {tactics.map((tactic) => (
            <Card key={tactic} className="border-border/60 bg-card/60">
              <CardHeader className="pb-2 flex flex-row items-center justify-between">
                <CardTitle className="text-sm">{tactic}</CardTitle>
                <span className="text-xs text-muted-foreground">
                  {grouped[tactic].length} techniques
                </span>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-2 gap-2">
                  {grouped[tactic].map((t, i) => {
                    const sev = (t.severity ?? "").toLowerCase();
                    const hot = sev === "critical" || sev === "high" || (t.count ?? 0) >= 5;
                    return (
                      <div
                        key={i}
                        className={`rounded border p-2 ${hot ? "border-[color:var(--sev-critical)]/40 bg-[color:var(--sev-critical)]/10" : "border-border/60 bg-background/40"}`}
                      >
                        <p className="font-mono text-[11px] text-blue-300">
                          {t.id ?? t.technique_id ?? "T?"}
                        </p>
                        <p className="truncate text-xs">{t.name ?? t.technique_name ?? "—"}</p>
                        <p className="text-[10px] text-muted-foreground">{t.count ?? 0} hits</p>
                      </div>
                    );
                  })}
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
