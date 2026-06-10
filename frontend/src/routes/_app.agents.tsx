import { createFileRoute } from "@tanstack/react-router";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Plus, Server, Copy, Power } from "lucide-react";
import { toast } from "sonner";
import { api } from "@/lib/api";
import { toArray, fmtRelative } from "@/lib/format";
import { StatusBadge } from "@/components/common/StatusBadge";
import { EmptyState } from "@/components/common/EmptyState";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";

export const Route = createFileRoute("/_app/agents")({ component: AgentsPage });

type Agent = {
  id?: string;
  agent_id?: string;
  name?: string;
  hostname?: string;
  os_type?: string;
  status?: string;
  agent_version?: string;
  ip_address?: string;
  last_seen_at?: string;
  tags?: string[];
};

function AgentsPage() {
  const qc = useQueryClient();
  const { data, isLoading } = useQuery({
    queryKey: ["agents"],
    queryFn: () => api.get<unknown>("/api/agents"),
  });
  const rows = toArray<Agent>(data);

  const disable = useMutation({
    mutationFn: (id: string) => api.post(`/api/agents/${id}/disable`),
    onSuccess: () => {
      toast.success("Agent disabled");
      void qc.invalidateQueries({ queryKey: ["agents"] });
    },
  });

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold tracking-tight">Agents</h1>
          <p className="text-sm text-muted-foreground">
            Endpoint sensors reporting telemetry into SentinelXDR.
          </p>
        </div>
        <RegisterAgentDialog
          onCreated={() => void qc.invalidateQueries({ queryKey: ["agents"] })}
        />
      </div>
      <Card className="border-border/60 bg-card/60">
        <CardContent className="p-0">
          {isLoading ? (
            <div className="p-6 text-sm text-muted-foreground">Loading agents…</div>
          ) : rows.length === 0 ? (
            <div className="p-6">
              <EmptyState
                icon={Server}
                title="No agents registered"
                description="Register your first sensor to start collecting telemetry."
              />
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="bg-muted/40 text-xs uppercase tracking-wide text-muted-foreground">
                  <tr>
                    <th className="px-3 py-2 text-left">Name</th>
                    <th className="px-3 py-2 text-left">Hostname</th>
                    <th className="px-3 py-2 text-left">OS</th>
                    <th className="px-3 py-2 text-left">Status</th>
                    <th className="px-3 py-2 text-left">Version</th>
                    <th className="px-3 py-2 text-left">IP</th>
                    <th className="px-3 py-2 text-left">Last seen</th>
                    <th className="px-3 py-2 text-left">Tags</th>
                    <th className="px-3 py-2"></th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border/60">
                  {rows.map((a) => {
                    const id = a.id ?? a.agent_id ?? "";
                    return (
                      <tr key={id} className="hover:bg-muted/20">
                        <td className="px-3 py-2 font-medium">{a.name ?? "—"}</td>
                        <td className="px-3 py-2 text-muted-foreground">{a.hostname ?? "—"}</td>
                        <td className="px-3 py-2 text-muted-foreground">{a.os_type ?? "—"}</td>
                        <td className="px-3 py-2">
                          <StatusBadge status={a.status} />
                        </td>
                        <td className="px-3 py-2 font-mono text-xs text-muted-foreground">
                          {a.agent_version ?? "—"}
                        </td>
                        <td className="px-3 py-2 font-mono text-xs text-muted-foreground">
                          {a.ip_address ?? "—"}
                        </td>
                        <td className="px-3 py-2 text-muted-foreground">
                          {fmtRelative(a.last_seen_at)}
                        </td>
                        <td className="px-3 py-2">
                          <div className="flex flex-wrap gap-1">
                            {(a.tags ?? []).map((t, i) => (
                              <span
                                key={i}
                                className="rounded border border-border/60 bg-background/40 px-1.5 py-0.5 text-[10px] text-muted-foreground"
                              >
                                {t}
                              </span>
                            ))}
                          </div>
                        </td>
                        <td className="px-3 py-2 text-right">
                          <Button
                            size="sm"
                            variant="ghost"
                            onClick={() => id && disable.mutate(id)}
                          >
                            <Power className="mr-1 h-3.5 w-3.5" /> Disable
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
    </div>
  );
}

function RegisterAgentDialog({ onCreated }: { onCreated: () => void }) {
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState({ name: "", hostname: "", os_type: "linux", tags: "" });
  const [apiKey, setApiKey] = useState<string | null>(null);

  const create = useMutation({
    mutationFn: () =>
      api.post<Record<string, unknown>>("/api/agents/register", {
        ...form,
        tags: form.tags
          .split(",")
          .map((t) => t.trim())
          .filter(Boolean),
      }),
    onSuccess: (res) => {
      const key = String(
        (res as Record<string, unknown>).api_key ??
          (res as Record<string, unknown>).agent_key ??
          "",
      );
      setApiKey(key || "registered");
      onCreated();
    },
  });

  function reset() {
    setApiKey(null);
    setForm({ name: "", hostname: "", os_type: "linux", tags: "" });
  }

  return (
    <Dialog
      open={open}
      onOpenChange={(o) => {
        setOpen(o);
        if (!o) reset();
      }}
    >
      <DialogTrigger asChild>
        <Button>
          <Plus className="mr-1 h-4 w-4" /> Register Agent
        </Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{apiKey ? "Agent registered" : "Register a new agent"}</DialogTitle>
        </DialogHeader>
        {apiKey ? (
          <div className="space-y-3">
            <p className="text-sm text-muted-foreground">
              Copy the one-time API key. It will not be shown again.
            </p>
            <div className="flex items-center gap-2 rounded-md border border-border bg-background/60 p-2 font-mono text-xs">
              <span className="flex-1 break-all">{apiKey}</span>
              <Button
                size="sm"
                variant="ghost"
                onClick={() => {
                  void navigator.clipboard.writeText(apiKey);
                  toast.success("Copied");
                }}
              >
                <Copy className="h-3.5 w-3.5" />
              </Button>
            </div>
            <DialogFooter>
              <Button onClick={() => setOpen(false)}>Done</Button>
            </DialogFooter>
          </div>
        ) : (
          <form
            onSubmit={(e) => {
              e.preventDefault();
              create.mutate();
            }}
            className="space-y-3"
          >
            <div className="space-y-1.5">
              <Label>Name</Label>
              <Input
                value={form.name}
                onChange={(e) => setForm({ ...form, name: e.target.value })}
                required
              />
            </div>
            <div className="space-y-1.5">
              <Label>Hostname</Label>
              <Input
                value={form.hostname}
                onChange={(e) => setForm({ ...form, hostname: e.target.value })}
                required
              />
            </div>
            <div className="space-y-1.5">
              <Label>OS Type</Label>
              <Input
                value={form.os_type}
                onChange={(e) => setForm({ ...form, os_type: e.target.value })}
              />
            </div>
            <div className="space-y-1.5">
              <Label>Tags (comma separated)</Label>
              <Input
                value={form.tags}
                onChange={(e) => setForm({ ...form, tags: e.target.value })}
                placeholder="prod, web-tier"
              />
            </div>
            <DialogFooter>
              <Button type="button" variant="ghost" onClick={() => setOpen(false)}>
                Cancel
              </Button>
              <Button type="submit" disabled={create.isPending}>
                {create.isPending ? "Registering…" : "Register"}
              </Button>
            </DialogFooter>
          </form>
        )}
      </DialogContent>
    </Dialog>
  );
}
