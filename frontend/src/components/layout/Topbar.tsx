import { useState } from "react";
import { LogOut, User, Search } from "lucide-react";
import { useAuth } from "@/context/AuthContext";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Input } from "@/components/ui/input";

export function Topbar() {
  const { user, organization, logout } = useAuth();
  const [q, setQ] = useState("");
  const displayName = user?.display_name || user?.full_name || user?.username || user?.email;
  const initial = (displayName || "U").charAt(0).toUpperCase();
  return (
    <header className="flex h-14 items-center justify-between gap-4 border-b border-border/60 bg-background/80 px-4 backdrop-blur">
      <div className="relative w-full max-w-md">
        <Search className="pointer-events-none absolute left-2.5 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
        <Input
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="Search alerts, incidents, hosts…"
          className="h-9 border-border/60 bg-card/60 pl-8 text-sm"
        />
      </div>
      <div className="flex items-center gap-3">
        <div className="hidden text-right md:block">
          <p className="text-xs font-medium text-foreground">{user?.email ?? "Operator"}</p>
          <p className="text-[11px] text-muted-foreground">
            {String(user?.role ?? "role")} · {organization?.name ?? "No organization"}
          </p>
        </div>
        <div className="hidden items-center gap-2 rounded-md border border-emerald-500/30 bg-emerald-500/10 px-2 py-1 text-xs text-emerald-300 md:flex">
          <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-emerald-400" />
          Live
        </div>
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" className="h-9 gap-2 px-2">
              <div className="grid h-7 w-7 place-items-center rounded-full bg-primary/15 text-xs font-semibold text-primary">
                {initial}
              </div>
              <span className="hidden text-sm md:inline">Account</span>
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="w-48">
            <DropdownMenuLabel>
              <span className="block">{displayName ?? "Account"}</span>
              <span className="block text-xs font-normal text-muted-foreground">
                {organization?.name ?? "No organization"}
              </span>
            </DropdownMenuLabel>
            <DropdownMenuSeparator />
            <DropdownMenuItem asChild>
              <a href="/settings">
                <User className="mr-2 h-4 w-4" /> Profile
              </a>
            </DropdownMenuItem>
            <DropdownMenuItem onClick={() => void logout()}>
              <LogOut className="mr-2 h-4 w-4" /> Sign out
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </header>
  );
}
