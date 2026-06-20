import { ApiError, BASE_URL, api } from "./api";
import { authStore } from "./auth";

export type EvidenceQuery = {
  incident_id?: string;
  status?: string;
  verification_status?: string;
  tag?: string;
  limit?: number;
  skip?: number;
};

export type EvidenceUploadInput = {
  file: File;
  incident_id?: string;
  description?: string;
  tags?: string;
};

async function downloadFile(path: string, fallbackFilename = "sentinelxdr-download") {
  const token = authStore.getAccess();
  const response = await fetch(`${BASE_URL}${path}`, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  });
  if (!response.ok) {
    throw new ApiError(response.status, `Download failed (${response.status})`);
  }
  const blob = await response.blob();
  const disposition = response.headers.get("content-disposition") ?? "";
  const match = disposition.match(/filename="?([^";]+)"?/i);
  return { blob, filename: match?.[1] ?? fallbackFilename };
}

export function saveDownload({ blob, filename }: { blob: Blob; filename: string }) {
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  anchor.click();
  URL.revokeObjectURL(url);
}

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

  auditLogs: (query = "") => api.get(`/api/audit${query}`),
  auditLog: (auditId: string) => api.get(`/api/audit/${auditId}`),

  listEvidence: (query: EvidenceQuery = {}) => api.get("/api/evidence", { query }),
  getEvidence: (evidenceId: string) => api.get(`/api/evidence/${evidenceId}`),
  uploadEvidence: (payload: EvidenceUploadInput) => {
    const form = new FormData();
    form.set("file", payload.file);
    if (payload.incident_id) form.set("incident_id", payload.incident_id);
    if (payload.description) form.set("description", payload.description);
    if (payload.tags) form.set("tags", payload.tags);
    return api.post("/api/evidence", form);
  },
  downloadEvidence: (evidenceId: string) =>
    downloadFile(`/api/evidence/${evidenceId}/download`, "evidence-download"),
  verifyEvidence: (evidenceId: string) => api.post(`/api/evidence/${evidenceId}/verify`),
  linkEvidence: (evidenceId: string, incidentId: string) =>
    api.patch(`/api/evidence/${evidenceId}/link`, { incident_id: incidentId }),
  unlinkEvidence: (evidenceId: string) => api.patch(`/api/evidence/${evidenceId}/unlink`),
  archiveEvidence: (evidenceId: string) => api.post(`/api/evidence/${evidenceId}/archive`),
  restoreEvidence: (evidenceId: string) => api.post(`/api/evidence/${evidenceId}/restore`),
  getEvidenceCustody: (evidenceId: string) => api.get(`/api/evidence/${evidenceId}/custody`),

  downloadIncidentReport: (incidentId: string) =>
    downloadFile(`/api/reports/incidents/${incidentId}.pdf`, `incident-${incidentId}.pdf`),
  downloadAttackChainReport: (chainId: string) =>
    downloadFile(`/api/reports/attack-chains/${chainId}.pdf`, `attack-chain-${chainId}.pdf`),
  downloadEvidenceReport: (evidenceId: string) =>
    downloadFile(`/api/reports/evidence/${evidenceId}.pdf`, `evidence-${evidenceId}.pdf`),
  downloadAuditCsv: () => downloadFile("/api/reports/audit.csv", "sentinelxdr-audit.csv"),
  downloadExecutiveSummary: () =>
    downloadFile("/api/reports/executive-summary.pdf", "sentinelxdr-executive-summary.pdf"),
};
