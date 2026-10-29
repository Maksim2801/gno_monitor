import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { telemetryApi, wellsApi } from "../api/endpoints";
import { TelemetryChart } from "../components/TelemetryChart";

const PARAMS = [
  "intake_pressure",
  "temperature",
  "motor_temperature",
  "current_a",
  "vibration",
  "flow_rate",
  "rpm",
  "power",
  "load",
];

export function TelemetryPage() {
  const [wellId, setWellId] = useState<number | "">("");
  const [selected, setSelected] = useState(["intake_pressure", "motor_temperature", "current_a"]);
  const [hours, setHours] = useState(48);

  const wellsQuery = useQuery({
    queryKey: ["wells-all"],
    queryFn: () => wellsApi.list({ page: 1, page_size: 100 }),
  });

  const range = useMemo(() => {
    const to = new Date();
    const from = new Date(Date.now() - hours * 3600 * 1000);
    return { from: from.toISOString(), to: to.toISOString() };
  }, [hours]);

  const seriesQuery = useQuery({
    queryKey: ["telemetry-page", wellId, selected.join(","), hours],
    queryFn: () =>
      telemetryApi.series(Number(wellId), range.from, range.to, selected.join(",")),
    enabled: !!wellId && selected.length > 0,
  });

  return (
    <div>
      <h1 className="page-title">Телеметрия</h1>
      <p className="page-subtitle">Временные ряды параметров ГНО</p>

      <div className="filters">
        <select
          value={wellId}
          onChange={(e) => setWellId(e.target.value ? Number(e.target.value) : "")}
        >
          <option value="">Выберите скважину</option>
          {(wellsQuery.data?.items || []).map((w) => (
            <option key={w.id} value={w.id}>
              {w.name}
            </option>
          ))}
        </select>
        <select value={hours} onChange={(e) => setHours(Number(e.target.value))}>
          <option value={24}>24 часа</option>
          <option value={48}>48 часов</option>
          <option value={168}>7 суток</option>
        </select>
      </div>

      <div className="panel">
        <h2>Параметры</h2>
        <div className="filters">
          {PARAMS.map((p) => (
            <label key={p} style={{ display: "flex", gap: "0.35rem", alignItems: "center" }}>
              <input
                type="checkbox"
                checked={selected.includes(p)}
                onChange={(e) =>
                  setSelected((prev) =>
                    e.target.checked ? [...prev, p] : prev.filter((x) => x !== p)
                  )
                }
              />
              {p}
            </label>
          ))}
        </div>
      </div>

      <div className="panel">
        {!wellId && <div className="state-box">Выберите скважину</div>}
        {wellId && seriesQuery.isLoading && <div className="state-box">Загрузка...</div>}
        {seriesQuery.error && (
          <div className="state-box error">{(seriesQuery.error as Error).message}</div>
        )}
        {seriesQuery.data && <TelemetryChart series={seriesQuery.data} />}
      </div>
    </div>
  );
}
