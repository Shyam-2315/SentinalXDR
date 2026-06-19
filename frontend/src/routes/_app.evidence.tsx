import { createFileRoute } from "@tanstack/react-router";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Archive,
  Download,
  FileCheck2,
  FolderLock,
  Link2,
  RotateCcw,
  ShieldCheck,
  Upload,
  Unlink,
} from "lucide-react";
import { FormEvent, useMemo, useState } from "react";
import { toast } from "sonner";
import { EmptyState } from "@/components/common/EmptyState";
import { ErrorState, LoadingState } from "@/components/common/PageState";
import { StatusBadge } from "@/components/common/StatusBadge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { Textarea } from "@/components/ui/textarea";
import { useAuth } from "@/context/AuthContext";
import { fmtDate, fmtRelative, toArray } from "@/lib/format";
import { sentinelApi } from "@/lib/sentinelxdr-api";

export const Route = createFileRoute("/_app/evidence")({ component: EvidencePage });

type Evidence = {
  id: string;
  organization_id: string;
  incident_id?: string | null;
  uploaded_by_user_id: string;
  uploaded_by_email: string;
  filename: string;
  original_filename: string;
  content_type: string;
  size_bytes: number;
  sha256: string;
  description?: string | null;
  tags: string[];
  status: "active" | "archived";
  created_at: string;
  updated_at: string;
  last_verified_at?: string | null;
  verification_status: "verified" | "failed" | "not_verified";
};

type CustodyEvent = {
  id: string;
  action: string;
  actor_email?: string | null;
  description: string;
  metadata: Record<string, unknown>;
  created_at: string;
};

