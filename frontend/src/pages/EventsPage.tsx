import { FormEvent, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { eventsApi, wellsApi } from "../api/endpoints";
import { useAuth } from "../features/auth/AuthContext";
import { formatDate } from "../utils/format";

export function EventsPage() {
  const { canWrite } = useAuth();
  const qc = useQueryClient();
  const [wellId, setWellId] = useState<number | "">("");

  const wells = useQuery({
    queryKey: ["wells-all"],
    queryFn: () => wellsApi.list({ page: 1, page_size: 100 }),
  });
  const events = useQuery({
    queryKey: ["events", wellId],
    queryFn: () =>
      eventsApi.list({
        well_id: wellId || undefined,
        limit: 100,
      }),
  });

  const create = useMutation({
    mutationFn: (payload: Record<string, unknown>) => eventsApi.createFailure(payload),
    onSuccess: () => void qc.invalidateQueries({ queryKey: ["events"] }),
  });

  function onCreate(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (!canWrite) return;
    if (
      !window.confirm("Зарегистрировать отказ? Операция будет сохранена в базе данных.")
    ) {
      return;
    }
    const fd = new FormData(e.currentTarget);
    create.mutate({
      well_id: Number(fd.get("well_id")),
      failure_type: String(fd.get("failure_type")),
      severity: String(fd.get("severity")),
      occurred_at: new Date(String(fd.get("occurred_at"))).toISOString(),
      description: String(fd.get("description") || ""),
    });
    e.currentTarget.reset();
  }

  return (
    <div>
      <h1 className="page-title">События эксплуатации</h1>
      <p className="page-subtitle">Отказы, ремонты и связанные события</p>

      <div className="filters">
        <select
          value={wellId}
          onChange={(e) => setWellId(e.target.value ? Number(e.target.value) : "")}
        >
          <option value="">Все скважины</option>
          {(wells.data?.items || []).map((w) => (
            <option key={w.id} value={w.id}>
              {w.name}
            </option>
          ))}
        </select>
      </div>

      {canWrite && (
        <div className="panel">
          <h2>Регистрация отказа</h2>
          <form className="form-grid" onSubmit={onCreate}>
            <label>
              Скважина
              <select name="well_id" required defaultValue="">
                <option value="" disabled>
                  Выберите
                </option>
                {(wells.data?.items || []).map((w) => (
                  <option key={w.id} value={w.id}>
                    {w.name}
                  </option>
                ))}
              </select>
            </label>
            <label>
              Тип отказа
              <input name="failure_type" required placeholder="Например: Перегрев ПЭД" />
            </label>
            <label>
              Тяжесть
              <select name="severity" defaultValue="medium">
                <option value="low">low</option>
                <option value="medium">medium</option>
                <option value="high">high</option>
              </select>
            </label>
            <label>
              Дата
              <input
                name="occurred_at"
                type="datetime-local"
                required
                defaultValue={new Date().toISOString().slice(0, 16)}
              />
            </label>
            <label>
              Описание
              <textarea name="description" rows={2} />
            </label>
            <button className="btn primary" disabled={create.isPending}>
              Сохранить
            </button>
            {create.isError && (
              <div className="state-box error">{(create.error as Error).message}</div>
            )}
          </form>
        </div>
      )}

      <div className="panel">
        {events.isLoading && <div className="state-box">Загрузка...</div>}
        {events.error && <div className="state-box error">{(events.error as Error).message}</div>}
        {events.data && (
          <div className="table-wrap">
            <table className="data">
              <thead>
                <tr>
                  <th>Дата</th>
                  <th>Тип</th>
                  <th>Скважина</th>
                  <th>Событие</th>
                  <th>Описание</th>
                </tr>
              </thead>
              <tbody>
                {events.data.map(
                  (e: {
                    id: number;
                    event_kind: string;
                    well_id: number;
                    well_name?: string;
                    title: string;
                    occurred_at: string;
                    description?: string;
                  }) => (
                    <tr key={`${e.event_kind}-${e.id}`}>
                      <td>{formatDate(e.occurred_at)}</td>
                      <td>{e.event_kind}</td>
                      <td>
                        <Link to={`/wells/${e.well_id}`}>{e.well_name}</Link>
                      </td>
                      <td>{e.title}</td>
                      <td style={{ whiteSpace: "normal" }}>{e.description || "—"}</td>
                    </tr>
                  )
                )}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
