import { createFileRoute, Link } from "@tanstack/react-router";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useMemo } from "react";
import { ArrowLeft, Target } from "lucide-react";
import { toast } from "sonner";
import { api } from "@/lib/api";
import { fmtDate, fmtRelative, toArray } from "@/lib/format";
import { SeverityBadge } from "@/components/common/SeverityBadge";
import { StatusBadge } from "@/components/common/StatusBadge";
import { MitreBadges } from "@/components/common/MitreBadges";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export const Route = createFileRoute("/_app/attack-chains/$id")({ component: ChainDetail });

type Node = { id: string; label?: string; type?: string; x?: number; y?: number };
type Edge = { source: string; target: string; label?: string; relationship?: string };

function ChainDetail() {
  const { id } = Route.useParams();
  const qc = useQueryClient();
  const { data } = useQuery({
    queryKey: ["chain", id],
    queryFn: () => api.get<Record<string, unknown>>(`/api/attack-chains/${id}`),
  });
  const updateStatus = useMutation({
    mutationFn: (status: string) => api.patch(`/api/attack-chains/${id}/status`, { status }),
    onSuccess: () => {
      toast.success("Chain updated");
      void qc.invalidateQueries({ queryKey: ["chain", id] });
    },
  });

  const d = data ?? {};
  const graph = (d.graph ?? {}) as Record<string, unknown>;
  const nodes = toArray<Node>(graph.nodes ?? d.nodes);
  const edges = toArray<Edge>(graph.edges ?? d.edges);
  const timeline = toArray<Record<string, unknown>>(d.timeline ?? d.events);
  const phases = toArray<string>(d.kill_chain_phases ?? d.phases);
  const actions = (d.recommended_actions as string[] | undefined) ?? [];

  return (
    <div className="space-y-4">
      <Link
        to="/attack-chains"
        className="inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground"
      >
        <ArrowLeft className="h-4 w-4" /> Back to attack chains
      </Link>
      <div className="flex flex-wrap items-center gap-3">
        <h1 className="text-xl font-semibold tracking-tight">
          {String(d.title ?? "Attack Chain")}
        </h1>
        <SeverityBadge severity={(d.severity as string) ?? undefined} />
        <StatusBadge status={(d.status as string) ?? undefined} />
        <select
          value={(d.status as string) ?? "active"}
          onChange={(e) => updateStatus.mutate(e.target.value)}
          className="h-8 rounded-md border border-input bg-background px-2 text-xs"
        >
          {["active", "contained", "resolved"].map((s) => (
            <option key={s} value={s}>
              {s.replace("_", " ")}
            </option>
          ))}
        </select>
      </div>

      <div className="grid gap-4 lg:grid-cols-3">
        <Card className="border-border/60 bg-card/60 lg:col-span-2">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm">Threat Story</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="whitespace-pre-line text-sm leading-relaxed text-foreground/90">
              {String(d.story ?? d.threat_story ?? d.summary ?? "No narrative available.")}
            </p>
          </CardContent>
        </Card>
        <div className="space-y-4">
          <div className="grid grid-cols-2 gap-3">
            <Card className="border-border/60 bg-card/60">
              <CardContent className="p-3">
                <p className="text-[10px] uppercase text-muted-foreground">Risk</p>
                <p className="text-2xl font-semibold text-[color:var(--sev-critical)]">
                  {String(d.risk_score ?? 0)}
                </p>
              </CardContent>
            </Card>
            <Card className="border-border/60 bg-card/60">
              <CardContent className="p-3">
                <p className="text-[10px] uppercase text-muted-foreground">Confidence</p>
                <p className="text-2xl font-semibold text-blue-300">
                  {String(d.confidence_score ?? 0)}
                </p>
              </CardContent>
            </Card>
          </div>
          <Card className="border-border/60 bg-card/60">
            <CardHeader className="pb-2">
              <CardTitle className="text-sm">Recommended Actions</CardTitle>
            </CardHeader>
            <CardContent>
              {actions.length === 0 ? (
                <p className="text-xs text-muted-foreground">None.</p>
              ) : (
                <ul className="space-y-1 text-sm">
                  {actions.map((a, i) => (
                    <li key={i} className="flex gap-2">
                      <span className="text-emerald-400">→</span>
                      {a}
                    </li>
                  ))}
                </ul>
              )}
            </CardContent>
          </Card>
        </div>
      </div>

      <Card className="border-border/60 bg-card/60">
        <CardHeader className="pb-2">
          <CardTitle className="text-sm">Attack Graph</CardTitle>
        </CardHeader>
        <CardContent>
          <GraphView nodes={nodes} edges={edges} />
        </CardContent>
      </Card>

      <div className="grid gap-4 lg:grid-cols-2">
        <Card className="border-border/60 bg-card/60">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm">Kill Chain Phases</CardTitle>
          </CardHeader>
          <CardContent>
            {phases.length === 0 ? (
              <p className="text-xs text-muted-foreground">No phases.</p>
            ) : (
              <ol className="space-y-2">
                {phases.map((p, i) => (
                  <li
                    key={i}
                    className="flex items-center gap-3 rounded border border-border/60 bg-background/40 p-2 text-sm"
                  >
                    <span className="grid h-6 w-6 place-items-center rounded-full bg-[color:var(--sev-critical)]/20 text-[10px] text-[color:var(--sev-critical)]">
                      {i + 1}
                    </span>
                    <div className="flex-1">
                      <p className="font-medium">{String(p).replaceAll("_", " ")}</p>
                    </div>
                  </li>
                ))}
              </ol>
            )}
          </CardContent>
        </Card>
        <Card className="border-border/60 bg-card/60">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm">Timeline</CardTitle>
          </CardHeader>
          <CardContent>
            {timeline.length === 0 ? (
              <p className="text-xs text-muted-foreground">No events.</p>
            ) : (
              <ol className="relative space-y-3 border-l border-border/60 pl-4">
                {timeline.map((t, i) => (
                  <li key={i} className="relative">
                    <span className="absolute -left-[21px] top-1.5 h-2.5 w-2.5 rounded-full bg-[color:var(--sev-high)]" />
                    <p className="text-sm font-medium">
                      {String(t.title ?? t.event_type ?? "Event")}
                    </p>
                    <p className="text-xs text-muted-foreground">
                      {fmtDate(t.timestamp as string)} · {fmtRelative(t.timestamp as string)}
                    </p>
                    {t.description ? <p className="mt-1 text-xs">{String(t.description)}</p> : null}
                  </li>
                ))}
              </ol>
            )}
          </CardContent>
        </Card>
      </div>

      {d.incident_id ? (
        <Card className="border-border/60 bg-card/60">
          <CardContent className="flex items-center justify-between p-4">
            <div className="flex items-center gap-2 text-sm">
              <Target className="h-4 w-4 text-primary" /> Linked incident
            </div>
            <Link
              to="/incidents/$id"
              params={{ id: String(d.incident_id) }}
              className="text-sm text-primary hover:underline"
            >
              Open incident →
            </Link>
          </CardContent>
        </Card>
      ) : null}
    </div>
  );
}

