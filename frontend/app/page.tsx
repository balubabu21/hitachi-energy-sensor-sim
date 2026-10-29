"use client";

import { useEffect, useMemo, useState } from "react";
import { api } from "@/lib/api";
import type { Product, ProductSummary } from "@/lib/types";
import { FieldsTable } from "@/components/FieldsTable";
import { CodePanel, JsonPanel } from "@/components/DataPanels";

function readHash(): { product?: string; sensor?: string } {
  if (typeof window === "undefined") return {};
  const [product, sensor] = window.location.hash.replace(/^#\/?/, "").split("/");
  return { product: product || undefined, sensor: sensor || undefined };
}

function formatInterval(s: number) {
  if (s < 60) return `${s} s`;
  if (s < 3600) return `${s / 60} min`;
  return `${s / 3600} h`;
}

export default function Home() {
  const [products, setProducts] = useState<ProductSummary[]>([]);
  const [productId, setProductId] = useState<string>();
  const [sensorId, setSensorId] = useState<string>();
  const [product, setProduct] = useState<Product>();
  const [query, setQuery] = useState("");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .products()
      .then((list) => {
        setProducts(list);
        const h = readHash();
        setProductId(list.some((p) => p.id === h.product) ? h.product : list[0]?.id);
        setSensorId(h.sensor);
      })
      .catch((e: Error) => setError(e.message));
  }, []);

  useEffect(() => {
    if (!productId) return;
    api
      .product(productId)
      .then((p) => {
        setProduct(p);
        setSensorId((s) => (p.sensors.some((x) => x.id === s) ? s : p.sensors[0]?.id));
      })
      .catch((e: Error) => setError(e.message));
  }, [productId]);

  useEffect(() => {
    if (productId && sensorId) window.history.replaceState(null, "", `#/${productId}/${sensorId}`);
  }, [productId, sensorId]);

  const grouped = useMemo(() => {
    const q = query.toLowerCase();
    const map = new Map<string, ProductSummary[]>();
    products
      .filter((p) => !q || `${p.name} ${p.group} ${p.sensors.map((s) => s.name).join(" ")}`.toLowerCase().includes(q))
      .forEach((p) => map.set(p.group, [...(map.get(p.group) ?? []), p]));
    return [...map.entries()];
  }, [products, query]);

  const sensor = product?.sensors.find((s) => s.id === sensorId);
  const totalSensors = products.reduce((n, p) => n + p.sensor_count, 0);

  return (
    <div className="shell">
      <header className="topbar">
        <div>
          <h1>Grid Sensor Simulator</h1>
          <p className="muted small">
            {products.length} Hitachi Energy product families · {totalSensors} simulated sensors · unofficial, for
            development &amp; testing only
          </p>
        </div>
      </header>

      <aside className="sidebar">
        <input className="search" placeholder="Search products or sensors…" value={query}
          onChange={(e) => setQuery(e.target.value)} />
        <nav>
          {grouped.map(([group, items]) => (
            <div key={group} className="group">
              <div className="group-title">{group}</div>
              {items.map((p) => (
                <button key={p.id} className={p.id === productId ? "nav-item on" : "nav-item"}
                  onClick={() => { setProductId(p.id); setSensorId(undefined); }}>
                  <span>{p.name}</span>
                  <span className="badge">{p.sensor_count}</span>
                </button>
              ))}
            </div>
          ))}
        </nav>
      </aside>

      <main className="main">
        {error && <p className="error">Could not reach the API: {error}</p>}
        {product && (
          <>
            <section className="product-head">
              <div className="eyebrow">{product.group}</div>
              <h2>{product.name}</h2>
              <p>{product.description}</p>
              <div className="chips">
                {product.examples.map((x) => <span key={x} className="chip">{x}</span>)}
              </div>
              <a className="link" href={product.url} target="_blank" rel="noreferrer">
                Source: hitachienergy.com ↗
              </a>
            </section>

            <h3 className="section-title">Sensors ({product.sensors.length})</h3>
            <div className="sensor-grid">
              {product.sensors.map((s) => (
                <button key={s.id} className={s.id === sensorId ? "sensor-card on" : "sensor-card"}
                  onClick={() => setSensorId(s.id)}>
                  <strong>{s.name}</strong>
                  <span className="small">{s.description}</span>
                  <span className="meta">
                    {s.fields.length} fields · every {formatInterval(s.sample_interval_s)} · {s.protocol}
                  </span>
                </button>
              ))}
            </div>

            {sensor && (
              <>
                <section className="sensor-detail">
                  <h3>{sensor.name}</h3>
                  <dl className="facts">
                    <div><dt>Principle</dt><dd>{sensor.principle}</dd></div>
                    <div><dt>Protocol</dt><dd>{sensor.protocol}</dd></div>
                    <div><dt>Sample interval</dt><dd>{formatInterval(sensor.sample_interval_s)}</dd></div>
                  </dl>
                  <FieldsTable fields={sensor.fields} envelope={product.envelope_fields} />
                </section>
                <div className="split">
                  <JsonPanel productId={product.id} sensorId={sensor.id} />
                  <CodePanel productId={product.id} sensorId={sensor.id} />
                </div>
              </>
            )}
          </>
        )}
      </main>
    </div>
  );
}
