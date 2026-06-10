import { createFileRoute, redirect } from "@tanstack/react-router";
import { authStore } from "@/lib/auth";

export const Route = createFileRoute("/")({
  beforeLoad: () => {
    throw redirect({ to: authStore.getAccess() ? "/dashboard" : "/login" });
  },
  component: () => null,
});
