import { createFileRoute, Link } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import { Server, Wifi, Activity, Bell, AlertOctagon, GitBranch, Flame, Gauge } from "lucide-react";
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
} from "recharts";
import { api } from "@/lib/api";
import { fmtRelative, toArray } from "@/lib/format";
import { MetricCard } from "@/components/common/MetricCard";
import { SeverityBadge } from "@/components/common/SeverityBadge";
import { StatusBadge } from "@/components/common/StatusBadge";
import { MitreBadges } from "@/components/common/MitreBadges";
import { EmptyState } from "@/components/common/EmptyState";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export const Route = createFileRoute("/_app/dashboard")({
  component: DashboardPage,
});

type Summary = {
  total_agents?: number;
  online_agents?: number;
  total_events?: number;
  open_alerts?: number;
  open_incidents?: number;
  active_attack_chains?: number;
  critical_alerts?: number;
  risk_score_average?: number;
};

type Posture = {
  posture_score?: number;
  posture_label?: string;
  top_risks?: string[];
  recommended_actions?: string[];
};

function useDash<T>(key: string, path: string) {
  return useQuery<T>({ queryKey: ["dash", key], queryFn: () => api.get<T>(path) });
}

function DashboardPage() {
  const summary = useDash<Summary>("summary", "/api/dashboard/summary");
  const posture = useDash<Posture>("posture", "/api/dashboard/security-posture");
  const alerts = useDash<unknown>("alerts", "/api/dashboard/recent-alerts");
  const incidents = useDash<unknown>("incidents", "/api/dashboard/recent-incidents");
  const chains = useDash<unknown>("chains", "/api/dashboard/recent-attack-chains");
  const mitre = useDash<unknown>("mitre", "/api/dashboard/mitre-summary");
  const trends = useDash<unknown>("trends", "/api/dashboard/severity-trends");
  const agents = useDash<unknown>("agentHealth", "/api/dashboard/agent-health");

  const s = summary.data ?? {};
  const p = posture.data ?? {};
  const trendData = normalizeTrend(trends.data);
  const mitreData = normalizeMitre(mitre.data);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-semibold tracking-tight">SOC Dashboard</h1>
        <p className="text-sm text-muted-foreground">
          Live posture across telemetry, detections, and active threats.
        </p>
      </div>

      <div className="grid grid-cols-2 gap-3 md:grid-cols-4 xl:grid-cols-8">
        <MetricCard
          label="Total Agents"
          value={s.total_agents ?? 0}
          icon={Server}
          loading={summary.isLoading}
        />
        <MetricCard
          label="Online Agents"
          value={s.online_agents ?? 0}
          tone="success"
          icon={Wifi}
          loading={summary.isLoading}
        />
        <MetricCard
          label="Total Events"
          value={s.total_events ?? 0}
          icon={Activity}
          loading={summary.isLoading}
        />
        <MetricCard
          label="Open Alerts"
          value={s.open_alerts ?? 0}
          tone="warning"
          icon={Bell}
          loading={summary.isLoading}
        />
        <MetricCard
          label="Open Incidents"
          value={s.open_incidents ?? 0}
          tone="critical"
          icon={AlertOctagon}
          loading={summary.isLoading}
        />
        <MetricCard
          label="Active Chains"
          value={s.active_attack_chains ?? 0}
          tone="critical"
          icon={GitBranch}
          loading={summary.isLoading}
        />
        <MetricCard
          label="Critical Alerts"
          value={s.critical_alerts ?? 0}
          tone="critical"
          icon={Flame}
          loading={summary.isLoading}
        />
        <MetricCard
          label="Avg Risk Score"
          value={s.risk_score_average ?? 0}
          tone="info"
          icon={Gauge}
          loading={summary.isLoading}
        />
      </div>

      <div className="grid gap-4 lg:grid-cols-3">
        <Card className="border-border/60 bg-card/60 lg:col-span-2">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm">Severity Trend · last 7 days</CardTitle>
          </CardHeader>
          <CardContent className="h-64 p-2">
            {trendData.length === 0 ? (
              <EmptyState title="No trend data" />
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={trendData}>
                  <defs>
                    <linearGradient id="gCrit" x1="0" x2="0" y1="0" y2="1">
                      <stop offset="0%" stopColor="#ef4444" stopOpacity={0.6} />
                      <stop offset="100%" stopColor="#ef4444" stopOpacity={0} />
                    </linearGradient>
                    <linearGradient id="gHigh" x1="0" x2="0" y1="0" y2="1">
                      <stop offset="0%" stopColor="#f97316" stopOpacity={0.5} />
                      <stop offset="100%" stopColor="#f97316" stopOpacity={0} />
                    </linearGradient>
                    <linearGradient id="gMed" x1="0" x2="0" y1="0" y2="1">
                      <stop offset="0%" stopColor="#eab308" stopOpacity={0.4} />
                      <stop offset="100%" stopColor="#eab308" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" />
                  <XAxis dataKey="date" stroke="rgba(255,255,255,0.4)" fontSize={11} />
                  <YAxis stroke="rgba(255,255,255,0.4)" fontSize={11} />
                  <Tooltip
                    contentStyle={{
                      background: "#0b1220",
                      border: "1px solid rgba(255,255,255,0.1)",
                      fontSize: 12,
                    }}
                  />
                  <Area
                    type="monotone"
                    dataKey="critical"
                    stroke="#ef4444"
                    fill="url(#gCrit)"
                    stackId="1"
                  />
                  <Area
                    type="monotone"
                    dataKey="high"
                    stroke="#f97316"
                    fill="url(#gHigh)"
                    stackId="1"
                  />
                  <Area
                    type="monotone"
                    dataKey="medium"
                    stroke="#eab308"
                    fill="url(#gMed)"
                    stackId="1"
                  />
                </AreaChart>
              </ResponsiveContainer>
            )}
          </CardContent>
        </Card>

        <Card className="border-border/60 bg-card/60">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm">Security Posture</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-baseline gap-3">
              <p className="text-4xl font-semibold tabular-nums text-foreground">
                {p.posture_score ?? "—"}
              </p>
              <SeverityBadge severity={mapPostureSeverity(p.posture_label)} />
              <span className="text-sm text-muted-foreground">{p.posture_label}</span>
            </div>
            <div>
              <p className="mb-1 text-xs uppercase tracking-wide text-muted-foreground">
                Top Risks
              </p>
              <ul className="space-y-1 text-sm">
                {(p.top_risks ?? []).slice(0, 5).map((r, i) => (
                  <li key={i} className="flex gap-2 text-foreground">
                    <span className="text-[color:var(--sev-high)]">•</span>
                    {r}
                  </li>
                ))}
                {(!p.top_risks || p.top_risks.length === 0) && (
                  <li className="text-xs text-muted-foreground">No risks reported</li>
                )}
              </ul>
            </div>
            <div>
              <p className="mb-1 text-xs uppercase tracking-wide text-muted-foreground">
                Recommended Actions
              </p>
              <ul className="space-y-1 text-sm">
                {(p.recommended_actions ?? []).slice(0, 5).map((a, i) => (
                  <li key={i} className="flex gap-2 text-foreground">
                    <span className="text-emerald-400">→</span>
                    {a}
                  </li>
                ))}
                {(!p.recommended_actions || p.recommended_actions.length === 0) && (
                  <li className="text-xs text-muted-foreground">No actions queued</li>
                )}
              </ul>
            </div>
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-4 lg:grid-cols-3">
        <Card className="border-border/60 bg-card/60 lg:col-span-2">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm">MITRE ATT&amp;CK Summary</CardTitle>
          </CardHeader>
          <CardContent>
            {mitreData.length === 0 ? (
              <EmptyState title="No MITRE coverage yet" />
            ) : (
              <div className="grid grid-cols-2 gap-2 md:grid-cols-3">
                {mitreData.slice(0, 12).map((t, i) => (
                  <div key={i} className="rounded-md border border-border/60 bg-background/40 p-3">
                    <p className="font-mono text-xs text-blue-300">{t.id}</p>
                    <p className="truncate text-sm text-foreground">{t.name}</p>
                    <p className="text-xs text-muted-foreground">{t.count} hits</p>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
        <Card className="border-border/60 bg-card/60">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm">Agent Health</CardTitle>
          </CardHeader>
          <CardContent>
            <AgentHealth data={agents.data} />
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-4 lg:grid-cols-3">
        <RecentTable
          title="Recent Alerts"
          to="/alerts"
          rows={toArray<Record<string, unknown>>(alerts.data)}
          kind="alert"
        />
        <RecentTable
          title="Recent Incidents"
          to="/incidents"
          rows={toArray<Record<string, unknown>>(incidents.data)}
          kind="incident"
        />
        <RecentTable
          title="Recent Attack Chains"
          to="/attack-chains"
          rows={toArray<Record<string, unknown>>(chains.data)}
          kind="chain"
        />
      </div>
    </div>
  );
}

function mapPostureSeverity(label?: string) {
  const v = (label ?? "").toLowerCase();
  if (v.includes("crit")) return "critical";
  if (v.includes("poor") || v.includes("high")) return "high";
  if (v.includes("fair") || v.includes("med")) return "medium";
  if (v.includes("good")) return "low";
  return "info";
}

function normalizeTrend(
  d: unknown,
): { date: string; critical: number; high: number; medium: number; low: number }[] {
  const arr = toArray<Record<string, unknown>>(d);
  return arr.map((r) => ({
    date: String(r.date ?? r.day ?? r.bucket ?? ""),
    critical: Number(r.critical ?? 0),
    high: Number(r.high ?? 0),
    medium: Number(r.medium ?? 0),
    low: Number(r.low ?? 0),
  }));
}

function normalizeMitre(d: unknown): { id: string; name: string; count: number }[] {
  const tactics = toArray<Record<string, unknown>>(d);
  return tactics.flatMap((tactic) =>
    toArray<Record<string, unknown>>(tactic.techniques).map((technique) => ({
      id: String(technique.technique ?? technique.technique_id ?? technique.id ?? "T?"),
      name: String(tactic.tactic ?? technique.technique_name ?? technique.name ?? ""),
      count: Number(technique.count ?? technique.hits ?? 0),
    })),
  );
}

function AgentHealth({ data }: { data: unknown }) {
  const obj = (data ?? {}) as Record<string, unknown>;
  const byStatus = toArray<Record<string, unknown>>(obj.by_status);
  const statusCount = (status: string) =>
    Number(byStatus.find((item) => item.status === status)?.count ?? 0);
  const online = Number(obj.online ?? statusCount("online"));
  const offline = Number(obj.offline ?? statusCount("offline"));
  const total = Number(obj.total ?? online + offline);
  const pct = total ? Math.round((online / total) * 100) : 0;
  return (
    <div className="space-y-3">
      <div className="flex items-end justify-between">
        <p className="text-3xl font-semibold tabular-nums">{pct}%</p>
        <p className="text-xs text-muted-foreground">
          {online} / {total} online
        </p>
      </div>
      <div className="h-2 overflow-hidden rounded-full bg-muted">
        <div className="h-full bg-emerald-400" style={{ width: `${pct}%` }} />
      </div>
      <div className="grid grid-cols-2 gap-2 text-xs">
        <div className="rounded border border-border/60 p-2">
          <p className="text-muted-foreground">Online</p>
          <p className="text-emerald-400">{online}</p>
        </div>
        <div className="rounded border border-border/60 p-2">
          <p className="text-muted-foreground">Offline</p>
          <p className="text-zinc-300">{offline}</p>
        </div>
      </div>
    </div>
  );
}

function RecentTable({
  title,
  to,
  rows,
  kind,
}: {
  title: string;
  to: "/alerts" | "/incidents" | "/attack-chains";
  rows: Record<string, unknown>[];
  kind: "alert" | "incident" | "chain";
}) {
  return (
    <Card className="border-border/60 bg-card/60">
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-sm">{title}</CardTitle>
        <Link to={to} className="text-xs text-primary hover:underline">
          View all
        </Link>
      </CardHeader>
      <CardContent className="px-0">
        {rows.length === 0 ? (
          <div className="px-4 pb-4">
            <EmptyState title="Nothing recent" />
          </div>
        ) : (
          <ul className="divide-y divide-border/60">
            {rows.slice(0, 6).map((r, i) => (
              <li key={i} className="flex items-center justify-between gap-3 px-4 py-2.5 text-sm">
                <div className="min-w-0">
                  <p className="truncate text-foreground">
                    {String(r.title ?? r.name ?? r.summary ?? "—")}
                  </p>
                  <div className="mt-1 flex items-center gap-2">
                    <SeverityBadge severity={(r.severity as string) ?? undefined} />
                    {kind !== "chain" && <StatusBadge status={(r.status as string) ?? undefined} />}
                    <MitreBadges
                      techniques={(r.mitre_techniques ?? r.techniques) as string[] | undefined}
                    />
                  </div>
                </div>
                <p className="shrink-0 text-xs text-muted-foreground">
                  {fmtRelative((r.created_at ?? r.first_seen_at) as string)}
                </p>
              </li>
            ))}
          </ul>
        )}
      </CardContent>
    </Card>
  );
}
