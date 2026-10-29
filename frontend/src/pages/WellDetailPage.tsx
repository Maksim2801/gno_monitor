import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";
import { analyticsApi, eventsApi, telemetryApi, wellsApi } from "../api/endpoints";
import { TelemetryChart } from "../components/TelemetryChart";
import { RiskBadge, StatusBadge } from "../components/StatusBadge";
import { useAuth } from "../features/auth/AuthContext";
import { formatDate, formatNumber } from "../utils/format";

export function WellDetailPage() {
  const { id } = useParams();
  const wellId = Number(id);
  const { canWrite } = useAuth();
  const qc = useQueryClient();

  const wellQuery = useQuery({
    queryKey: ["well", wellId],
    queryFn: () => wellsApi.get(wellId),
    enabled: Number.isFinite(wellId),
  });

  const to = new Date();
  const from = new Date(Date.now() - 48 * 3600 * 1000);
  const telemetryQuery = useQuery({
    queryKey: ["well-telemetry", wellId],
    queryFn: () =>
      telemetryApi.series(
        wellId,
        from.toISOString(),
        to.toISOString(),
        "intake_pressure,motor_temperature,current_a,vibration,flow_rate,rpm"
      ),
    enabled: Number.isFinite(wellId),
  });

  const eventsQuery = useQuery({
    queryKey: ["well-events", wellId],
    queryFn: () => eventsApi.list({ well_id: wellId, limit: 20 }),
    enabled: Number.isFinite(wellId),
  });

  const runAnalytics = useMutation({
    mutationFn: () => analyticsApi.run(wellId),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["well", wellId] });
      void qc.invalidateQueries({ queryKey: ["predictions"] });
      void qc.invalidateQueries({ queryKey: ["alerts"] });
    },
  });

  if (wellQuery.isLoading) return <div className="state-box">Загрузка карточки...</div>;
  if (wellQuery.error || !wellQuery.data)
    return (
      <div className="state-box error">
        {(wellQuery.error as Error)?.message || "Скважина не найдена"}
      </div>
    );

  const well = wellQuery.data;
  const pred = well.latest_prediction;

  return (
    <div>
      <p className="muted">
        <Link to="/wells">← К списку</Link>
      </p>
      <div style={{ display: "flex", justifyContent: "space-between", gap: "1rem", flexWrap: "wrap" }}>
        <div>
          <h1 className="page-title">{well.name}</h1>
          <p className="page-subtitle">
            {well.oil_field.name} · {well.well_pad.name} · инв. {well.inventory_number || "—"}
          </p>
        </div>
        <div style={{ display: "flex", gap: "0.5rem", alignItems: "center" }}>
          <StatusBadge status={well.status} />
          {canWrite && (
            <button
              className="btn primary"
              disabled={runAnalytics.isPending}
              onClick={() => runAnalytics.mutate()}
            >
              {runAnalytics.isPending ? "Расчёт..." : "Запустить аналитику"}
            </button>
          )}
        </div>
      </div>
      {runAnalytics.isError && (
        <div className="state-box error">{(runAnalytics.error as Error).message}</div>
      )}
      {runAnalytics.isSuccess && (
        <div className="panel">{(runAnalytics.data as { message: string }).message}</div>
      )}

      <div className="grid-kpi">
        <div className="kpi">
          <div className="kpi-label">Глубина, м</div>
          <div className="kpi-value">{formatNumber(well.depth_m, 0)}</div>
        </div>
        <div className="kpi">
          <div className="kpi-label">Активные тревоги</div>
          <div className="kpi-value">{well.active_alerts}</div>
        </div>
        <div className="kpi">
          <div className="kpi-label">Риск отказа</div>
          <div className="kpi-value" style={{ fontSize: "1.2rem" }}>
            <RiskBadge risk={pred?.risk_category} />
          </div>
        </div>
        <div className="kpi">
          <div className="kpi-label">P отказа / {pred?.horizon_days ?? 7} сут.</div>
          <div className="kpi-value">{formatNumber(pred?.failure_probability, 3)}</div>
        </div>
      </div>

      <div className="stack-2">
        <div className="panel">
          <h2>Телеметрия (48 ч)</h2>
          {telemetryQuery.isLoading ? (
            <div className="state-box">Загрузка графиков...</div>
          ) : telemetryQuery.error ? (
            <div className="state-box error">{(telemetryQuery.error as Error).message}</div>
          ) : (
            <TelemetryChart series={telemetryQuery.data || []} />
          )}
        </div>
        <div className="panel">
          <h2>Прогноз и аномалия</h2>
          {pred ? (
            <>
              <p>
                Модель: <span className="mono">{pred.model_name}</span> v{pred.model_version}
              </p>
              <p className="muted">{pred.reliability_note}</p>
              {!pred.is_reliable && (
                <p className="state-box error" style={{ textAlign: "left" }}>
                  Достоверный прогноз ограничен: недостаточно размеченной истории.
                </p>
              )}
              <p>Предполагаемый тип отказа: {pred.presumed_failure_type || "—"}</p>
              <h3 style={{ fontSize: "0.95rem" }}>Ключевые факторы</h3>
              <ul>
                {(pred.top_factors || []).map((f) => (
                  <li key={f.factor}>
                    {f.factor}: {formatNumber(f.importance, 3)}
                  </li>
                ))}
              </ul>
            </>
          ) : (
            <div className="state-box">Прогноз ещё не рассчитан</div>
          )}
          {well.latest_anomaly && (
            <p style={{ marginTop: "1rem" }}>
              Аномалия: score={formatNumber(well.latest_anomaly.anomaly_score, 3)},{" "}
              {well.latest_anomaly.is_anomaly ? "да" : "нет"} ({well.latest_anomaly.algorithm})
            </p>
          )}
        </div>
      </div>

      <div className="panel">
        <h2>Оборудование</h2>
        <div className="table-wrap">
          <table className="data">
            <thead>
              <tr>
                <th>Тип</th>
                <th>Наименование</th>
                <th>Модель</th>
                <th>Мощность</th>
                <th>Статус</th>
              </tr>
            </thead>
            <tbody>
              {well.equipment.map((e) => (
                <tr key={e.id}>
                  <td>{e.equipment_type}</td>
                  <td>{e.name}</td>
                  <td>
                    {e.manufacturer} {e.model}
                  </td>
                  <td>{formatNumber(e.rated_power_kw, 0)} кВт</td>
                  <td>{e.status}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <div className="panel">
        <h2>История событий</h2>
        {eventsQuery.isLoading ? (
          <div className="state-box">Загрузка...</div>
        ) : (
          <div className="table-wrap">
            <table className="data">
              <thead>
                <tr>
                  <th>Дата</th>
                  <th>Тип</th>
                  <th>Событие</th>
                  <th>Описание</th>
                </tr>
              </thead>
              <tbody>
                {(eventsQuery.data || []).map(
                  (e: {
                    id: number;
                    event_kind: string;
                    title: string;
                    occurred_at: string;
                    description?: string;
                  }) => (
                    <tr key={`${e.event_kind}-${e.id}`}>
                      <td>{formatDate(e.occurred_at)}</td>
                      <td>{e.event_kind}</td>
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
