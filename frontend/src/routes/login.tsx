import { createFileRoute, useNavigate, Link } from "@tanstack/react-router";
import { useState, type FormEvent } from "react";
import { Shield } from "lucide-react";
import { useAuth } from "@/context/AuthContext";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent } from "@/components/ui/card";

export const Route = createFileRoute("/login")({
  component: LoginPage,
});

function LoginPage() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [submitting, setSubmitting] = useState(false);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    try {
      await login(email, password);
      void navigate({ to: "/dashboard" });
    } catch {
      // toast handled by api
    } finally {
      setSubmitting(false);
    }
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
            <p className="text-xs text-muted-foreground">AI-powered XDR / SOC platform</p>
          </div>
        </div>
        <Card className="border-border/60 bg-card/70 backdrop-blur">
          <CardContent className="space-y-4 p-6">
            <div className="space-y-1">
              <h2 className="text-xl font-semibold">Sign in</h2>
              <p className="text-sm text-muted-foreground">Operator access to the SOC console.</p>
            </div>
            <form onSubmit={onSubmit} className="space-y-3">
              <div className="space-y-1.5">
                <Label htmlFor="email">Email</Label>
                <Input
                  id="email"
                  type="email"
                  autoComplete="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="password">Password</Label>
                <Input
                  id="password"
                  type="password"
                  autoComplete="current-password"
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                />
              </div>
              <Button type="submit" disabled={submitting} className="w-full">
                {submitting ? "Signing in…" : "Sign in"}
              </Button>
            </form>
            <p className="text-center text-xs text-muted-foreground">
              No account?{" "}
              <Link to="/register" className="text-primary hover:underline">
                Register
              </Link>
            </p>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
