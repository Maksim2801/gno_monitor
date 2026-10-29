import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { dashboardApi } from "../api/endpoints";
import { RiskBadge, StatusBadge } from "../components/StatusBadge";
import { formatDate, formatNumber } from "../utils/format";

export function DashboardPage() {
  const { data, isLoading, error, refetch, isFetching } = useQuery({
    queryKey: ["dashboard"],
    queryFn: dashboardApi.get,
    refetchInterval: 30000,
  });

  if (isLoading) return <div className="state-box">Загрузка панели...</div>;
  if (error || !data)
    return (
      <div className="state-box error">
        {(error as Error)?.message || "Не удалось загрузить панель"}
      </div>
    );

  const riskData = [
    { name: "Низкий", value: data.risk_distribution.low },
    { name: "Средний", value: data.risk_distribution.medium },
    { name: "Высокий", value: data.risk_distribution.high },
    { name: "н/д", value: data.risk_distribution.unknown },
  ];

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", gap: "1rem" }}>
        <div>
          <h1 className="page-title">Панель мониторинга фонда</h1>
          <p className="page-subtitle">
            Сводка по скважинам, рискам и активным тревогам · обновлено{" "}
            {formatDate(data.generated_at)}
          </p>
        </div>
        <button className="btn" onClick={() => refetch()} disabled={isFetching}>
          Обновить
        </button>
      </div>

      <div className="grid-kpi">
        <div className="kpi">
          <div className="kpi-label">Скважин</div>
          <div className="kpi-value">{data.total_wells}</div>
        </div>
        <div className="kpi">
          <div className="kpi-label">Норма</div>
          <div className="kpi-value">{data.normal_count}</div>
        </div>
        <div className="kpi">
          <div className="kpi-label">Предупреждения</div>
          <div className="kpi-value">{data.warning_count}</div>
        </div>
        <div className="kpi">
          <div className="kpi-label">Высокий риск / критика</div>
          <div className="kpi-value">{data.critical_count}</div>
        </div>
        <div className="kpi">
          <div className="kpi-label">Активные тревоги</div>
          <div className="kpi-value">{data.active_alerts}</div>
        </div>
      </div>

      <div className="stack-2">
        <div className="panel">
          <h2>Распределение по категориям риска</h2>
          <div style={{ height: 260 }}>
            <ResponsiveContainer>
              <BarChart data={riskData}>
                <CartesianGrid stroke="#2a3644" strokeDasharray="3 3" />
                <XAxis dataKey="name" tick={{ fill: "#8b9aab" }} />
                <YAxis allowDecimals={false} tick={{ fill: "#8b9aab" }} />
                <Tooltip contentStyle={{ background: "#1c2530", border: "1px solid #2a3644" }} />
                <Bar dataKey="value" fill="#2f9e7b" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
        <div className="panel">
          <h2>Последние тревоги</h2>
          {data.recent_alerts.length === 0 ? (
            <div className="state-box">Активных тревог нет</div>
          ) : (
            <div className="table-wrap">
              <table className="data">
                <thead>
                  <tr>
                    <th>Скважина</th>
                    <th>Уровень</th>
                    <th>Сообщение</th>
                  </tr>
                </thead>
                <tbody>
                  {data.recent_alerts.map((a) => (
                    <tr key={a.id}>
                      <td>
                        <Link to={`/wells/${a.well_id}`}>{a.well_name}</Link>
                      </td>
                      <td>
                        <span className={`badge ${a.severity}`}>{a.severity}</span>
                      </td>
                      <td style={{ whiteSpace: "normal", maxWidth: 280 }}>{a.message}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>

      <div className="panel">
        <h2>Скважины, требующие внимания</h2>
        <div className="table-wrap">
          <table className="data">
            <thead>
              <tr>
                <th>Скважина</th>
                <th>Месторождение</th>
                <th>Статус</th>
                <th>Риск</th>
                <th>P отказа</th>
                <th>Тревоги</th>
              </tr>
            </thead>
            <tbody>
              {data.attention_wells.map((w) => (
                <tr key={w.id}>
                  <td>
                    <Link to={`/wells/${w.id}`}>{w.name}</Link>
                  </td>
                  <td>{w.oil_field}</td>
                  <td>
                    <StatusBadge status={w.status} />
                  </td>
                  <td>
                    <RiskBadge risk={w.risk_category} />
                  </td>
                  <td className="mono">{formatNumber(w.failure_probability, 3)}</td>
                  <td>{w.active_alerts}</td>
                </tr>
              ))}
              {data.attention_wells.length === 0 && (
                <tr>
                  <td colSpan={6}>
                    <div className="state-box">Проблемных объектов нет</div>
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      <div className="panel">
        <h2>Последние эксплуатационные события</h2>
        <div className="table-wrap">
          <table className="data">
            <thead>
              <tr>
                <th>Дата</th>
                <th>Тип</th>
                <th>Скважина</th>
                <th>Событие</th>
              </tr>
            </thead>
            <tbody>
              {data.recent_events.map((e) => (
                <tr key={`${e.event_kind}-${e.id}`}>
                  <td>{formatDate(e.occurred_at)}</td>
                  <td>{e.event_kind}</td>
                  <td>
                    <Link to={`/wells/${e.well_id}`}>{e.well_name}</Link>
                  </td>
                  <td>{e.title}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
