import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { alertsApi } from "../api/endpoints";
import { useAuth } from "../features/auth/AuthContext";
import { formatDate } from "../utils/format";

export function AlertsPage() {
  const { canWrite } = useAuth();
  const qc = useQueryClient();
  const [status, setStatus] = useState("new");
  const [severity, setSeverity] = useState("");

  const { data, isLoading, error } = useQuery({
    queryKey: ["alerts", status, severity],
    queryFn: () =>
      alertsApi.list({
        page: 1,
        page_size: 50,
        status: status || undefined,
        severity: severity || undefined,
      }),
  });

  const update = useMutation({
    mutationFn: ({ id, next }: { id: number; next: string }) =>
      alertsApi.updateStatus(id, next),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["alerts"] });
      void qc.invalidateQueries({ queryKey: ["alerts-badge"] });
      void qc.invalidateQueries({ queryKey: ["dashboard"] });
    },
  });

  return (
    <div>
      <h1 className="page-title">Центр уведомлений</h1>
      <p className="page-subtitle">
        Пороговые отклонения, аномалии и превышение риска отказа · статусы: new →
        acknowledged → closed
      </p>

      <div className="filters">
        <select value={status} onChange={(e) => setStatus(e.target.value)}>
          <option value="">Все статусы</option>
          <option value="new">Новые</option>
          <option value="acknowledged">Подтверждённые</option>
          <option value="closed">Закрытые</option>
        </select>
        <select value={severity} onChange={(e) => setSeverity(e.target.value)}>
          <option value="">Все уровни</option>
          <option value="info">info</option>
          <option value="warning">warning</option>
          <option value="critical">critical</option>
        </select>
      </div>

      <div className="panel">
        {isLoading && <div className="state-box">Загрузка...</div>}
        {error && <div className="state-box error">{(error as Error).message}</div>}
        {data && (
          <div className="table-wrap">
            <table className="data">
              <thead>
                <tr>
                  <th>Дата</th>
                  <th>Скважина</th>
                  <th>Тип</th>
                  <th>Уровень</th>
                  <th>Статус</th>
                  <th>Сообщение</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {data.items.map((a) => (
                  <tr key={a.id}>
                    <td>{formatDate(a.created_at)}</td>
                    <td>
                      <Link to={`/wells/${a.well_id}`}>{a.well_name}</Link>
                    </td>
                    <td>{a.alert_type}</td>
                    <td>
                      <span className={`badge ${a.severity}`}>{a.severity}</span>
                    </td>
                    <td>
                      <span className={`badge ${a.status}`}>{a.status}</span>
                    </td>
                    <td style={{ whiteSpace: "normal", maxWidth: 360 }}>{a.message}</td>
                    <td>
                      {canWrite && a.status === "new" && (
                        <button
                          className="btn"
                          onClick={() =>
                            update.mutate({ id: a.id, next: "acknowledged" })
                          }
                        >
                          Подтвердить
                        </button>
                      )}
                      {canWrite && a.status !== "closed" && (
                        <button
                          className="btn"
                          style={{ marginLeft: 6 }}
                          onClick={() => {
                            if (window.confirm("Закрыть уведомление?")) {
                              update.mutate({ id: a.id, next: "closed" });
                            }
                          }}
                        >
                          Закрыть
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
                {data.items.length === 0 && (
                  <tr>
                    <td colSpan={7}>
                      <div className="state-box">Уведомлений нет</div>
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
