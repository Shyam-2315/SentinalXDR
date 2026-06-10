import { createFileRoute } from "@tanstack/react-router";
import { useAuth } from "@/context/AuthContext";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { JsonViewer } from "@/components/common/JsonViewer";

export const Route = createFileRoute("/_app/settings")({ component: SettingsPage });

function SettingsPage() {
  const { user, logout } = useAuth();
  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-xl font-semibold tracking-tight">Profile &amp; Settings</h1>
        <p className="text-sm text-muted-foreground">Operator account and session.</p>
      </div>
      <div className="grid gap-4 lg:grid-cols-2">
        <Card className="border-border/60 bg-card/60">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm">Account</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3 text-sm">
            <Field label="Email" value={user?.email} />
            <Field label="Username" value={user?.username} />
            <Field label="Full name" value={user?.full_name} />
            <Field label="Role" value={user?.role} />
            <Button variant="destructive" onClick={() => void logout()}>
              Sign out
            </Button>
          </CardContent>
        </Card>
        <Card className="border-border/60 bg-card/60">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm">Session payload</CardTitle>
          </CardHeader>
          <CardContent>
            <JsonViewer data={user ?? {}} />
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

function Field({ label, value }: { label: string; value?: string | null }) {
  return (
    <div className="flex items-center justify-between border-b border-border/60 pb-2 last:border-none">
      <span className="text-xs uppercase tracking-wide text-muted-foreground">{label}</span>
      <span className="font-mono text-xs">{value ?? "—"}</span>
    </div>
  );
}
