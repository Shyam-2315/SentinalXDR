import { createFileRoute } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { Activity } from "lucide-react";
import { api } from "@/lib/api";
import { toArray, fmtRelative } from "@/lib/format";
import { SeverityBadge } from "@/components/common/SeverityBadge";
import { EmptyState } from "@/components/common/EmptyState";
import { ErrorState, LoadingState } from "@/components/common/PageState";
import { JsonViewer } from "@/components/common/JsonViewer";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Sheet, SheetContent, SheetHeader, SheetTitle } from "@/components/ui/sheet";

export const Route = createFileRoute("/_app/events")({ component: EventsPage });

type Event = {
  id?: string;
  event_id?: string;
  timestamp?: string;
  source?: string;
  event_type?: string;
  severity?: string;
  title?: string;
  agent_id?: string;
  tags?: string[];
  description?: string;
  raw_event?: unknown;
  normalized_fields?: unknown;
};

function EventsPage() {
  const [q, setQ] = useState("");
  const [sev, setSev] = useState("");
  const [source, setSource] = useState("");
  const [eventType, setEventType] = useState("");
  const [agentId, setAgentId] = useState("");
  const [selected, setSelected] = useState<Event | null>(null);
  const selectedId = selected?.id ?? selected?.event_id ?? "";

  const query = useQuery({
    queryKey: ["events", q, sev, source, eventType, agentId],
    queryFn: () =>
      api.get<unknown>("/api/events", {
        query: {
          search: q || undefined,
          severity: sev || undefined,
          source: source || undefined,
          event_type: eventType || undefined,
          agent_id: agentId || undefined,
        },
      }),
  });
  const rows = toArray<Event>(query.data);
  const detail = useQuery({
    queryKey: ["event", selectedId],
    queryFn: () => api.get<Event>(`/api/events/${selectedId}`),
    enabled: !!selectedId,
  });
  const selectedEvent = detail.data ?? selected;

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-xl font-semibold tracking-tight">Events</h1>
        <p className="text-sm text-muted-foreground">
          Normalized telemetry from connected sensors.
        </p>
      </div>
      <div className="flex flex-wrap gap-2">
        <Input
          placeholder="Search title / type / source…"
          value={q}
          onChange={(e) => setQ(e.target.value)}
          className="max-w-xs"
        />
        <select
          value={sev}
          onChange={(e) => setSev(e.target.value)}
          className="h-9 rounded-md border border-input bg-card/60 px-3 text-sm"
        >
          <option value="">All severities</option>
          <option value="critical">Critical</option>
          <option value="high">High</option>
          <option value="medium">Medium</option>
          <option value="low">Low</option>
          <option value="info">Info</option>
        </select>
        <Input
          placeholder="Source"
          value={source}
          onChange={(e) => setSource(e.target.value)}
          className="max-w-[10rem]"
        />
        <Input
          placeholder="Event type"
          value={eventType}
          onChange={(e) => setEventType(e.target.value)}
          className="max-w-[12rem]"
        />
        <Input
          placeholder="Agent ID"
          value={agentId}
          onChange={(e) => setAgentId(e.target.value)}
          className="max-w-[14rem]"
        />
      </div>
      <Card className="border-border/60 bg-card/60">
        <CardContent className="p-0">
          {query.isLoading ? (
            <LoadingState label="Loading events" />
          ) : query.isError ? (
            <div className="p-6">
              <ErrorState error={query.error} onRetry={() => void query.refetch()} />
            </div>
          ) : rows.length === 0 ? (
            <div className="p-6">
              <EmptyState icon={Activity} title="No events found" />
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="bg-muted/40 text-xs uppercase tracking-wide text-muted-foreground">
                  <tr>
                    <th className="px-3 py-2 text-left">Time</th>
                    <th className="px-3 py-2 text-left">Severity</th>
                    <th className="px-3 py-2 text-left">Title</th>
                    <th className="px-3 py-2 text-left">Type</th>
                    <th className="px-3 py-2 text-left">Source</th>
                    <th className="px-3 py-2 text-left">Agent</th>
                    <th className="px-3 py-2 text-left">Tags</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border/60">
                  {rows.map((e) => {
                    const id = e.id ?? e.event_id ?? "";
                    return (
                      <tr
                        key={id}
                        className="cursor-pointer hover:bg-muted/20"
                        onClick={() => setSelected(e)}
                      >
                        <td className="px-3 py-2 text-xs text-muted-foreground">
                          {fmtRelative(e.timestamp)}
                        </td>
                        <td className="px-3 py-2">
                          <SeverityBadge severity={e.severity} />
                        </td>
                        <td className="px-3 py-2 font-medium">{e.title ?? "—"}</td>
                        <td className="px-3 py-2 text-muted-foreground">{e.event_type ?? "—"}</td>
                        <td className="px-3 py-2 text-muted-foreground">{e.source ?? "—"}</td>
                        <td className="px-3 py-2 font-mono text-xs text-muted-foreground">
                          {e.agent_id ?? "—"}
                        </td>
                        <td className="px-3 py-2">
                          <div className="flex flex-wrap gap-1">
                            {(e.tags ?? []).map((t, i) => (
                              <span
                                key={i}
                                className="rounded border border-border/60 bg-background/40 px-1.5 py-0.5 text-[10px] text-muted-foreground"
                              >
                                {t}
                              </span>
                            ))}
                          </div>
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
            <SheetTitle>{selectedEvent?.title ?? "Event"}</SheetTitle>
          </SheetHeader>
          {selectedEvent && (
            <div className="space-y-4 p-4 pt-2">
              <div className="flex items-center gap-2">
                <SeverityBadge severity={selectedEvent.severity} />
                <span className="text-xs text-muted-foreground">
                  {fmtRelative(selectedEvent.timestamp)}
                </span>
              </div>
              {selectedEvent.description && <p className="text-sm">{selectedEvent.description}</p>}
              <Section title="Normalized fields">
                <JsonViewer data={selectedEvent.normalized_fields ?? {}} />
              </Section>
              <Section title="Raw event">
                <JsonViewer data={selectedEvent.raw_event ?? {}} />
              </Section>
            </div>
          )}
        </SheetContent>
      </Sheet>
    </div>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div>
      <p className="mb-2 text-xs uppercase tracking-wide text-muted-foreground">{title}</p>
      {children}
    </div>
  );
}
