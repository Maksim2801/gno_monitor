import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { wellsApi } from "../api/endpoints";
import { RiskBadge, StatusBadge } from "../components/StatusBadge";
import { formatNumber } from "../utils/format";

export function WellsPage() {
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState("");
  const [risk, setRisk] = useState("");
  const [page, setPage] = useState(1);

  const { data, isLoading, error } = useQuery({
    queryKey: ["wells", search, status, risk, page],
    queryFn: () =>
      wellsApi.list({
        page,
        page_size: 15,
        search: search || undefined,
        status: status || undefined,
        risk_category: risk || undefined,
      }),
  });

  return (
    <div>
      <h1 className="page-title">Фонд скважин</h1>
      <p className="page-subtitle">Поиск, фильтрация и переход к карточке объекта</p>

      <div className="filters">
        <input
          placeholder="Поиск по имени / инв. №"
          value={search}
          onChange={(e) => {
            setPage(1);
            setSearch(e.target.value);
          }}
        />
        <select
          value={status}
          onChange={(e) => {
            setPage(1);
            setStatus(e.target.value);
          }}
        >
          <option value="">Все статусы</option>
          <option value="normal">Норма</option>
          <option value="warning">Предупреждение</option>
          <option value="critical">Критично</option>
          <option value="stopped">Останов</option>
        </select>
        <select
          value={risk}
          onChange={(e) => {
            setPage(1);
            setRisk(e.target.value);
          }}
        >
          <option value="">Все уровни риска</option>
          <option value="low">Низкий</option>
          <option value="medium">Средний</option>
          <option value="high">Высокий</option>
        </select>
      </div>

      <div className="panel">
        {isLoading && <div className="state-box">Загрузка...</div>}
        {error && <div className="state-box error">{(error as Error).message}</div>}
        {data && (
          <>
            <div className="table-wrap">
              <table className="data">
                <thead>
                  <tr>
                    <th>Скважина</th>
                    <th>Месторождение</th>
                    <th>Куст</th>
                    <th>Статус</th>
                    <th>Риск</th>
                    <th>P отказа</th>
                    <th>Тревоги</th>
                  </tr>
                </thead>
                <tbody>
                  {data.items.map((w) => (
                    <tr key={w.id}>
                      <td>
                        <Link to={`/wells/${w.id}`}>{w.name}</Link>
                      </td>
                      <td>{w.oil_field}</td>
                      <td>{w.well_pad}</td>
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
                  {data.items.length === 0 && (
                    <tr>
                      <td colSpan={7}>
                        <div className="state-box">Объекты не найдены</div>
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
            <div style={{ display: "flex", gap: "0.5rem", marginTop: "0.85rem" }}>
              <button className="btn" disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>
                Назад
              </button>
              <span className="muted">
                Стр. {data.page} / {Math.max(data.pages, 1)} · всего {data.total}
              </span>
              <button
                className="btn"
                disabled={page >= data.pages}
                onClick={() => setPage((p) => p + 1)}
              >
                Вперёд
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
