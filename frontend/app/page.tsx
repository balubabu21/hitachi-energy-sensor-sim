"use client";

import { useEffect, useMemo, useState } from "react";
import { api } from "@/lib/api";
import type { BrowserSensor, FieldSpec, Product, ProductSummary } from "@/lib/types";
import { FieldsTable } from "@/components/FieldsTable";
import { CodePanel, JsonPanel } from "@/components/DataPanels";
import { CreateSensorForm } from "@/components/CreateSensorForm";
import { SensorRequestForm } from "@/components/SensorRequestForm";

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

function schemaStorageKey(productId: string, sensorId: string) {
  return `grid-sensor-sim:schema:v1:${productId}:${sensorId}`;
}

function localSensorsStorageKey(productId: string) {
  return `grid-sensor-sim:local-sensors:v1:${productId}`;
}

function isFieldSpecArray(value: unknown): value is FieldSpec[] {
  if (!Array.isArray(value) || value.length < 1 || value.length > 100) return false;
  const jsonTypes: Record<string, string> = {
    float: "number",
    integer: "integer",
    counter: "integer (monotonic)",
    boolean: "boolean",
    enum: "string (enum)",
    float_array: "object<label, number>",
  };
  const names = new Set<string>();

  return value.every((item) => {
    if (typeof item !== "object" || item === null) return false;
    const field = item as Record<string, unknown>;
    if (typeof field.name !== "string" || !/^[A-Za-z_][A-Za-z0-9_]{0,63}$/.test(field.name) ||
        names.has(field.name) || ["timestamp", "asset_id", "sensor_id", "sequence", "quality"].includes(field.name) ||
        typeof field.dtype !== "string" || !Object.hasOwn(jsonTypes, field.dtype) ||
        field.json_type !== jsonTypes[field.dtype] || typeof field.description !== "string" ||
        !field.description.trim() || field.description.length > 500 ||
        typeof field.precision !== "number" || !Number.isInteger(field.precision) ||
        field.precision < 0 || field.precision > 12 ||
        (field.unit !== undefined && (typeof field.unit !== "string" || field.unit.length > 32))) {
      return false;
    }

    names.add(field.name);
    const numericType = ["float", "integer", "counter", "float_array"].includes(field.dtype);
    if (numericType) {
      if (typeof field.min !== "number" || !Number.isFinite(field.min) ||
          typeof field.max !== "number" || !Number.isFinite(field.max) ||
          typeof field.nominal !== "number" || !Number.isFinite(field.nominal) ||
          field.min > field.max || field.nominal < field.min || field.nominal > field.max) {
        return false;
      }
      if ((field.dtype === "integer" || field.dtype === "counter") &&
          ![field.min, field.max, field.nominal].every(Number.isInteger)) return false;
    }
    if (field.dtype === "counter" &&
        (typeof field.step !== "number" || !Number.isInteger(field.step) || field.step < 1)) return false;
    if (field.dtype === "boolean" &&
        (typeof field.p_true !== "number" || !Number.isFinite(field.p_true) || field.p_true < 0 || field.p_true > 1)) {
      return false;
    }
    if (field.dtype === "enum") {
      if (typeof field.options !== "object" || field.options === null || Array.isArray(field.options)) return false;
      const options = Object.entries(field.options as Record<string, unknown>);
      if (options.length < 1 || options.length > 100 ||
          options.some(([name, weight]) => !name || name.length > 64 ||
            typeof weight !== "number" || !Number.isFinite(weight) || weight < 0) ||
          options.every(([, weight]) => weight === 0)) return false;
    }
    if (field.dtype === "float_array") {
      if (!Array.isArray(field.labels) || field.labels.length < 1 || field.labels.length > 100 ||
          !field.labels.every((label) => typeof label === "string" && label.trim() && label.length <= 64) ||
          new Set(field.labels).size !== field.labels.length) return false;
    }
    return true;
  });
}

function isBrowserSensorArray(value: unknown): value is BrowserSensor[] {
  if (!Array.isArray(value) || value.length > 100) return false;
  const ids = new Set<string>();
  return value.every((item) => {
    if (typeof item !== "object" || item === null) return false;
    const sensor = item as Record<string, unknown>;
    if (typeof sensor.id !== "string" || !/^local-[A-Za-z0-9_-]{1,58}$/.test(sensor.id) ||
        ids.has(sensor.id) || typeof sensor.name !== "string" || !sensor.name.trim() ||
        sensor.name.length > 120 || typeof sensor.description !== "string" ||
        !sensor.description.trim() || sensor.description.length > 1000 ||
        typeof sensor.principle !== "string" || !sensor.principle.trim() || sensor.principle.length > 500 ||
        typeof sensor.protocol !== "string" || !sensor.protocol.trim() || sensor.protocol.length > 120 ||
        typeof sensor.sample_interval_s !== "number" || !Number.isInteger(sensor.sample_interval_s) ||
        sensor.sample_interval_s < 1 || sensor.sample_interval_s > 86400 ||
        !isFieldSpecArray(sensor.fields) || !isFieldSpecArray(sensor.defaultFields)) {
      return false;
    }
    ids.add(sensor.id);
    return true;
  });
}

