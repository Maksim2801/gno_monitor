export type UserRole = "admin" | "technologist" | "viewer";

export interface User {
  id: number;
  username: string;
  full_name: string;
  email?: string | null;
  role: UserRole;
  role_name: string;
  is_active: boolean;
}

export interface Paginated<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}

export interface WellListItem {
  id: number;
  name: string;
  inventory_number?: string | null;
  status: string;
  depth_m?: number | null;
  oil_field: string;
  well_pad: string;
  risk_category?: string | null;
  failure_probability?: number | null;
  active_alerts: number;
}

export interface WellDetail {
  id: number;
  name: string;
  inventory_number?: string | null;
  status: string;
  depth_m?: number | null;
  notes?: string | null;
  commissioning_date?: string | null;
  oil_field: { id: number; name: string; code: string; region?: string | null };
  well_pad: {
    id: number;
    name: string;
    code: string;
    oil_field_id: number;
    oil_field_name?: string | null;
  };
  equipment: Array<{
    id: number;
    equipment_type: string;
    name: string;
    manufacturer?: string | null;
    model?: string | null;
    serial_number?: string | null;
    rated_power_kw?: number | null;
    status: string;
  }>;
  sensors: Array<{
    id: number;
    tag: string;
    parameter_code: string;
    parameter_name: string;
    unit: string;
    is_active: boolean;
  }>;
  latest_prediction?: Prediction | null;
  latest_anomaly?: Anomaly | null;
  latest_telemetry: Record<string, number | null>;
  active_alerts: number;
}

export interface Prediction {
  id: number;
  well_id: number;
  well_name?: string | null;
  calculated_at: string;
  model_name: string;
  model_version: string;
  failure_probability: number;
  risk_category: string;
  horizon_days: number;
  top_factors?: Array<{ factor: string; importance: number; value?: number }> | null;
  presumed_failure_type?: string | null;
  is_reliable: boolean;
  reliability_note?: string | null;
}

export interface Anomaly {
  id: number;
  well_id: number;
  well_name?: string | null;
  calculated_at: string;
  algorithm: string;
  anomaly_score: number;
  is_anomaly: boolean;
  details?: string | null;
}

export interface Alert {
  id: number;
  well_id: number;
  well_name?: string | null;
  alert_type: string;
  severity: string;
  message: string;
  status: string;
  created_at: string;
  acknowledged_at?: string | null;
  closed_at?: string | null;
  anomaly_result_id?: number | null;
  prediction_result_id?: number | null;
}

export interface TelemetryPoint {
  id: number;
  well_id: number;
  sensor_id: number;
  parameter_code: string;
  value: number;
  unit: string;
  quality_flag: string;
  source: string;
  recorded_at: string;
}

export interface TelemetrySeries {
  parameter_code: string;
  unit: string;
  points: TelemetryPoint[];
}

export interface Dashboard {
  total_wells: number;
  normal_count: number;
  warning_count: number;
  critical_count: number;
  stopped_count: number;
  active_alerts: number;
  risk_distribution: { low: number; medium: number; high: number; unknown: number };
  attention_wells: WellListItem[];
  recent_events: Array<{
    id: number;
    event_kind: string;
    well_id: number;
    well_name?: string | null;
    title: string;
    occurred_at: string;
    severity?: string | null;
    description?: string | null;
  }>;
  recent_alerts: Alert[];
  generated_at: string;
}

export interface Report {
  id: number;
  report_type: string;
  title: string;
  period_start: string;
  period_end: string;
  parameters?: Record<string, unknown> | null;
  content_json?: Record<string, unknown> | null;
  content_text?: string | null;
  file_format?: string | null;
  created_at: string;
}
