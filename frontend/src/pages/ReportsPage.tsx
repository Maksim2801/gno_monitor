import { FormEvent, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { reportsApi, wellsApi } from "../api/endpoints";
import { useAuth } from "../features/auth/AuthContext";
import { formatDate } from "../utils/format";

export function ReportsPage() {
  const { canWrite } = useAuth();
  const qc = useQueryClient();
  const [selectedId, setSelectedId] = useState<number | null>(null);

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
    mutationFn: (payload: Record<string, unknown>) => reportsApi.create(payload),
    onSuccess: (report) => {
      void qc.invalidateQueries({ queryKey: ["reports"] });
      setSelectedId(report.id);
    },
  });

  function onSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const fd = new FormData(e.currentTarget);
    const wellRaw = String(fd.get("well_id") || "");
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
              Сформировать
            </button>
            {create.isError && (
              <div className="state-box error">{(create.error as Error).message}</div>
            )}
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
