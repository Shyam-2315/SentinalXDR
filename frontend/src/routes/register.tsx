import { createFileRoute, useNavigate, Link } from "@tanstack/react-router";
import { useState, type FormEvent } from "react";
import { Shield } from "lucide-react";
import { useAuth } from "@/context/AuthContext";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent } from "@/components/ui/card";

export const Route = createFileRoute("/register")({
  component: RegisterPage,
});

function RegisterPage() {
  const { register } = useAuth();
  const navigate = useNavigate();
  const [form, setForm] = useState({ email: "", username: "", full_name: "", password: "" });
  const [submitting, setSubmitting] = useState(false);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    try {
      await register(form);
      void navigate({ to: "/dashboard" });
    } catch {
      // handled by toast
    } finally {
      setSubmitting(false);
    }
  }

  function set<K extends keyof typeof form>(k: K) {
    return (e: React.ChangeEvent<HTMLInputElement>) =>
      setForm((f) => ({ ...f, [k]: e.target.value }));
  }

  return (
    <div className="relative grid min-h-screen place-items-center overflow-hidden bg-background p-4">
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_30%_20%,rgba(56,189,248,0.08),transparent_55%),radial-gradient(circle_at_80%_70%,rgba(239,68,68,0.08),transparent_55%)]" />
      <div className="relative w-full max-w-md space-y-6">
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
                <Label htmlFor="username">Username</Label>
                <Input id="username" required value={form.username} onChange={set("username")} />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="full_name">Full name</Label>
                <Input id="full_name" value={form.full_name} onChange={set("full_name")} />
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
              <Button type="submit" disabled={submitting} className="w-full">
                {submitting ? "Creating…" : "Create account"}
              </Button>
            </form>
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
