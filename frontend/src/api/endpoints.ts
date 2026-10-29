import { api } from "./client";
import type {
  Alert,
  Anomaly,
  Dashboard,
  Paginated,
  Prediction,
  Report,
  TelemetrySeries,
  User,
  WellDetail,
  WellListItem,
} from "../types";

export const authApi = {
  login: async (username: string, password: string) => {
    const { data } = await api.post<{ access_token: string }>("/auth/login", {
      username,
      password,
    });
    return data;
  },
  me: async () => {
    const { data } = await api.get<User>("/auth/me");
    return data;
  },
};

export const dashboardApi = {
  get: async () => {
    const { data } = await api.get<Dashboard>("/dashboard");
    return data;
  },
};

export const wellsApi = {
  list: async (params: Record<string, string | number | undefined>) => {
    const { data } = await api.get<Paginated<WellListItem>>("/wells", { params });
    return data;
  },
  get: async (id: number) => {
    const { data } = await api.get<WellDetail>(`/wells/${id}`);
    return data;
  },
  fields: async () => {
    const { data } = await api.get("/wells/meta/fields");
    return data;
  },
};

export const telemetryApi = {
  series: async (
    wellId: number,
    dateFrom: string,
    dateTo: string,
    parameters?: string
  ) => {
    const { data } = await api.get<TelemetrySeries[]>(`/telemetry/wells/${wellId}`, {
      params: { date_from: dateFrom, date_to: dateTo, parameters },
    });
    return data;
  },
};

export const analyticsApi = {
  run: async (wellId?: number) => {
    const { data } = await api.post("/analytics/run", null, {
      params: wellId ? { well_id: wellId } : undefined,
    });
    return data;
  },
  predictions: async (wellId?: number) => {
    const { data } = await api.get<Prediction[]>("/analytics/predictions", {
      params: wellId ? { well_id: wellId } : undefined,
    });
    return data;
  },
  anomalies: async (wellId?: number) => {
    const { data } = await api.get<Anomaly[]>("/analytics/anomalies", {
      params: wellId ? { well_id: wellId } : undefined,
    });
    return data;
  },
};

export const alertsApi = {
  list: async (params: Record<string, string | number | undefined>) => {
    const { data } = await api.get<Paginated<Alert>>("/alerts", { params });
    return data;
  },
  updateStatus: async (id: number, status: string) => {
    const { data } = await api.patch<Alert>(`/alerts/${id}`, { status });
    return data;
  },
};

export const eventsApi = {
  list: async (params?: Record<string, string | number | undefined>) => {
    const { data } = await api.get("/events", { params });
    return data;
  },
  createFailure: async (payload: Record<string, unknown>) => {
    const { data } = await api.post("/events/failures", payload);
    return data;
  },
};

export const reportsApi = {
  list: async () => {
    const { data } = await api.get<Report[]>("/reports");
    return data;
  },
  create: async (payload: Record<string, unknown>) => {
    const { data } = await api.post<Report>("/reports", payload);
    return data;
  },
  get: async (id: number) => {
    const { data } = await api.get<Report>(`/reports/${id}`);
    return data;
  },
};

export const adminApi = {
  users: async () => {
    const { data } = await api.get<User[]>("/admin/users");
    return data;
  },
  createUser: async (payload: Record<string, unknown>) => {
    const { data } = await api.post<User>("/admin/users", payload);
    return data;
  },
  updateUser: async (id: number, payload: Record<string, unknown>) => {
    const { data } = await api.patch<User>(`/admin/users/${id}`, payload);
    return data;
  },
  roles: async () => {
    const { data } = await api.get("/admin/roles");
    return data;
  },
  sensorTypes: async () => {
    const { data } = await api.get("/admin/sensor-types");
    return data;
  },
};
