export type ApiTrafficPhase = "request" | "response" | "error";

export interface ApiTrafficEntry {
  id: string;
  phase: ApiTrafficPhase;
  method: string;
  url: string;
  status?: number;
  duration_ms?: number;
  request_body?: unknown;
  response_body?: unknown;
  error_message?: string;
  timestamp: string;
}

const MAX_ENTRIES = 200;
const entries: ApiTrafficEntry[] = [];
const listeners = new Set<() => void>();

function notify() {
  for (const listener of listeners) {
    listener();
  }
}

function redact(value: unknown): unknown {
  if (Array.isArray(value)) {
    return value.map(redact);
  }
  if (value && typeof value === "object") {
    const asRecord = value as Record<string, unknown>;
    const out: Record<string, unknown> = {};
    for (const [key, nested] of Object.entries(asRecord)) {
      const lowered = key.toLowerCase();
      if (
        lowered.includes("authorization")
        || lowered.includes("token")
        || lowered.includes("secret")
        || lowered.includes("password")
      ) {
        out[key] = "[REDACTED]";
      } else {
        out[key] = redact(nested);
      }
    }
    return out;
  }
  return value;
}

function toSafeBody(value: unknown): unknown {
  if (value === undefined) {
    return undefined;
  }
  try {
    return redact(JSON.parse(JSON.stringify(value)));
  } catch {
    return "[unserializable]";
  }
}

export function addApiTrafficEntry(entry: ApiTrafficEntry) {
  entries.unshift(entry);
  if (entries.length > MAX_ENTRIES) {
    entries.length = MAX_ENTRIES;
  }
  notify();
}

export function getApiTrafficEntries() {
  return entries;
}

export function subscribeApiTraffic(listener: () => void) {
  listeners.add(listener);
  return () => {
    listeners.delete(listener);
  };
}

export { toSafeBody };

