import { createFileRoute, Link } from "@tanstack/react-router";
import { useMutation } from "@tanstack/react-query";
import {
  AlertOctagon,
  ClipboardList,
  FileDown,
  FileText,
  FolderLock,
  GitBranch,
} from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { saveDownload, sentinelApi } from "@/lib/sentinelxdr-api";

export const Route = createFileRoute("/_app/reports")({ component: ReportsPage });

const reportLinks = [
  {
    title: "Incident Reports",
    description: "PDF exports with MITRE context, alerts, evidence, custody, and actions.",
    icon: AlertOctagon,
    to: "/incidents",
  },
  {
    title: "Attack Chain Reports",
    description: "Narrative PDFs for timelines, graph references, risk, and recommendations.",
    icon: GitBranch,
    to: "/attack-chains",
  },
  {
    title: "Evidence Reports",
    description: "Evidence PDFs with hashes, verification state, and custody history.",
    icon: FolderLock,
    to: "/evidence",
  },
  {
    title: "Audit Export",
    description: "CSV export for organization-scoped audit review.",
    icon: ClipboardList,
    to: "/audit",
  },
] as const;

function ReportsPage() {
  const executiveSummary = useMutation({
    mutationFn: () => sentinelApi.downloadExecutiveSummary(),
    onSuccess: (download) => {
      saveDownload(download);
      toast.success("Executive summary exported");
    },
  });

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold tracking-tight">Reports</h1>
          <p className="text-sm text-muted-foreground">
            Organization-scoped exports for investigations, evidence, audit, and leadership review.
          </p>
        </div>
        <Button onClick={() => executiveSummary.mutate()} disabled={executiveSummary.isPending}>
          <FileDown className="h-4 w-4" />
          Executive Summary PDF
        </Button>
      </div>

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        {reportLinks.map((item) => {
          const Icon = item.icon;
          return (
            <Card key={item.title} className="border-border/60 bg-card/60">
              <CardHeader className="pb-2">
                <CardTitle className="flex items-center gap-2 text-sm">
                  <Icon className="h-4 w-4 text-primary" />
                  {item.title}
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <p className="text-sm text-muted-foreground">{item.description}</p>
                <Link to={item.to} className="inline-flex items-center gap-1 text-sm text-primary">
                  <FileText className="h-4 w-4" />
                  Open
                </Link>
              </CardContent>
            </Card>
          );
        })}
      </div>
    </div>
  );
}
