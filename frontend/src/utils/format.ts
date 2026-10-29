export function formatDate(value?: string | null) {
  if (!value) return "—";
  return new Date(value).toLocaleString("ru-RU");
}

export function formatNumber(value?: number | null, digits = 2) {
  if (value === null || value === undefined || Number.isNaN(value)) return "—";
  return value.toLocaleString("ru-RU", {
    minimumFractionDigits: 0,
    maximumFractionDigits: digits,
  });
}

export function riskLabel(risk?: string | null) {
  switch (risk) {
    case "low":
      return "Низкий";
    case "medium":
      return "Средний";
    case "high":
      return "Высокий";
    default:
      return "н/д";
  }
}

export function statusLabel(status?: string | null) {
  const map: Record<string, string> = {
    normal: "Норма",
    warning: "Предупреждение",
    critical: "Критично",
    stopped: "Останов",
    maintenance: "Ремонт",
  };
  return map[status || ""] || status || "—";
}
