import { createFileRoute, Link } from "@tanstack/react-router";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useState, useEffect } from "react";
import { ArrowLeft } from "lucide-react";
import { toast } from "sonner";
import { api } from "@/lib/api";
import { fmtRelative, toArray } from "@/lib/format";
import { SeverityBadge } from "@/components/common/SeverityBadge";
import { StatusBadge } from "@/components/common/StatusBadge";
import { MitreBadges } from "@/components/common/MitreBadges";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Input } from "@/components/ui/input";

export const Route = createFileRoute("/_app/incidents/$id")({ component: IncidentDetail });

function IncidentDetail() {
  const { id } = Route.useParams();
  const qc = useQueryClient();
  const { data } = useQuery({
    queryKey: ["incident", id],
    queryFn: () => api.get<Record<string, unknown>>(`/api/incidents/${id}`),
  });
  const chain = useQuery({
    queryKey: ["incident", id, "chain"],
    queryFn: () =>
      api.get<Record<string, unknown>>(`/api/incidents/${id}/attack-chain`).catch(() => null),
  });

  const [summary, setSummary] = useState("");
  const [assignee, setAssignee] = useState("");
  useEffect(() => {
    if (data) {
      setSummary(String(data.summary ?? ""));
      setAssignee(String(data.assigned_to_user_id ?? ""));
    }
  }, [data]);

  const updateStatus = useMutation({
    mutationFn: (status: string) => api.patch(`/api/incidents/${id}/status`, { status }),
    onSuccess: () => {
      toast.success("Status updated");
      void qc.invalidateQueries({ queryKey: ["incident", id] });
    },
  });
  const updateAssign = useMutation({
    mutationFn: () =>
      api.patch(`/api/incidents/${id}/assign`, {
        assigned_to_user_id: assignee.trim() || null,
      }),
    onSuccess: () => {
      toast.success("Assigned");
      void qc.invalidateQueries({ queryKey: ["incident", id] });
    },
  });
  const updateSummary = useMutation({
    mutationFn: () => api.patch(`/api/incidents/${id}/summary`, { summary }),
    onSuccess: () => {
      toast.success("Summary saved");
      void qc.invalidateQueries({ queryKey: ["incident", id] });
    },
  });

  const d = data ?? {};
  const alerts = toArray<Record<string, unknown>>(d.alerts);
  const events = toArray<Record<string, unknown>>(d.events);
  const alertIds = toArray<string>(d.alert_ids);
  const eventIds = toArray<string>(d.event_ids);
  const techniques = (d.mitre_techniques ?? d.techniques) as string[] | undefined;

  return (
    <div className="space-y-4">
      <Link
        to="/incidents"
        className="inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground"
      >
        <ArrowLeft className="h-4 w-4" /> Back to incidents
      </Link>
      <div className="flex flex-wrap items-center gap-3">
        <h1 className="text-xl font-semibold tracking-tight">{String(d.title ?? "Incident")}</h1>
        <SeverityBadge severity={(d.severity as string) ?? undefined} />
        <StatusBadge status={(d.status as string) ?? undefined} />
        <span className="text-xs text-muted-foreground">
          First seen {fmtRelative(d.first_seen_at as string)}
        </span>
      </div>

      <div className="grid gap-4 lg:grid-cols-3">
        <Card className="border-border/60 bg-card/60 lg:col-span-2">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm">AI Summary</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            <Textarea
              rows={6}
              value={summary}
              onChange={(e) => setSummary(e.target.value)}
              className="text-sm"
            />
            <Button
              size="sm"
              onClick={() => updateSummary.mutate()}
              disabled={updateSummary.isPending}
            >
              Save summary
            </Button>
          </CardContent>
        </Card>
        <Card className="border-border/60 bg-card/60">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm">Triage</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="space-y-1.5">
              <p className="text-xs text-muted-foreground">Status</p>
              <select
                value={(d.status as string) ?? "open"}
                onChange={(e) => updateStatus.mutate(e.target.value)}
                className="h-9 w-full rounded-md border border-input bg-background px-2 text-sm"
              >
                {["open", "investigating", "contained", "resolved", "false_positive"].map((s) => (
                  <option key={s} value={s}>
                    {s.replace("_", " ")}
                  </option>
                ))}
              </select>
            </div>
            <div className="space-y-1.5">
              <p className="text-xs text-muted-foreground">Assignee</p>
              <div className="flex gap-2">
                <Input value={assignee} onChange={(e) => setAssignee(e.target.value)} />
                <Button
                  size="sm"
                  onClick={() => updateAssign.mutate()}
                  disabled={updateAssign.isPending}
                >
                  Assign
                </Button>
              </div>
            </div>
            <div className="space-y-1.5">
              <p className="text-xs text-muted-foreground">MITRE</p>
              <MitreBadges techniques={techniques} />
            </div>
            {chain.data ? (
              <Link
                to="/attack-chains/$id"
                params={{
                  id: String(
                    (chain.data as Record<string, unknown>).id ??
                      (chain.data as Record<string, unknown>).chain_id ??
                      "",
                  ),
                }}
                className="block text-sm text-primary hover:underline"
              >
                View linked attack chain →
              </Link>
            ) : null}
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <Card className="border-border/60 bg-card/60">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm">
              Linked Alerts ({alerts.length || alertIds.length})
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            {alerts.length === 0 && alertIds.length === 0 ? (
              <p className="text-xs text-muted-foreground">No linked alerts.</p>
            ) : alerts.length === 0 ? (
              alertIds.map((alertId) => (
                <div
                  key={alertId}
                  className="rounded border border-border/60 bg-background/40 p-2 font-mono text-xs text-muted-foreground"
                >
                  {alertId}
                </div>
              ))
            ) : (
              alerts.map((a, i) => (
                <div
                  key={i}
                  className="flex items-center justify-between gap-3 rounded border border-border/60 bg-background/40 p-2 text-sm"
                >
                  <div className="min-w-0">
                    <p className="truncate">{String(a.title ?? "—")}</p>
                    <div className="mt-1 flex gap-2">
                      <SeverityBadge severity={a.severity as string} />
                      <StatusBadge status={a.status as string} />
                    </div>
                  </div>
                  <span className="shrink-0 text-xs text-muted-foreground">
                    {fmtRelative(a.created_at as string)}
                  </span>
                </div>
              ))
            )}
          </CardContent>
        </Card>
        <Card className="border-border/60 bg-card/60">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm">
              Linked Events ({events.length || eventIds.length})
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            {events.length === 0 && eventIds.length === 0 ? (
              <p className="text-xs text-muted-foreground">No linked events.</p>
            ) : events.length === 0 ? (
              eventIds.map((eventId) => (
                <div
                  key={eventId}
                  className="rounded border border-border/60 bg-background/40 p-2 font-mono text-xs text-muted-foreground"
                >
                  {eventId}
                </div>
              ))
            ) : (
              events.slice(0, 20).map((e, i) => (
                <div
                  key={i}
                  className="flex items-center justify-between gap-3 rounded border border-border/60 bg-background/40 p-2 text-sm"
                >
                  <div className="min-w-0">
                    <p className="truncate">{String(e.title ?? e.event_type ?? "—")}</p>
                    <p className="text-[10px] text-muted-foreground">{String(e.source ?? "")}</p>
                  </div>
                  <span className="shrink-0 text-xs text-muted-foreground">
                    {fmtRelative(e.timestamp as string)}
                  </span>
                </div>
              ))
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
