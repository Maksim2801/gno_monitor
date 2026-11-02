import axios from "axios";

const API_URL = import.meta.env.VITE_API_URL || "/api/v1";

export const api = axios.create({
  baseURL: API_URL,
  timeout: 60000,
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem("gno_token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

api.interceptors.response.use(
  (r) => r,
  async (error) => {
    const status = error.response?.status;
    let data = error.response?.data;
    if (typeof Blob !== "undefined" && data instanceof Blob) {
      try {
        const text = await data.text();
        data = text ? JSON.parse(text) : null;
      } catch {
        data = null;
      }
    }
    const detail = data?.detail;
    const message =
      typeof detail === "string"
        ? detail
        : Array.isArray(detail)
          ? detail.map((d: { msg?: string }) => d.msg).join("; ")
          : error.message || "Ошибка запроса";
    if (status === 401 && !error.config?.url?.includes("/auth/login")) {
      localStorage.removeItem("gno_token");
      if (!window.location.pathname.includes("/login")) {
        window.location.href = "/login";
      }
    }
    return Promise.reject(new Error(message));
  }
);