function GraphView({ nodes, edges }: { nodes: Node[]; edges: Edge[] }) {
  const positioned = useMemo(() => {
    const W = 720,
      H = 320,
      pad = 40;
    if (nodes.length === 0) return { nodes: [], W, H };
    const cols = Math.ceil(Math.sqrt(nodes.length));
    const step = (W - pad * 2) / Math.max(cols - 1, 1);
    return {
      W,
      H,
      nodes: nodes.map((n, i) => {
        const row = Math.floor(i / cols);
        const col = i % cols;
        return {
          ...n,
          x: n.x ?? pad + col * step,
          y: n.y ?? pad + row * 70 + 20,
        };
      }),
    };
  }, [nodes]);
  if (nodes.length === 0) return <p className="text-xs text-muted-foreground">No graph data.</p>;
  const map = new Map(positioned.nodes.map((n) => [n.id, n]));
  return (
    <div className="overflow-auto">
      <svg
        width={positioned.W}
        height={positioned.H}
        className="rounded-md border border-border/60 bg-background/40"
      >
        {edges.map((e, i) => {
          const a = map.get(e.source);
          const b = map.get(e.target);
          if (!a || !b) return null;
          return (
            <line
              key={i}
              x1={a.x}
              y1={a.y}
              x2={b.x}
              y2={b.y}
              stroke="rgba(239,68,68,0.5)"
              strokeWidth={1.5}
              markerEnd="url(#arrow)"
            />
          );
        })}
        <defs>
          <marker id="arrow" markerWidth={8} markerHeight={8} refX={6} refY={4} orient="auto">
            <path d="M0,0 L8,4 L0,8 z" fill="rgba(239,68,68,0.7)" />
          </marker>
        </defs>
        {positioned.nodes.map((n) => (
          <g key={n.id} transform={`translate(${n.x},${n.y})`}>
            <rect
              x={-60}
              y={-16}
              width={120}
              height={32}
              rx={6}
              className="fill-[color:var(--card)] stroke-[color:var(--border)]"
            />
            <text textAnchor="middle" dy={4} className="fill-foreground text-[11px]">
              {n.label ?? n.id}
            </text>
          </g>
        ))}
      </svg>
    </div>
  );
}
