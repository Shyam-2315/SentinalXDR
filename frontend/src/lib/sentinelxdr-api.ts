import { api } from "./api";

export const sentinelApi = {
  me: () => api.get("/api/auth/me"),
  login: (email: string, password: string) =>
    api.post("/api/auth/login", { email, password }, { auth: false }),
  register: (payload: Record<string, unknown>) =>
    api.post("/api/auth/register", payload, { auth: false }),

  dashboardSummary: () => api.get("/api/dashboard/summary"),
  securityPosture: () => api.get("/api/dashboard/security-posture"),
  recentAlerts: () => api.get("/api/dashboard/recent-alerts"),
  recentIncidents: () => api.get("/api/dashboard/recent-incidents"),
  recentAttackChains: () => api.get("/api/dashboard/recent-attack-chains"),
  mitreSummary: () => api.get("/api/dashboard/mitre-summary"),
  severityTrends: () => api.get("/api/dashboard/severity-trends"),
  agentHealth: () => api.get("/api/dashboard/agent-health"),

  agents: () => api.get("/api/agents"),
  registerAgent: (payload: Record<string, unknown>) => api.post("/api/agents/register", payload),
  disableAgent: (agentId: string) => api.post(`/api/agents/${agentId}/disable`),

  events: () => api.get("/api/events"),
  event: (eventId: string) => api.get(`/api/events/${eventId}`),

  detectionRules: () => api.get("/api/detections/rules"),
  createDetectionRule: (payload: Record<string, unknown>) =>
    api.post("/api/detections/rules", payload),
  updateDetectionRule: (ruleId: string, payload: Record<string, unknown>) =>
    api.patch(`/api/detections/rules/${ruleId}`, payload),
  enableDetectionRule: (ruleId: string) => api.post(`/api/detections/rules/${ruleId}/enable`),
  disableDetectionRule: (ruleId: string) => api.post(`/api/detections/rules/${ruleId}/disable`),
  detectionResults: () => api.get("/api/detections/results"),

  alerts: () => api.get("/api/alerts"),
  alert: (alertId: string) => api.get(`/api/alerts/${alertId}`),
  updateAlertStatus: (alertId: string, status: string) =>
    api.patch(`/api/alerts/${alertId}/status`, { status }),

  incidents: () => api.get("/api/incidents"),
  incident: (incidentId: string) => api.get(`/api/incidents/${incidentId}`),
  updateIncidentStatus: (incidentId: string, status: string) =>
    api.patch(`/api/incidents/${incidentId}/status`, { status }),
  assignIncident: (incidentId: string, assignedToUserId: string | null) =>
    api.patch(`/api/incidents/${incidentId}/assign`, {
      assigned_to_user_id: assignedToUserId,
    }),
  updateIncidentSummary: (incidentId: string, summary: string | null) =>
    api.patch(`/api/incidents/${incidentId}/summary`, { summary }),

  attackChains: () => api.get("/api/attack-chains"),
  attackChain: (chainId: string) => api.get(`/api/attack-chains/${chainId}`),
  incidentAttackChain: (incidentId: string) => api.get(`/api/incidents/${incidentId}/attack-chain`),
  updateAttackChainStatus: (chainId: string, status: string) =>
    api.patch(`/api/attack-chains/${chainId}/status`, { status }),
};
