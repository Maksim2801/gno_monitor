import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { analyticsApi } from "../api/endpoints";
import { RiskBadge } from "../components/StatusBadge";
import { useAuth } from "../features/auth/AuthContext";
import { formatDate, formatNumber } from "../utils/format";

export function AnalyticsPage() {
  const { canWrite } = useAuth();
  const qc = useQueryClient();

  const predictions = useQuery({
    queryKey: ["predictions"],
    queryFn: () => analyticsApi.predictions(),
  });
  const anomalies = useQuery({
    queryKey: ["anomalies"],
    queryFn: () => analyticsApi.anomalies(),
  });

  const run = useMutation({
    mutationFn: () => analyticsApi.run(),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["predictions"] });
      void qc.invalidateQueries({ queryKey: ["anomalies"] });
      void qc.invalidateQueries({ queryKey: ["dashboard"] });
      void qc.invalidateQueries({ queryKey: ["alerts"] });
    },
  });

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", gap: "1rem" }}>
        <div>
          <h1 className="page-title">Аналитика и прогнозы риска</h1>
          <p className="page-subtitle">
            Isolation Forest (аномалии) + Random Forest / экспертный fallback (риск отказа, 7 сут.)
          </p>
        </div>
        {canWrite && (
          <button className="btn primary" disabled={run.isPending} onClick={() => run.mutate()}>
            {run.isPending ? "Выполняется..." : "Пересчитать по фонду"}
          </button>
        )}
      </div>

      {run.isSuccess && (
        <div className="panel">
          {(run.data as { message: string }).message}. Создано прогнозов:{" "}
          {(run.data as { predictions_created: number }).predictions_created}, аномалий:{" "}
          {(run.data as { anomalies_created: number }).anomalies_created}, уведомлений:{" "}
          {(run.data as { alerts_created: number }).alerts_created}
        </div>
      )}
      {run.isError && <div className="state-box error">{(run.error as Error).message}</div>}

      <div className="panel">
        <h2>Последние оценки риска</h2>
        {predictions.isLoading && <div className="state-box">Загрузка...</div>}
        {predictions.error && (
          <div className="state-box error">{(predictions.error as Error).message}</div>
        )}
        {predictions.data && (
          <div className="table-wrap">
            <table className="data">
              <thead>
                <tr>
                  <th>Дата</th>
                  <th>Скважина</th>
                  <th>P отказа</th>
                  <th>Риск</th>
                  <th>Модель</th>
                  <th>Достоверность</th>
                </tr>
              </thead>
              <tbody>
                {predictions.data.map((p) => (
                  <tr key={p.id}>
                    <td>{formatDate(p.calculated_at)}</td>
                    <td>
                      <Link to={`/wells/${p.well_id}`}>{p.well_name}</Link>
                    </td>
                    <td className="mono">{formatNumber(p.failure_probability, 3)}</td>
                    <td>
                      <RiskBadge risk={p.risk_category} />
                    </td>
                    <td className="mono">{p.model_name}</td>
                    <td>{p.is_reliable ? "да" : "ограничена"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      <div className="panel">
        <h2>Аномалии</h2>
        {anomalies.isLoading && <div className="state-box">Загрузка...</div>}
        {anomalies.data && (
          <div className="table-wrap">
            <table className="data">
              <thead>
                <tr>
                  <th>Дата</th>
                  <th>Скважина</th>
                  <th>Score</th>
                  <th>Аномалия</th>
                  <th>Алгоритм</th>
                </tr>
              </thead>
              <tbody>
                {anomalies.data.map((a) => (
                  <tr key={a.id}>
                    <td>{formatDate(a.calculated_at)}</td>
                    <td>
                      <Link to={`/wells/${a.well_id}`}>{a.well_name}</Link>
                    </td>
                    <td className="mono">{formatNumber(a.anomaly_score, 3)}</td>
                    <td>{a.is_anomaly ? "да" : "нет"}</td>
                    <td>{a.algorithm}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
