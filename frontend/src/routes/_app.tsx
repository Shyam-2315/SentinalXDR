import { createFileRoute, Outlet, redirect } from "@tanstack/react-router";
import { authStore } from "@/lib/auth";
import { AppLayout } from "@/components/layout/AppLayout";

export const Route = createFileRoute("/_app")({
  beforeLoad: () => {
    if (typeof window !== "undefined" && !authStore.getAccess()) {
      throw redirect({ to: "/login" });
    }
  },
  component: () => (
    <AppLayout>
      <Outlet />
    </AppLayout>
  ),
});
