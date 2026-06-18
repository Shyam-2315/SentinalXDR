import type { ReactNode } from "react";
import { Sidebar } from "./Sidebar";
import { Topbar } from "./Topbar";

export function AppLayout({ children }: { children: ReactNode }) {
  return (
    <div className="flex min-h-screen bg-background bg-[radial-gradient(circle_at_25%_0%,rgba(56,189,248,0.06),transparent_32%),radial-gradient(circle_at_85%_20%,rgba(239,68,68,0.08),transparent_32%)] text-foreground">
      <Sidebar />
      <div className="flex min-w-0 flex-1 flex-col">
        <Topbar />
        <main className="flex-1 overflow-x-hidden p-4 md:p-6">{children}</main>
      </div>
    </div>
  );
}
