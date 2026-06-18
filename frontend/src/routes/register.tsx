import { createFileRoute, useNavigate, Link } from "@tanstack/react-router";
import { useState, type ChangeEvent, type FormEvent } from "react";
import { Building2, Shield, Users } from "lucide-react";
import { useAuth } from "@/context/AuthContext";
import { getErrorMessage } from "@/lib/page-state";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent } from "@/components/ui/card";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";

export const Route = createFileRoute("/register")({
  component: RegisterPage,
});

type RegistrationMode = "create" | "join";

function RegisterPage() {
  const { register } = useAuth();
  const navigate = useNavigate();
  const [mode, setMode] = useState<RegistrationMode>("create");
  const [form, setForm] = useState({
    email: "",
    display_name: "",
    password: "",
    organization_name: "",
    organization_id: "",
  });
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      const payload = {
        email: form.email.trim(),
        password: form.password,
        display_name: form.display_name.trim(),
        ...(mode === "create"
          ? { organization_name: form.organization_name.trim() }
          : { organization_id: form.organization_id.trim() }),
      };
      await register(payload);
      void navigate({ to: "/dashboard" });
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setSubmitting(false);
    }
  }

  function set<K extends keyof typeof form>(k: K) {
    return (e: ChangeEvent<HTMLInputElement>) => setForm((f) => ({ ...f, [k]: e.target.value }));
  }

  return (
    <div className="relative grid min-h-screen place-items-center overflow-hidden bg-background p-4">
      <div className="pointer-events-none absolute inset-x-0 top-0 h-24 border-b border-border/50 bg-muted/20" />
      <div className="relative w-full max-w-lg space-y-6">
        <div className="flex items-center gap-3">
          <div className="grid h-10 w-10 place-items-center rounded-md bg-[color:var(--sev-critical)]/15 text-[color:var(--sev-critical)]">
            <Shield className="h-5 w-5" />
          </div>
          <div>
            <h1 className="text-lg font-semibold tracking-tight">SentinelXDR</h1>
            <p className="text-xs text-muted-foreground">Create operator account</p>
          </div>
        </div>
        <Card className="border-border/60 bg-card/70 backdrop-blur">
          <CardContent className="space-y-4 p-6">
            <form onSubmit={onSubmit} className="space-y-3">
              <div className="space-y-2">
                <Label>Organization setup</Label>
                <RadioGroup
                  value={mode}
                  onValueChange={(value) => setMode(value as RegistrationMode)}
                  className="grid gap-2 sm:grid-cols-2"
                >
                  <Label
                    htmlFor="mode-create"
                    className="flex cursor-pointer items-start gap-3 rounded-md border border-border/60 bg-background/40 p-3"
                  >
                    <RadioGroupItem id="mode-create" value="create" className="mt-1" />
                    <span className="space-y-1">
                      <span className="flex items-center gap-2 text-sm font-medium">
                        <Building2 className="h-4 w-4" />
                        Create new organization
                      </span>
                      <span className="block text-xs font-normal text-muted-foreground">
                        Create your workspace and become organization admin.
                      </span>
                    </span>
                  </Label>
                  <Label
                    htmlFor="mode-join"
                    className="flex cursor-pointer items-start gap-3 rounded-md border border-border/60 bg-background/40 p-3"
                  >
                    <RadioGroupItem id="mode-join" value="join" className="mt-1" />
                    <span className="space-y-1">
                      <span className="flex items-center gap-2 text-sm font-medium">
                        <Users className="h-4 w-4" />
                        Join existing organization
                      </span>
                      <span className="block text-xs font-normal text-muted-foreground">
                        Enter organization ID shared by your admin.
                      </span>
                    </span>
                  </Label>
                </RadioGroup>
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="email">Email</Label>
                <Input
                  id="email"
                  type="email"
                  required
                  value={form.email}
                  onChange={set("email")}
                />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="display_name">Full name</Label>
                <Input
                  id="display_name"
                  autoComplete="name"
                  required
                  value={form.display_name}
                  onChange={set("display_name")}
                />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="password">Password</Label>
                <Input
                  id="password"
                  type="password"
                  required
                  value={form.password}
                  onChange={set("password")}
                />
              </div>
              {mode === "create" ? (
                <div className="space-y-1.5">
                  <Label htmlFor="organization_name">Organization name</Label>
                  <Input
                    id="organization_name"
                    required
                    value={form.organization_name}
                    onChange={set("organization_name")}
                  />
                </div>
              ) : (
                <div className="space-y-1.5">
                  <Label htmlFor="organization_id">Organization ID</Label>
                  <Input
                    id="organization_id"
                    required
                    autoComplete="off"
                    value={form.organization_id}
                    onChange={set("organization_id")}
                  />
                </div>
              )}
              <Button type="submit" disabled={submitting} className="w-full">
                {submitting ? "Creating…" : "Create account"}
              </Button>
            </form>
            {error ? (
              <p className="rounded-md border border-[color:var(--sev-critical)]/40 bg-[color:var(--sev-critical)]/10 p-2 text-xs text-[color:var(--sev-critical)]">
                {error}
              </p>
            ) : null}
            <p className="text-center text-xs text-muted-foreground">
              Have an account?{" "}
              <Link to="/login" className="text-primary hover:underline">
                Sign in
              </Link>
            </p>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
