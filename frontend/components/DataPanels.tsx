"use client";

import { useCallback, useEffect, useState } from "react";
import { api } from "@/lib/api";
import { generateLocalReadings } from "@/lib/local-generator";
import type { CodeFile, FieldSpec, MockResponse } from "@/lib/types";
import { CodeBlock, CopyButton } from "./CodeBlock";

export function JsonPanel({
  productId,
  sensorId,
  fields,
  localOnly = false,
  sampleIntervalS = 60,
  protocol = "",
}: {
  productId: string;
  sensorId: string;
  fields: FieldSpec[];
  localOnly?: boolean;
  sampleIntervalS?: number;
  protocol?: string;
}) {
  const [count, setCount] = useState(5);
  const [seed, setSeed] = useState<string>("");
  const [anomaly, setAnomaly] = useState(0);
  const [data, setData] = useState<MockResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const load = useCallback(() => {
    setLoading(true);
    setError(null);
    const params = {
        count,
        seed: seed === "" ? undefined : Number(seed),
        anomalyRate: anomaly / 100,
      };
    const request = localOnly
      ? Promise.resolve(generateLocalReadings(
        productId,
        { id: sensorId, name: sensorId, description: "", principle: "", protocol, sample_interval_s: sampleIntervalS, fields },
        count,
        params.anomalyRate,
        params.seed,
      ))
      : api.mock(productId, sensorId, params, fields);
    request
      .then(setData)
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false));
  }, [productId, sensorId, count, seed, anomaly, fields, localOnly, sampleIntervalS, protocol]);

  useEffect(() => {
    load();
    // regenerate when the sensor or schema changes; controls use the button
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [productId, sensorId, fields, localOnly]);

  const json = data ? JSON.stringify(data, null, 2) : "";

  const download = () => {
    const url = URL.createObjectURL(new Blob([json], { type: "application/json" }));
    const a = document.createElement("a");
    a.href = url;
    a.download = `${productId}__${sensorId}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <section className="panel">
      <header className="panel-head">
        <h3>Mock data (JSON)</h3>
        <div className="actions">
          <CopyButton text={json} />
          <button className="btn ghost" onClick={download} disabled={!data}>Download</button>
        </div>
      </header>
      <div className="controls">
        <label>
          Readings
          <input type="number" min={1} max={1000} value={count}
            onChange={(e) => setCount(Math.max(1, Math.min(1000, Number(e.target.value) || 1)))} />
        </label>
        <label>
          Seed
          <input type="number" placeholder="random" value={seed} onChange={(e) => setSeed(e.target.value)} />
        </label>
        <label>
          Anomalies {anomaly}%
          <input type="range" min={0} max={50} value={anomaly} onChange={(e) => setAnomaly(Number(e.target.value))} />
        </label>
        <button className="btn primary" onClick={load} disabled={loading}>
          {loading ? "Generating…" : "Generate"}
        </button>
      </div>
      {error && <p className="error">{error}</p>}
      {data && <CodeBlock code={json} language="json" />}
    </section>
  );
}

export function CodePanel({
  productId,
  sensorId,
  fields,
  localOnly = false,
}: {
  productId: string;
  sensorId: string;
  fields: FieldSpec[];
  localOnly?: boolean;
}) {
  const [files, setFiles] = useState<CodeFile[]>([]);
  const [active, setActive] = useState(0);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setActive(0);
    setError(null);
    if (localOnly) {
      setFiles([{
        filename: `${sensorId}-schema.json`,
        language: "json",
        content: JSON.stringify({ sensor_id: sensorId, fields }, null, 2),
      }]);
      return;
    }
    api
      .code(productId, sensorId, fields)
      .then((r) => setFiles(r.files))
      .catch((e: Error) => setError(e.message));
  }, [productId, sensorId, fields, localOnly]);

  const file = files[active];

  return (
    <section className="panel">
      <header className="panel-head">
        <h3>Generator code</h3>
        <div className="actions">{file && <CopyButton text={file.content} />}</div>
      </header>
      <div className="file-tabs" role="tablist">
        {files.map((f, i) => (
          <button key={f.filename} role="tab" aria-selected={i === active}
            className={i === active ? "file-tab on" : "file-tab"} onClick={() => setActive(i)}>
            {f.filename}
          </button>
        ))}
      </div>
      {error && <p className="error">{error}</p>}
      {file && (
        <>
          {localOnly ? (
            <p className="hint">Browser-only sensor definition, saved in this browser.</p>
          ) : active === 0 && (
            <p className="hint">
              Standalone script — standard library only. Run it with{" "}
              <code>python {file.filename} --count 10 --seed 42</code>
            </p>
          )}
          <CodeBlock code={file.content} language={file.language} />
        </>
      )}
    </section>
  );
}
