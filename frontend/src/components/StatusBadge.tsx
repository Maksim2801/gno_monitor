import { riskLabel, statusLabel } from "../utils/format";

export function StatusBadge({ status }: { status: string }) {
  return <span className={`badge ${status}`}>{statusLabel(status)}</span>;
}

export function RiskBadge({ risk }: { risk?: string | null }) {
  const cls = risk || "info";
  return <span className={`badge ${cls}`}>{riskLabel(risk)}</span>;
}
