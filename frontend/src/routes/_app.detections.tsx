import { createFileRoute } from "@tanstack/react-router";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Plus, ShieldAlert } from "lucide-react";
import { toast } from "sonner";
import { api } from "@/lib/api";
import { toArray } from "@/lib/format";
import { SeverityBadge } from "@/components/common/SeverityBadge";
import { StatusBadge } from "@/components/common/StatusBadge";
import { MitreBadges } from "@/components/common/MitreBadges";
import { EmptyState } from "@/components/common/EmptyState";
import { ErrorState, LoadingState } from "@/components/common/PageState";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";

export const Route = createFileRoute("/_app/detections")({ component: DetectionsPage });

type Rule = {
  id?: string;
  rule_id?: string;
  name?: string;
  severity?: string;
  source?: string;
  event_type?: string;
  mitre_techniques?: string[];
  enabled?: boolean;
  is_custom?: boolean;
};

type DetectionResult = {
  id?: string;
  rule_name?: string;
  severity?: string;
  title?: string;
  event_id?: string;
  agent_id?: string;
  mitre_techniques?: string[];
  created_at?: string;
};

function DetectionsPage() {
  const qc = useQueryClient();
  const query = useQuery({
    queryKey: ["detections", "rules"],
    queryFn: () => api.get<unknown>("/api/detections/rules"),
  });
  const results = useQuery({
    queryKey: ["detections", "results"],
    queryFn: () => api.get<unknown>("/api/detections/results"),
  });
  const rows = toArray<Rule>(query.data);
  const resultRows = toArray<DetectionResult>(results.data);

  const toggle = useMutation({
    mutationFn: ({ id, enable }: { id: string; enable: boolean }) =>
      api.post(`/api/detections/rules/${id}/${enable ? "enable" : "disable"}`),
    onSuccess: () => {
      toast.success("Rule updated");
      void qc.invalidateQueries({ queryKey: ["detections", "rules"] });
    },
  });

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold tracking-tight">Detection Rules</h1>
          <p className="text-sm text-muted-foreground">
            Built-in and custom detections evaluated against incoming events.
          </p>
        </div>
        <CreateRuleDialog
          onCreated={() => void qc.invalidateQueries({ queryKey: ["detections", "rules"] })}
        />
      </div>
      <Card className="border-border/60 bg-card/60">
        <CardContent className="p-0">
          {query.isLoading ? (
            <LoadingState label="Loading rules" />
          ) : query.isError ? (
            <div className="p-6">
              <ErrorState error={query.error} onRetry={() => void query.refetch()} />
            </div>
          ) : rows.length === 0 ? (
            <div className="p-6">
              <EmptyState icon={ShieldAlert} title="No detection rules" />
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="bg-muted/40 text-xs uppercase tracking-wide text-muted-foreground">
                  <tr>
                    <th className="px-3 py-2 text-left">Name</th>
                    <th className="px-3 py-2 text-left">Severity</th>
                    <th className="px-3 py-2 text-left">Source</th>
                    <th className="px-3 py-2 text-left">Event Type</th>
                    <th className="px-3 py-2 text-left">MITRE</th>
                    <th className="px-3 py-2 text-left">Status</th>
                    <th className="px-3 py-2"></th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border/60">
                  {rows.map((r) => {
                    const id = r.id ?? r.rule_id ?? "";
                    return (
                      <tr key={id} className="hover:bg-muted/20">
                        <td className="px-3 py-2">
                          <p className="font-medium">{r.name ?? "—"}</p>
                          <p className="text-[10px] uppercase text-muted-foreground">
                            {r.is_custom ? "custom" : "built-in"}
                          </p>
                        </td>
                        <td className="px-3 py-2">
                          <SeverityBadge severity={r.severity} />
                        </td>
                        <td className="px-3 py-2 text-muted-foreground">{r.source ?? "—"}</td>
                        <td className="px-3 py-2 text-muted-foreground">{r.event_type ?? "—"}</td>
                        <td className="px-3 py-2">
                          <MitreBadges techniques={r.mitre_techniques} />
                        </td>
                        <td className="px-3 py-2">
                          <StatusBadge status={r.enabled ? "enabled" : "disabled"} />
                        </td>
                        <td className="px-3 py-2 text-right">
                          <Button
                            size="sm"
                            variant="ghost"
                            onClick={() => id && toggle.mutate({ id, enable: !r.enabled })}
                          >
                            {r.enabled ? "Disable" : "Enable"}
                          </Button>
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
      <Card className="border-border/60 bg-card/60">
        <CardContent className="p-0">
          <div className="border-b border-border/60 px-4 py-3">
            <h2 className="text-sm font-semibold">Detection Results</h2>
            <p className="text-xs text-muted-foreground">
              Recent rule matches created from ingested events.
            </p>
          </div>
          {results.isLoading ? (
            <LoadingState label="Loading results" />
          ) : results.isError ? (
            <div className="p-6">
              <ErrorState error={results.error} onRetry={() => void results.refetch()} />
            </div>
          ) : resultRows.length === 0 ? (
            <div className="p-6">
              <EmptyState title="No detection results" />
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
                  </tr>
                </thead>
                <tbody className="divide-y divide-border/60">
                  {resultRows.map((result) => (
                    <tr key={result.id} className="hover:bg-muted/20">
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
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

function CreateRuleDialog({ onCreated }: { onCreated: () => void }) {
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState({
    name: "",
    severity: "medium",
    event_type: "",
    source: "",
    description: "",
    mitre_tactics: "",
    mitre_techniques: "",
    conditions:
      '{\n  "all": [\n    { "field": "normalized_fields.command_line", "operator": "contains", "value": "demo" }\n  ]\n}',
  });
  const [error, setError] = useState<string | null>(null);

  const create = useMutation({
    mutationFn: () => {
      let conditions: unknown;
      try {
        conditions = JSON.parse(form.conditions);
      } catch {
        throw new Error("Invalid JSON in conditions");
      }
      return api.post("/api/detections/rules", {
        name: form.name,
        description: form.description || form.name,
        severity: form.severity,
        event_type: form.event_type,
        source: form.source,
        mitre_tactics: form.mitre_tactics
          .split(",")
          .map((s) => s.trim())
          .filter(Boolean),
        mitre_techniques: form.mitre_techniques
          .split(",")
          .map((s) => s.trim())
          .filter(Boolean),
        tags: ["custom"],
        conditions,
      });
    },
    onSuccess: () => {
      toast.success("Rule created");
      onCreated();
      setOpen(false);
    },
    onError: (e: unknown) => setError((e as Error).message),
  });

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button>
          <Plus className="mr-1 h-4 w-4" /> New Rule
        </Button>
      </DialogTrigger>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle>Create custom detection rule</DialogTitle>
        </DialogHeader>
        <form
          onSubmit={(e) => {
            e.preventDefault();
            setError(null);
            create.mutate();
          }}
          className="space-y-3"
        >
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1.5">
              <Label>Name</Label>
              <Input
                value={form.name}
                onChange={(e) => setForm({ ...form, name: e.target.value })}
                required
              />
            </div>
            <div className="space-y-1.5">
              <Label>Severity</Label>
              <select
                value={form.severity}
                onChange={(e) => setForm({ ...form, severity: e.target.value })}
                className="h-9 w-full rounded-md border border-input bg-background px-3 text-sm"
              >
                <option value="critical">Critical</option>
                <option value="high">High</option>
                <option value="medium">Medium</option>
                <option value="low">Low</option>
                <option value="info">Info</option>
              </select>
            </div>
            <div className="space-y-1.5">
              <Label>Event type</Label>
              <Input
                value={form.event_type}
                onChange={(e) => setForm({ ...form, event_type: e.target.value })}
                required
              />
            </div>
            <div className="space-y-1.5">
              <Label>Source</Label>
              <Input
                value={form.source}
                onChange={(e) => setForm({ ...form, source: e.target.value })}
                required
                placeholder="linux"
              />
            </div>
          </div>
          <div className="space-y-1.5">
            <Label>Description</Label>
            <Input
              value={form.description}
              onChange={(e) => setForm({ ...form, description: e.target.value })}
              placeholder="What this rule detects"
            />
          </div>
          <div className="space-y-1.5">
            <Label>MITRE tactics (comma separated)</Label>
            <Input
              value={form.mitre_tactics}
              onChange={(e) => setForm({ ...form, mitre_tactics: e.target.value })}
              placeholder="Execution"
            />
          </div>
          <div className="space-y-1.5">
            <Label>MITRE techniques (comma separated)</Label>
            <Input
              value={form.mitre_techniques}
              onChange={(e) => setForm({ ...form, mitre_techniques: e.target.value })}
              placeholder="T1059, T1055"
            />
          </div>
          <div className="space-y-1.5">
            <Label>Conditions (JSON)</Label>
            <Textarea
              rows={10}
              className="font-mono text-xs"
              value={form.conditions}
              onChange={(e) => setForm({ ...form, conditions: e.target.value })}
            />
          </div>
          {error && <p className="text-xs text-[color:var(--sev-critical)]">{error}</p>}
          <DialogFooter>
            <Button type="button" variant="ghost" onClick={() => setOpen(false)}>
              Cancel
            </Button>
            <Button type="submit" disabled={create.isPending}>
              {create.isPending ? "Saving…" : "Create"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