function EvidencePage() {
  const queryClient = useQueryClient();
  const { user } = useAuth();
  const [uploadOpen, setUploadOpen] = useState(false);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [tag, setTag] = useState("");
  const [status, setStatus] = useState("");
  const [verification, setVerification] = useState("");

  const canWrite = user?.role !== "VIEWER";
  const canAdmin = user?.role === "ORG_ADMIN" || user?.role === "SUPER_ADMIN";

  const evidenceQuery = useQuery({
    queryKey: ["evidence", { tag, status, verification }],
    queryFn: () =>
      sentinelApi.listEvidence({
        tag: tag || undefined,
        status: status || undefined,
        verification_status: verification || undefined,
      }),
  });
  const rows = toArray<Evidence>(evidenceQuery.data);

  const detail = useQuery({
    queryKey: ["evidence", selectedId],
    queryFn: () => sentinelApi.getEvidence(selectedId ?? ""),
    enabled: Boolean(selectedId),
  });
  const selected = detail.data as Evidence | undefined;

  const custody = useQuery({
    queryKey: ["evidence", selectedId, "custody"],
    queryFn: () => sentinelApi.getEvidenceCustody(selectedId ?? ""),
    enabled: Boolean(selectedId),
  });
  const custodyRows = toArray<CustodyEvent>(custody.data);

  function invalidateEvidence() {
    void queryClient.invalidateQueries({ queryKey: ["evidence"] });
  }

  const verifyMutation = useMutation({
    mutationFn: (id: string) => sentinelApi.verifyEvidence(id),
    onSuccess: () => {
      toast.success("Evidence verified");
      invalidateEvidence();
    },
  });
  const archiveMutation = useMutation({
    mutationFn: (id: string) => sentinelApi.archiveEvidence(id),
    onSuccess: () => {
      toast.success("Evidence archived");
      invalidateEvidence();
    },
  });
  const restoreMutation = useMutation({
    mutationFn: (id: string) => sentinelApi.restoreEvidence(id),
    onSuccess: () => {
      toast.success("Evidence restored");
      invalidateEvidence();
    },
  });
  const linkMutation = useMutation({
    mutationFn: ({ id, incidentId }: { id: string; incidentId: string }) =>
      sentinelApi.linkEvidence(id, incidentId),
    onSuccess: () => {
      toast.success("Evidence linked");
      invalidateEvidence();
    },
  });
  const unlinkMutation = useMutation({
    mutationFn: (id: string) => sentinelApi.unlinkEvidence(id),
    onSuccess: () => {
      toast.success("Evidence unlinked");
      invalidateEvidence();
    },
  });
  const downloadMutation = useMutation({
    mutationFn: (id: string) => sentinelApi.downloadEvidence(id),
    onSuccess: ({ blob, filename }) => {
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = filename;
      anchor.click();
      URL.revokeObjectURL(url);
      invalidateEvidence();
    },
  });

  const count = useMemo(() => {
    const data = evidenceQuery.data as Record<string, unknown> | undefined;
    return Number(data?.count ?? rows.length);
  }, [evidenceQuery.data, rows.length]);

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold tracking-tight">Evidence Vault</h1>
          <p className="text-sm text-muted-foreground">
            Digital evidence, integrity status, and chain of custody.
          </p>
        </div>
        {canWrite ? (
          <Button onClick={() => setUploadOpen(true)}>
            <Upload className="h-4 w-4" />
            Upload
          </Button>
        ) : null}
      </div>

      <Card className="border-border/60 bg-card/60">
        <CardContent className="space-y-3 p-4">
          <div className="grid gap-2 md:grid-cols-4">
            <Input
              value={tag}
              onChange={(event) => setTag(event.target.value)}
              placeholder="Filter by tag"
            />
            <select
              value={status}
              onChange={(event) => setStatus(event.target.value)}
              className="h-9 rounded-md border border-input bg-background px-2 text-sm"
            >
              <option value="">All statuses</option>
              <option value="active">Active</option>
              <option value="archived">Archived</option>
            </select>
            <select
              value={verification}
              onChange={(event) => setVerification(event.target.value)}
              className="h-9 rounded-md border border-input bg-background px-2 text-sm"
            >
              <option value="">All verification</option>
              <option value="verified">Verified</option>
              <option value="failed">Failed</option>
              <option value="not_verified">Not verified</option>
            </select>
            <div className="flex items-center justify-end text-xs text-muted-foreground">
              {count} item{count === 1 ? "" : "s"}
            </div>
          </div>

          {evidenceQuery.isLoading ? (
            <LoadingState label="Loading evidence" />
          ) : evidenceQuery.isError ? (
            <ErrorState error={evidenceQuery.error} onRetry={() => void evidenceQuery.refetch()} />
          ) : rows.length === 0 ? (
            <EmptyState icon={FolderLock} title="No evidence" />
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="bg-muted/40 text-xs uppercase tracking-wide text-muted-foreground">
                  <tr>
                    <th className="px-3 py-2 text-left">Filename</th>
                    <th className="px-3 py-2 text-left">Incident</th>
                    <th className="px-3 py-2 text-left">Size</th>
                    <th className="px-3 py-2 text-left">SHA256</th>
                    <th className="px-3 py-2 text-left">Verification</th>
                    <th className="px-3 py-2 text-left">Status</th>
                    <th className="px-3 py-2 text-left">Uploaded By</th>
                    <th className="px-3 py-2 text-left">Created</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border/60">
                  {rows.map((item) => (
                    <tr
                      key={item.id}
                      className="cursor-pointer hover:bg-muted/20"
                      onClick={() => setSelectedId(item.id)}
                    >
                      <td className="px-3 py-2 font-medium">{item.original_filename}</td>
                      <td className="px-3 py-2 font-mono text-xs">
                        {item.incident_id ?? "unlinked"}
                      </td>
                      <td className="px-3 py-2 tabular-nums">{formatBytes(item.size_bytes)}</td>
                      <td className="px-3 py-2 font-mono text-xs">{truncateHash(item.sha256)}</td>
                      <td className="px-3 py-2">
                        <StatusBadge status={item.verification_status} />
                      </td>
                      <td className="px-3 py-2">
                        <StatusBadge status={item.status} />
                      </td>
                      <td className="px-3 py-2 text-xs text-muted-foreground">
                        {item.uploaded_by_email}
                      </td>
                      <td className="px-3 py-2 text-xs text-muted-foreground">
                        {fmtRelative(item.created_at)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>

      <UploadEvidenceDialog
        open={uploadOpen}
        onOpenChange={setUploadOpen}
        onUploaded={invalidateEvidence}
      />

      <Sheet open={Boolean(selectedId)} onOpenChange={(open) => !open && setSelectedId(null)}>
        <SheetContent className="w-full overflow-y-auto sm:max-w-2xl">
          <SheetHeader>
            <SheetTitle>{selected?.original_filename ?? "Evidence"}</SheetTitle>
            <SheetDescription>{selected?.id ?? "Loading metadata"}</SheetDescription>
          </SheetHeader>
          {detail.isLoading ? (
            <LoadingState label="Loading evidence" />
          ) : detail.isError ? (
            <ErrorState error={detail.error} onRetry={() => void detail.refetch()} />
          ) : selected ? (
            <div className="mt-6 space-y-5">
              <div className="flex flex-wrap gap-2">
                <Button
                  size="sm"
                  onClick={() => verifyMutation.mutate(selected.id)}
                  disabled={verifyMutation.isPending}
                >
                  <ShieldCheck className="h-4 w-4" />
                  Verify
                </Button>
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => downloadMutation.mutate(selected.id)}
                  disabled={downloadMutation.isPending}
                >
                  <Download className="h-4 w-4" />
                  Download
                </Button>
                {canWrite ? (
                  <LinkControls
                    evidence={selected}
                    linking={linkMutation.isPending}
                    unlinking={unlinkMutation.isPending}
                    onLink={(incidentId) => linkMutation.mutate({ id: selected.id, incidentId })}
                    onUnlink={() => unlinkMutation.mutate(selected.id)}
                  />
                ) : null}
                {canAdmin && selected.status === "active" ? (
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => archiveMutation.mutate(selected.id)}
                    disabled={archiveMutation.isPending}
                  >
                    <Archive className="h-4 w-4" />
                    Archive
                  </Button>
                ) : null}
                {canAdmin && selected.status === "archived" ? (
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => restoreMutation.mutate(selected.id)}
                    disabled={restoreMutation.isPending}
                  >
                    <RotateCcw className="h-4 w-4" />
                    Restore
                  </Button>
                ) : null}
              </div>

              <dl className="grid gap-3 text-sm md:grid-cols-2">
                <Meta label="Stored filename" value={selected.filename} mono />
                <Meta label="Content type" value={selected.content_type} />
                <Meta label="Size" value={formatBytes(selected.size_bytes)} />
                <Meta label="Uploaded by" value={selected.uploaded_by_email} />
                <Meta label="Incident" value={selected.incident_id ?? "unlinked"} mono />
                <Meta label="Created" value={fmtDate(selected.created_at)} />
                <Meta label="Last verified" value={fmtDate(selected.last_verified_at)} />
                <Meta label="Description" value={selected.description ?? "—"} />
              </dl>
              <div className="space-y-1">
                <p className="text-xs uppercase tracking-wide text-muted-foreground">SHA256</p>
                <p className="break-all rounded-md border border-border/60 bg-background/50 p-2 font-mono text-xs">
                  {selected.sha256}
                </p>
              </div>
              <div className="flex flex-wrap gap-1">
                {selected.tags.length === 0 ? (
                  <span className="text-xs text-muted-foreground">No tags</span>
                ) : (
                  selected.tags.map((item) => (
                    <span
                      key={item}
                      className="rounded border border-border/60 bg-background/50 px-2 py-0.5 text-xs"
                    >
                      {item}
                    </span>
                  ))
                )}
              </div>
              <div className="space-y-2">
                <h2 className="text-sm font-semibold">Chain of Custody</h2>
                {custody.isLoading ? (
                  <LoadingState label="Loading custody" />
                ) : custodyRows.length === 0 ? (
                  <EmptyState icon={FileCheck2} title="No custody events" />
                ) : (
                  <ol className="space-y-2">
                    {custodyRows.map((event) => (
                      <li
                        key={event.id}
                        className="rounded-md border border-border/60 bg-background/40 p-3 text-sm"
                      >
                        <div className="flex items-start justify-between gap-3">
                          <div>
                            <p className="font-medium">{event.action.replace(/_/g, " ")}</p>
                            <p className="text-xs text-muted-foreground">{event.description}</p>
                            <p className="mt-1 text-xs text-muted-foreground">
                              {event.actor_email ?? "System"}
                            </p>
                          </div>
                          <p className="shrink-0 text-xs text-muted-foreground">
                            {fmtRelative(event.created_at)}
                          </p>
                        </div>
                      </li>
                    ))}
                  </ol>
                )}
              </div>
            </div>
          ) : null}
        </SheetContent>
      </Sheet>
    </div>
  );
}

function UploadEvidenceDialog({
  open,
  onOpenChange,
  onUploaded,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onUploaded: () => void;
}) {
  const [file, setFile] = useState<File | null>(null);
  const [incidentId, setIncidentId] = useState("");
  const [description, setDescription] = useState("");
  const [tags, setTags] = useState("");

  const uploadMutation = useMutation({
    mutationFn: () => {
      if (!file) throw new Error("Select a file");
      return sentinelApi.uploadEvidence({
        file,
        incident_id: incidentId.trim() || undefined,
        description: description.trim() || undefined,
        tags: tags.trim() || undefined,
      });
    },
    onSuccess: () => {
      toast.success("Evidence uploaded");
      setFile(null);
      setIncidentId("");
      setDescription("");
      setTags("");
      onOpenChange(false);
      onUploaded();
    },
  });

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    uploadMutation.mutate();
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Upload evidence</DialogTitle>
          <DialogDescription>
            Attach a file to the vault or directly to an incident.
          </DialogDescription>
        </DialogHeader>
        <form className="space-y-4" onSubmit={submit}>
          <div className="space-y-1.5">
            <Label htmlFor="evidence-file">File</Label>
            <Input
              id="evidence-file"
              type="file"
              required
              onChange={(event) => setFile(event.target.files?.[0] ?? null)}
            />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="incident-id">Incident ID</Label>
            <Input
              id="incident-id"
              value={incidentId}
              onChange={(event) => setIncidentId(event.target.value)}
              placeholder="inc_..."
            />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="evidence-description">Description</Label>
            <Textarea
              id="evidence-description"
              rows={3}
              value={description}
              onChange={(event) => setDescription(event.target.value)}
            />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="evidence-tags">Tags</Label>
            <Input
              id="evidence-tags"
              value={tags}
              onChange={(event) => setTags(event.target.value)}
              placeholder="host1, memory, warrant"
            />
          </div>
          <Button type="submit" disabled={uploadMutation.isPending || !file}>
            <Upload className="h-4 w-4" />
            Upload
          </Button>
        </form>
      </DialogContent>
    </Dialog>
  );
}

function LinkControls({
  evidence,
  linking,
  unlinking,
  onLink,
  onUnlink,
}: {
  evidence: Evidence;
  linking: boolean;
  unlinking: boolean;
  onLink: (incidentId: string) => void;
  onUnlink: () => void;
}) {
  const [incidentId, setIncidentId] = useState(evidence.incident_id ?? "");

  return (
    <div className="flex min-w-64 gap-2">
      <Input
        value={incidentId}
        onChange={(event) => setIncidentId(event.target.value)}
        placeholder="inc_..."
        className="h-8"
      />
      <Button
        size="sm"
        variant="outline"
        onClick={() => onLink(incidentId)}
        disabled={linking || !incidentId.trim()}
      >
        <Link2 className="h-4 w-4" />
      </Button>
      {evidence.incident_id ? (
        <Button size="sm" variant="outline" onClick={onUnlink} disabled={unlinking}>
          <Unlink className="h-4 w-4" />
        </Button>
      ) : null}
    </div>
  );
}

function Meta({ label, value, mono = false }: { label: string; value: string; mono?: boolean }) {
  return (
    <div className="space-y-1">
      <dt className="text-xs uppercase tracking-wide text-muted-foreground">{label}</dt>
      <dd className={mono ? "break-all font-mono text-xs" : "text-sm"}>{value}</dd>
    </div>
  );
}

function truncateHash(value: string) {
  return value.length > 18 ? `${value.slice(0, 12)}...${value.slice(-6)}` : value;
}

function formatBytes(value: number) {
  if (value < 1024) return `${value} B`;
  if (value < 1024 * 1024) return `${(value / 1024).toFixed(1)} KB`;
  return `${(value / 1024 / 1024).toFixed(1)} MB`;
}
