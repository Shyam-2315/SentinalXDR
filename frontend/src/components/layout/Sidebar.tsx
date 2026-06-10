import { Link, useRouterState } from "@tanstack/react-router";
import {
  LayoutDashboard,
  Server,
  Activity,
  ShieldAlert,
  Bell,
  AlertOctagon,
  GitBranch,
  Crosshair,
  Settings,
  Shield,
} from "lucide-react";
import { cn } from "@/lib/utils";

const nav = [
  { to: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { to: "/agents", label: "Agents", icon: Server },
  { to: "/events", label: "Events", icon: Activity },
  { to: "/detections", label: "Detection Rules", icon: ShieldAlert },
  { to: "/alerts", label: "Alerts", icon: Bell },
  { to: "/incidents", label: "Incidents", icon: AlertOctagon },
  { to: "/attack-chains", label: "Attack Chains", icon: GitBranch },
  { to: "/mitre", label: "MITRE Summary", icon: Crosshair },
  { to: "/settings", label: "Settings", icon: Settings },
] as const;

export function Sidebar() {
  const pathname = useRouterState({ select: (s) => s.location.pathname });
  return (
    <aside className="hidden h-screen w-60 shrink-0 flex-col border-r border-border/60 bg-sidebar md:flex">
      <div className="flex h-14 items-center gap-2 border-b border-border/60 px-4">
        <div className="grid h-8 w-8 place-items-center rounded-md bg-[color:var(--sev-critical)]/15 text-[color:var(--sev-critical)]">
          <Shield className="h-4 w-4" />
        </div>
        <div className="leading-tight">
          <p className="text-sm font-semibold tracking-tight">SentinelXDR</p>
          <p className="text-[10px] uppercase tracking-wider text-muted-foreground">SOC Console</p>
        </div>
      </div>
      <nav className="flex-1 space-y-0.5 overflow-y-auto p-2">
        {nav.map((item) => {
          const active = pathname === item.to || pathname.startsWith(`${item.to}/`);
          const Icon = item.icon;
          return (
            <Link
              key={item.to}
              to={item.to}
              className={cn(
                "flex items-center gap-2 rounded-md px-3 py-2 text-sm transition-colors",
                active
                  ? "bg-sidebar-accent text-sidebar-accent-foreground"
                  : "text-sidebar-foreground/80 hover:bg-sidebar-accent/60 hover:text-sidebar-foreground",
              )}
            >
              <Icon className="h-4 w-4" />
              {item.label}
            </Link>
          );
        })}
      </nav>
      <div className="border-t border-border/60 p-3 text-[10px] text-muted-foreground">
        v1.0 · AI-Powered XDR
      </div>
    </aside>
  );
}
