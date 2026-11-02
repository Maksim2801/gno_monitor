import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { telemetryApi, wellsApi } from "../api/endpoints";
import { TelemetryChart } from "../components/TelemetryChart";
import { PARAM_GROUPS, TELEMETRY_PARAMS } from "../utils/parameters";

type IntervalPreset = "12h" | "24h" | "3d" | "7d" | "custom";

const PRESET_HOURS: Record<Exclude<IntervalPreset, "custom">, number> = {
  "12h": 12,
  "24h": 24,
  "3d": 72,
  "7d": 168,
};

const DEFAULT_SELECTED = ["intake_pressure", "motor_temperature", "current_a"];

function toLocalInputValue(date: Date) {
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`;
}

function fromLocalInputValue(value: string) {
  return new Date(value);
}

export function TelemetryPage() {
  const [wellId, setWellId] = useState<number | "">("");
  const [selected, setSelected] = useState<string[]>(DEFAULT_SELECTED);
  const [interval, setInterval] = useState<IntervalPreset>("24h");
  const [customFrom, setCustomFrom] = useState(() =>
    toLocalInputValue(new Date(Date.now() - 24 * 3600 * 1000))
  );
  const [customTo, setCustomTo] = useState(() => toLocalInputValue(new Date()));

  const wellsQuery = useQuery({
    queryKey: ["wells-all"],
    queryFn: () => wellsApi.list({ page: 1, page_size: 100 }),
  });

  const range = useMemo(() => {
    if (interval === "custom") {
      const from = fromLocalInputValue(customFrom);
      const to = fromLocalInputValue(customTo);
      return {
        from: from.toISOString(),
        to: to.toISOString(),
        valid: !Number.isNaN(from.getTime()) && !Number.isNaN(to.getTime()) && from <= to,
      };
    }
    const hours = PRESET_HOURS[interval];
    const to = new Date();
    const from = new Date(Date.now() - hours * 3600 * 1000);
    return { from: from.toISOString(), to: to.toISOString(), valid: true };
  }, [interval, customFrom, customTo]);

  const seriesQuery = useQuery({
    queryKey: ["telemetry-page", wellId, selected.join(","), interval, range.from, range.to],
    queryFn: () =>
      telemetryApi.series(Number(wellId), range.from, range.to, selected.join(",")),
    enabled: !!wellId && selected.length > 0 && range.valid,
  });

  function onIntervalChange(value: IntervalPreset) {
    setInterval(value);
    if (value === "custom") {
      const now = new Date();
      setCustomTo(toLocalInputValue(now));
      setCustomFrom(toLocalInputValue(new Date(now.getTime() - 24 * 3600 * 1000)));
    }
  }

  function toggleParam(code: string) {
    setSelected((prev) =>
      prev.includes(code) ? prev.filter((item) => item !== code) : [...prev, code]
    );
  }

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
        <select
          value={interval}
          onChange={(e) => onIntervalChange(e.target.value as IntervalPreset)}
        >
          <option value="12h">12 часов</option>
          <option value="24h">24 часа</option>
          <option value="3d">3 дня</option>
          <option value="7d">7 дней</option>
          <option value="custom">Ручная настройка</option>
        </select>
        {interval === "custom" && (
          <>
            <label style={{ display: "flex", gap: "0.35rem", alignItems: "center" }}>
              От
              <input
                type="datetime-local"
                value={customFrom}
                onChange={(e) => setCustomFrom(e.target.value)}
              />
            </label>
            <label style={{ display: "flex", gap: "0.35rem", alignItems: "center" }}>
              До
              <input
                type="datetime-local"
                value={customTo}
                onChange={(e) => setCustomTo(e.target.value)}
              />
            </label>
          </>
        )}
      </div>

      {interval === "custom" && !range.valid && (
        <div className="state-box error">Укажите корректный период: «От» не позже «До»</div>
      )}

      <div className="panel">
        <div className="panel-head">
          <h2>Параметры</h2>
          <div className="panel-actions">
            <button
              type="button"
              className="btn sm"
              onClick={() => setSelected(TELEMETRY_PARAMS.map((p) => p.code))}
            >
              Выбрать все
            </button>
            <button type="button" className="btn sm" onClick={() => setSelected([])}>
              Сбросить
            </button>
          </div>
        </div>

        <div className="param-groups">
          {PARAM_GROUPS.map((group) => {
            const items = TELEMETRY_PARAMS.filter((p) => p.group === group.id);
            return (
              <div key={group.id}>
                <h3 className="param-group-title">{group.title}</h3>
                <div className="param-grid">
                  {items.map((param) => {
                    const active = selected.includes(param.code);
                    return (
                      <label
                        key={param.code}
                        className={`param-chip${active ? " is-active" : ""}`}
                      >
                        <input
                          type="checkbox"
                          checked={active}
                          onChange={() => toggleParam(param.code)}
                        />
                        <span>
                          <span className="param-chip-title">{param.name}</span>
                          <span className="param-chip-meta">{param.unit}</span>
                        </span>
                      </label>
                    );
                  })}
                </div>
              </div>
            );
          })}
        </div>

        {selected.length === 0 && (
          <div className="state-box" style={{ paddingTop: "1rem" }}>
            Выберите хотя бы один параметр
          </div>
        )}
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
