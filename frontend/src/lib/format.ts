export function fmtDate(value?: string | number | null) {
  if (!value) return "—";
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return String(value);
  return d.toLocaleString();
}

export function fmtRelative(value?: string | number | null) {
  if (!value) return "—";
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return String(value);
  const diff = (Date.now() - d.getTime()) / 1000;
  if (diff < 60) return `${Math.floor(diff)}s ago`;
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
  return `${Math.floor(diff / 86400)}d ago`;
}

export function toArray<T>(v: unknown): T[] {
  if (Array.isArray(v)) return v as T[];
  if (v && typeof v === "object") {
    const obj = v as Record<string, unknown>;
    for (const k of [
      "items",
      "results",
      "data",
      "agents",
      "events",
      "rules",
      "alerts",
      "incidents",
      "attack_chains",
      "detections",
      "days",
      "tactics",
      "by_status",
      "nodes",
      "edges",
      "timeline",
    ]) {
      if (Array.isArray(obj[k])) return obj[k] as T[];
    }
  }
  return [];
}
