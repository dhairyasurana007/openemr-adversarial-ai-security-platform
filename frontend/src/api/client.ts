import axios from "axios";

import { addApiTrafficEntry, toSafeBody } from "./traffic";

const api = axios.create({ baseURL: import.meta.env.VITE_API_URL ?? "/api" });

api.interceptors.request.use((cfg) => {
  const token = localStorage.getItem("agentforge_token");
  if (token) {
    cfg.headers.Authorization = `Bearer ${token}`;
  }
  const method = (cfg.method ?? "GET").toUpperCase();
  const url = `${cfg.baseURL ?? ""}${cfg.url ?? ""}`;
  const traceId = crypto.randomUUID();
  (cfg as typeof cfg & { __trace_id?: string; __trace_started_ms?: number }).__trace_id = traceId;
  (cfg as typeof cfg & { __trace_id?: string; __trace_started_ms?: number }).__trace_started_ms = Date.now();
  addApiTrafficEntry({
    id: traceId,
    phase: "request",
    method,
    url,
    request_body: toSafeBody(cfg.data),
    timestamp: new Date().toISOString(),
  });
  return cfg;
});

api.interceptors.response.use(
  (response) => {
    const cfg = response.config;
    const meta = cfg as typeof cfg & { __trace_id?: string; __trace_started_ms?: number };
    const startedMs = meta.__trace_started_ms ?? Date.now();
    addApiTrafficEntry({
      id: meta.__trace_id ?? crypto.randomUUID(),
      phase: "response",
      method: (cfg.method ?? "GET").toUpperCase(),
      url: `${cfg.baseURL ?? ""}${cfg.url ?? ""}`,
      status: response.status,
      duration_ms: Date.now() - startedMs,
      request_body: toSafeBody(cfg.data),
      response_body: toSafeBody(response.data),
      timestamp: new Date().toISOString(),
    });
    return response;
  },
  (error) => {
    const cfg = error.config ?? {};
    const meta = cfg as typeof cfg & { __trace_id?: string; __trace_started_ms?: number };
    const startedMs = meta.__trace_started_ms ?? Date.now();
    addApiTrafficEntry({
      id: meta.__trace_id ?? crypto.randomUUID(),
      phase: "error",
      method: (cfg.method ?? "GET").toUpperCase(),
      url: `${cfg.baseURL ?? ""}${cfg.url ?? ""}`,
      status: error.response?.status,
      duration_ms: Date.now() - startedMs,
      request_body: toSafeBody(cfg.data),
      response_body: toSafeBody(error.response?.data),
      error_message: error.message,
      timestamp: new Date().toISOString(),
    });
    return Promise.reject(error);
  },
);

export default api;
