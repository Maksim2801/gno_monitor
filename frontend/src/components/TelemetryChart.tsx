import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { TelemetrySeries } from "../types";

const COLORS = ["#2f9e7b", "#3a7ca5", "#d4a017", "#d64545", "#9b59b6", "#1abc9c"];

export function TelemetryChart({ series }: { series: TelemetrySeries[] }) {
  if (!series.length || series.every((s) => s.points.length === 0)) {
    return <div className="state-box">Нет данных телеметрии за выбранный период</div>;
  }

  const timeMap = new Map<string, Record<string, number | string>>();
  series.forEach((s) => {
    s.points.forEach((p) => {
      const key = p.recorded_at;
      const row = timeMap.get(key) || { time: new Date(key).toLocaleString("ru-RU") };
      row[s.parameter_code] = p.value;
      timeMap.set(key, row);
    });
  });
  const data = Array.from(timeMap.entries())
    .sort((a, b) => a[0].localeCompare(b[0]))
    .map(([, v]) => v);

  return (
    <div style={{ width: "100%", height: 360 }}>
      <ResponsiveContainer>
        <LineChart data={data}>
          <CartesianGrid stroke="#2a3644" strokeDasharray="3 3" />
          <XAxis dataKey="time" minTickGap={40} tick={{ fill: "#8b9aab", fontSize: 11 }} />
          <YAxis tick={{ fill: "#8b9aab", fontSize: 11 }} />
          <Tooltip
            contentStyle={{ background: "#1c2530", border: "1px solid #2a3644" }}
          />
          <Legend />
          {series.map((s, i) => (
            <Line
              key={s.parameter_code}
              type="monotone"
              dataKey={s.parameter_code}
              name={`${s.parameter_code} (${s.unit})`}
              stroke={COLORS[i % COLORS.length]}
              dot={false}
              strokeWidth={2}
            />
          ))}
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
