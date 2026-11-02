import { FormEvent, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { reportsApi, wellsApi } from "../api/endpoints";
import { useAuth } from "../features/auth/AuthContext";
import type { Report } from "../types";
import { formatDate } from "../utils/format";

function reportExtension(report: Report, preferredFormat?: string) {
  const format = (preferredFormat || report.file_format || "json").toLowerCase();
  return format === "pdf" || format === "csv" ? format : "json";
}

function reportFilename(report: Report, preferredFormat?: string) {
  const base = (report.title || "report").replace(/[\\/:*?"<>|]+/g, "_");
  return `${base}_${report.id}.${reportExtension(report, preferredFormat)}`;
}

function saveBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  link.rel = "noopener";
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.setTimeout(() => URL.revokeObjectURL(url), 1000);
}

async function downloadReport(report: Report, preferredFormat?: string) {
  const ext = reportExtension(report, preferredFormat);
  if (ext === "json") {
    const full =
      report.content_json != null || report.content_text != null
        ? report
        : await reportsApi.get(report.id);
    const text = JSON.stringify(full.content_json ?? {}, null, 2);
    saveBlob(
      new Blob([text], { type: "application/json;charset=utf-8" }),
      reportFilename(report, preferredFormat)
    );
    return;
  }
  const blob = await reportsApi.download(report.id);
  saveBlob(blob, reportFilename(report, preferredFormat));
}

export function ReportsPage() {
  const { canWrite } = useAuth();
  const qc = useQueryClient();
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [downloadError, setDownloadError] = useState<string | null>(null);

  const list = useQuery({ queryKey: ["reports"], queryFn: reportsApi.list });
  const wells = useQuery({
    queryKey: ["wells-all"],
    queryFn: () => wellsApi.list({ page: 1, page_size: 100 }),
  });
  const detail = useQuery({
    queryKey: ["report", selectedId],
    queryFn: () => reportsApi.get(selectedId!),
    enabled: !!selectedId,
  });

  const create = useMutation({
    mutationFn: async (payload: Record<string, unknown>) => {
      const report = await reportsApi.create(payload);
      const exportFormat = String(payload.export_format || report.file_format || "json");
      await downloadReport(report, exportFormat);
      return report;
    },
    onSuccess: (report) => {
      void qc.invalidateQueries({ queryKey: ["reports"] });
      setSelectedId(report.id);
      setDownloadError(null);
    },
    onError: (err) => {
      setDownloadError((err as Error).message || "Не удалось сформировать или скачать отчёт");
    },
  });

  function onSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const fd = new FormData(e.currentTarget);
    const wellRaw = String(fd.get("well_id") || "");
    setDownloadError(null);
    create.mutate({
      report_type: String(fd.get("report_type")),
      period_start: new Date(String(fd.get("period_start"))).toISOString(),
      period_end: new Date(String(fd.get("period_end"))).toISOString(),
      well_id: wellRaw ? Number(wellRaw) : null,
      export_format: String(fd.get("export_format")),
    });
  }

  const now = new Date();
  const weekAgo = new Date(Date.now() - 7 * 24 * 3600 * 1000);

  return (
    <div>
      <h1 className="page-title">Отчёты</h1>
      <p className="page-subtitle">Формирование и просмотр сохранённых аналитических документов</p>

      {canWrite && (
        <div className="panel">
          <h2>Новый отчёт</h2>
          <form className="form-grid" onSubmit={onSubmit}>
            <label>
              Тип
              <select name="report_type" defaultValue="fund_summary">
                <option value="fund_summary">Сводка по фонду</option>
                <option value="well">По скважине</option>
                <option value="telemetry">Телеметрия</option>
                <option value="failures">Отказы и ремонты</option>
                <option value="analytics">Аномалии и прогнозы</option>
                <option value="alerts">Уведомления</option>
              </select>
            </label>
            <label>
              Скважина (если нужно)
              <select name="well_id" defaultValue="">
                <option value="">—</option>
                {(wells.data?.items || []).map((w) => (
                  <option key={w.id} value={w.id}>
                    {w.name}
                  </option>
                ))}
              </select>
            </label>
            <label>
              Начало периода
              <input
                type="datetime-local"
                name="period_start"
                required
                defaultValue={weekAgo.toISOString().slice(0, 16)}
              />
            </label>
            <label>
              Конец периода
              <input
                type="datetime-local"
                name="period_end"
                required
                defaultValue={now.toISOString().slice(0, 16)}
              />
            </label>
            <label>
              Формат
              <select name="export_format" defaultValue="json">
                <option value="json">JSON</option>
                <option value="csv">CSV</option>
                <option value="pdf">PDF</option>
              </select>
            </label>
            <button className="btn primary" disabled={create.isPending}>
              {create.isPending ? "Формирование..." : "Сформировать"}
            </button>
            {create.isError && (
              <div className="state-box error">{(create.error as Error).message}</div>
            )}
            {downloadError && <div className="state-box error">{downloadError}</div>}
          </form>
        </div>
      )}

      <div className="stack-2">
        <div className="panel">
          <h2>Ранее созданные</h2>
          {list.isLoading && <div className="state-box">Загрузка...</div>}
          {list.data && (
            <div className="table-wrap">
              <table className="data">
                <thead>
                  <tr>
                    <th>Дата</th>
                    <th>Тип</th>
                    <th>Название</th>
                  </tr>
                </thead>
                <tbody>
                  {list.data.map((r) => (
                    <tr
                      key={r.id}
                      onClick={() => setSelectedId(r.id)}
                      style={{ cursor: "pointer" }}
                    >
                      <td>{formatDate(r.created_at)}</td>
                      <td>{r.report_type}</td>
                      <td>{r.title}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
        <div className="panel">
          <h2>Содержимое</h2>
          {!selectedId && <div className="state-box">Выберите отчёт</div>}
          {detail.isLoading && <div className="state-box">Загрузка...</div>}
          {detail.data && (
            <pre
              className="mono"
              style={{
                whiteSpace: "pre-wrap",
                fontSize: "0.8rem",
                maxHeight: 480,
                overflow: "auto",
              }}
            >
              {detail.data.content_text}
            </pre>
          )}
        </div>
      </div>
    </div>
  );
}
