export type TelemetryParam = {
  code: string;
  name: string;
  unit: string;
  group: "process" | "electric" | "mechanical";
};

export const TELEMETRY_PARAMS: TelemetryParam[] = [
  { code: "intake_pressure", name: "Давление на приёме", unit: "МПа", group: "process" },
  { code: "temperature", name: "Температура", unit: "°C", group: "process" },
  { code: "motor_temperature", name: "Температура ПЭД", unit: "°C", group: "electric" },
  { code: "current_a", name: "Ток фазы A", unit: "А", group: "electric" },
  { code: "vibration", name: "Вибрация", unit: "мм/с", group: "mechanical" },
  { code: "flow_rate", name: "Дебит жидкости", unit: "м³/сут", group: "process" },
  { code: "rpm", name: "Обороты", unit: "об/мин", group: "mechanical" },
  { code: "power", name: "Мощность", unit: "кВт", group: "electric" },
  { code: "load", name: "Загрузка", unit: "%", group: "electric" },
];

export const PARAM_GROUPS: { id: TelemetryParam["group"]; title: string }[] = [
  { id: "process", title: "Процесс" },
  { id: "electric", title: "Электрика" },
  { id: "mechanical", title: "Механика" },
];

const PARAM_BY_CODE = Object.fromEntries(TELEMETRY_PARAMS.map((p) => [p.code, p]));

export function paramLabel(code: string, withUnit = false) {
  const param = PARAM_BY_CODE[code];
  if (!param) return code;
  return withUnit ? `${param.name}, ${param.unit}` : param.name;
}
