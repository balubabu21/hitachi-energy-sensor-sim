import type { CodeFile, FieldSpec, MockResponse, Product, ProductSummary, SensorSubmission } from "./types";

// All calls go through the Next.js route handler at /api/*, which proxies to the
// Python backend (BACKEND_URL) at runtime. The browser never talks to the backend directly.
async function get<T>(path: string): Promise<T> {
  const res = await fetch(`/api${path}`, { cache: "no-store" });
  if (!res.ok) throw new Error(`${res.status} ${res.statusText} – ${path}`);
  return res.json() as Promise<T>;
}

async function post<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`/api${path}`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(body),
    cache: "no-store",
  });
  if (!res.ok) {
    const errorBody = await res.text();
    throw new Error(`${res.status} ${res.statusText} – ${path}${errorBody ? `: ${errorBody}` : ""}`);
  }
  return res.json() as Promise<T>;
}

export const api = {
  products: () => get<ProductSummary[]>("/products"),
  product: (id: string) => get<Product>(`/products/${encodeURIComponent(id)}`),
  mock: (
    productId: string,
    sensorId: string,
    params: { count: number; seed?: number; anomalyRate: number },
    fields: FieldSpec[],
  ) => {
    const q = new URLSearchParams({ count: String(params.count), anomaly_rate: String(params.anomalyRate) });
    if (params.seed !== undefined) q.set("seed", String(params.seed));
    return post<MockResponse>(
      `/products/${encodeURIComponent(productId)}/sensors/${encodeURIComponent(sensorId)}/mock?${q}`,
      { fields: fields.map(({ json_type: _jsonType, ...field }) => field) },
    );
  },
  code: (productId: string, sensorId: string, fields: FieldSpec[]) =>
    post<{ files: CodeFile[] }>(
      `/products/${encodeURIComponent(productId)}/sensors/${encodeURIComponent(sensorId)}/code`,
      { fields: fields.map(({ json_type: _jsonType, ...field }) => field) },
    ),
  submitSensorRequest: (request: SensorSubmission) => post<{ status: string }>("/sensor-requests", request),
};
