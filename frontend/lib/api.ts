import type { CodeFile, MockResponse, Product, ProductSummary } from "./types";

// All calls go through the Next.js route handler at /api/*, which proxies to the
// Python backend (BACKEND_URL) at runtime. The browser never talks to the backend directly.
async function get<T>(path: string): Promise<T> {
  const res = await fetch(`/api${path}`, { cache: "no-store" });
  if (!res.ok) throw new Error(`${res.status} ${res.statusText} – ${path}`);
  return res.json() as Promise<T>;
}

export const api = {
  products: () => get<ProductSummary[]>("/products"),
  product: (id: string) => get<Product>(`/products/${encodeURIComponent(id)}`),
  mock: (productId: string, sensorId: string, params: { count: number; seed?: number; anomalyRate: number }) => {
    const q = new URLSearchParams({ count: String(params.count), anomaly_rate: String(params.anomalyRate) });
    if (params.seed !== undefined) q.set("seed", String(params.seed));
    return get<MockResponse>(
      `/products/${encodeURIComponent(productId)}/sensors/${encodeURIComponent(sensorId)}/mock?${q}`,
    );
  },
  code: (productId: string, sensorId: string) =>
    get<{ files: CodeFile[] }>(
      `/products/${encodeURIComponent(productId)}/sensors/${encodeURIComponent(sensorId)}/code`,
    ),
};