export default function Home() {
  const [products, setProducts] = useState<ProductSummary[]>([]);
  const [productId, setProductId] = useState<string>();
  const [sensorId, setSensorId] = useState<string>();
  const [product, setProduct] = useState<Product>();
  const [query, setQuery] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [schemaError, setSchemaError] = useState<string | null>(null);
  const [schemas, setSchemas] = useState<Record<string, { fields: FieldSpec[]; customized: boolean }>>({});
  const [localSensorsByProduct, setLocalSensorsByProduct] = useState<Record<string, BrowserSensor[]>>({});
  const [loadedLocalSensors, setLoadedLocalSensors] = useState<Record<string, boolean>>({});
  const [showCreateSensor, setShowCreateSensor] = useState(false);
  const [showRequestForm, setShowRequestForm] = useState(false);

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
        setSensorId((s) => s ?? p.sensors[0]?.id);
      })
      .catch((e: Error) => setError(e.message));
  }, [productId]);

  useEffect(() => {
    if (!productId) return;
    try {
      const saved = localStorage.getItem(localSensorsStorageKey(productId));
      if (saved === null) {
        setLocalSensorsByProduct((current) => ({ ...current, [productId]: [] }));
      } else {
        const parsed: unknown = JSON.parse(saved);
        if (!isBrowserSensorArray(parsed)) {
          throw new Error("Saved browser-only sensors are invalid.");
        }
        setLocalSensorsByProduct((current) => ({ ...current, [productId]: parsed }));
      }
      setSchemaError(null);
    } catch (e) {
      setLocalSensorsByProduct((current) => ({ ...current, [productId]: [] }));
      setSchemaError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoadedLocalSensors((current) => ({ ...current, [productId]: true }));
    }
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

  const localSensors = productId ? localSensorsByProduct[productId] ?? [] : [];
  const sensors = [...(product?.sensors ?? []), ...localSensors];
  const sensor = sensors.find((s) => s.id === sensorId);
  const localSensor = localSensors.find((s) => s.id === sensorId);
  const activeSchemaKey = productId && sensorId ? `${productId}:${sensorId}` : undefined;
  const activeSchema = activeSchemaKey ? schemas[activeSchemaKey] : undefined;
  const fields = localSensor?.fields ?? activeSchema?.fields ?? sensor?.fields ?? [];
  const customized = localSensor
    ? JSON.stringify(localSensor.fields) !== JSON.stringify(localSensor.defaultFields)
    : activeSchema?.customized ?? false;
  const totalSensors = products.reduce((n, p) => n + p.sensor_count, 0);

  useEffect(() => {
    if (!product || !productId || !loadedLocalSensors[productId] || !sensorId) return;
    if (sensors.some((item) => item.id === sensorId)) return;
    setSensorId(sensors[0]?.id);
  }, [loadedLocalSensors, product, productId, sensorId, sensors]);

  useEffect(() => {
    if (!sensor || localSensor || !activeSchemaKey || !productId || !sensorId) return;
    try {
      const saved = localStorage.getItem(schemaStorageKey(productId, sensorId));
      if (saved === null) {
        setSchemas((current) => ({
          ...current,
          [activeSchemaKey]: { fields: sensor.fields, customized: false },
        }));
        setSchemaError(null);
        return;
      }

      const parsed: unknown = JSON.parse(saved);
      if (!isFieldSpecArray(parsed)) {
        throw new Error("Saved sensor fields are invalid.");
      }
      setSchemas((current) => ({
        ...current,
        [activeSchemaKey]: { fields: parsed, customized: true },
      }));
      setSchemaError(null);
    } catch (e) {
      setSchemas((current) => ({
        ...current,
        [activeSchemaKey]: { fields: sensor.fields, customized: true },
      }));
      setSchemaError(e instanceof Error ? e.message : String(e));
    }
  }, [activeSchemaKey, localSensor, productId, sensor, sensorId]);

  function saveLocalSensors(nextSensors: BrowserSensor[]) {
    if (!productId) return false;
    try {
      localStorage.setItem(localSensorsStorageKey(productId), JSON.stringify(nextSensors));
      setLocalSensorsByProduct((current) => ({ ...current, [productId]: nextSensors }));
      setSchemaError(null);
      return true;
    } catch (e) {
      setSchemaError(e instanceof Error ? e.message : String(e));
      return false;
    }
  }

  function saveFields(nextFields: FieldSpec[]) {
    if (!productId || !sensorId || !activeSchemaKey) return;
    if (localSensor) {
      saveLocalSensors(localSensors.map((item) => item.id === sensorId ? { ...item, fields: nextFields } : item));
      return;
    }
    try {
      localStorage.setItem(schemaStorageKey(productId, sensorId), JSON.stringify(nextFields));
      setSchemas((current) => ({
        ...current,
        [activeSchemaKey]: { fields: nextFields, customized: true },
      }));
      setSchemaError(null);
    } catch (e) {
      setSchemaError(e instanceof Error ? e.message : String(e));
    }
  }

  function resetFields() {
    if (!productId || !sensorId || !sensor || !activeSchemaKey) return;
    if (localSensor) {
      saveFields(localSensor.defaultFields);
      return;
    }
    try {
      localStorage.removeItem(schemaStorageKey(productId, sensorId));
      setSchemas((current) => ({
        ...current,
        [activeSchemaKey]: { fields: sensor.fields, customized: false },
      }));
      setSchemaError(null);
    } catch (e) {
      setSchemaError(e instanceof Error ? e.message : String(e));
    }
  }

  function createLocalSensor(id: string, definition: Omit<BrowserSensor, "id">) {
    const nextSensors = [...localSensors, { id, ...definition }];
    if (!saveLocalSensors(nextSensors)) return;
    setSensorId(id);
    setShowCreateSensor(false);
  }

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

            <div className="section-heading">
              <h3 className="section-title">Sensors ({sensors.length})</h3>
              <button className="btn primary" onClick={() => setShowCreateSensor((shown) => !shown)}>
                {showCreateSensor ? "Cancel" : "Create sensor"}
              </button>
            </div>
            {showCreateSensor && (
              <CreateSensorForm
                existingSensors={localSensors}
                onCreate={createLocalSensor}
                onCancel={() => setShowCreateSensor(false)}
              />
            )}
            <div className="sensor-grid">
              {sensors.map((s) => (
                <button key={s.id} className={s.id === sensorId ? "sensor-card on" : "sensor-card"}
                  onClick={() => setSensorId(s.id)}>
                  <strong>{s.name}</strong>
                  <span className="small">{s.description}</span>
                  <span className="meta">
                    {(s.id === sensorId ? fields.length : s.fields.length)} fields · every {formatInterval(s.sample_interval_s)} · {s.protocol}
                    {"defaultFields" in s && " · browser-only"}
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
                  {localSensor && (
                    <div className="browser-sensor-actions">
                      <span className="badge">Browser-only</span>
                      <button className="btn ghost" onClick={() => setShowRequestForm((shown) => !shown)}>
                        {showRequestForm ? "Hide request form" : "Request permanent addition"}
                      </button>
                    </div>
                  )}
                  {localSensor && showRequestForm && (
                    <SensorRequestForm productId={product.id} productName={product.name} sensor={localSensor} />
                  )}
                  {schemaError && <p className="error" role="alert">Could not load or save this sensor schema: {schemaError}</p>}
                  <FieldsTable
                    fields={fields}
                    envelope={product.envelope_fields}
                    customized={Boolean(customized)}
                    onUpdateField={(field) => saveFields(fields.map((current) => current.name === field.name ? field : current))}
                    onRemoveField={(field) => {
                      if (fields.length > 1) saveFields(fields.filter((current) => current.name !== field.name));
                    }}
                    onAddField={(field) => saveFields([...fields, field])}
                    onReset={resetFields}
                  />
                </section>
                <div className="split">
                  <JsonPanel
                    productId={product.id}
                    sensorId={sensor.id}
                    fields={fields}
                    localOnly={Boolean(localSensor)}
                    sampleIntervalS={sensor.sample_interval_s}
                    protocol={sensor.protocol}
                  />
                  <CodePanel
                    productId={product.id}
                    sensorId={sensor.id}
                    fields={fields}
                    localOnly={Boolean(localSensor)}
                  />
                </div>
              </>
            )}
          </>
        )}
      </main>
    </div>
  );
}
