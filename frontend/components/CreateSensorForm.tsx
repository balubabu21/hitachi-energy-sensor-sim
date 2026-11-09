"use client";

import { useState, type FormEvent } from "react";
import type { BrowserSensor } from "@/lib/types";

const STARTER_FIELDS: BrowserSensor["fields"] = [{
  name: "measurement_value",
  dtype: "float",
  json_type: "number",
  description: "Synthetic measurement value",
  min: 0,
  max: 100,
  nominal: 50,
  precision: 2,
}];

export function CreateSensorForm({
  existingSensors,
  onCreate,
  onCancel,
}: {
  existingSensors: BrowserSensor[];
  onCreate: (id: string, sensor: Omit<BrowserSensor, "id">) => void;
  onCancel: () => void;
}) {
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [principle, setPrinciple] = useState("User-defined synthetic measurement");
  const [protocol, setProtocol] = useState("Browser-only");
  const [sampleInterval, setSampleInterval] = useState("60");
  const [error, setError] = useState<string | null>(null);

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const trimmedName = name.trim();
    const trimmedDescription = description.trim();
    const interval = Number(sampleInterval);
    if (existingSensors.length >= 100) {
      setError("A product can have at most 100 browser-only sensors.");
      return;
    }
    if (!trimmedName || trimmedName.length > 120 || !trimmedDescription || trimmedDescription.length > 1000) {
      setError("Enter a sensor name (up to 120 characters) and description (up to 1000 characters).");
      return;
    }
    if (!principle.trim() || principle.trim().length > 500 || !protocol.trim() || protocol.trim().length > 120) {
      setError("Enter a measurement principle (up to 500 characters) and protocol (up to 120 characters).");
      return;
    }
    if (!Number.isInteger(interval) || interval < 1 || interval > 86400) {
      setError("Sample interval must be a whole number between 1 and 86400 seconds.");
      return;
    }

    const baseId = trimmedName.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "").slice(0, 54) || "custom-sensor";
    let id = `local-${baseId}`;
    let suffix = 2;
    const usedIds = new Set(existingSensors.map((sensor) => sensor.id));
    while (usedIds.has(id)) {
      id = `local-${baseId}-${suffix}`;
      suffix += 1;
    }

    onCreate(id, {
      name: trimmedName,
      description: trimmedDescription,
      principle: principle.trim(),
      protocol: protocol.trim(),
      sample_interval_s: interval,
      fields: STARTER_FIELDS.map((field) => ({ ...field })),
      defaultFields: STARTER_FIELDS.map((field) => ({ ...field })),
    });
    setError(null);
    setName("");
    setDescription("");
  }

  return (
    <form className="field-editor-form" onSubmit={submit}>
      <h4>Create browser-only sensor</h4>
      <p className="hint">This sensor is saved only in this browser. You can edit its fields after creating it.</p>
      <div className="field-editor-grid">
        <label>
          Sensor name
          <input required maxLength={120} value={name} onChange={(event) => setName(event.target.value)} />
        </label>
        <label>
          Sample interval (seconds)
          <input required type="number" min={1} max={86400} step={1} value={sampleInterval}
            onChange={(event) => setSampleInterval(event.target.value)} />
        </label>
        <label>
          Protocol
          <input required maxLength={120} value={protocol} onChange={(event) => setProtocol(event.target.value)} />
        </label>
        <label>
          Measurement principle
          <input required maxLength={500} value={principle} onChange={(event) => setPrinciple(event.target.value)} />
        </label>
        <label className="wide">
          Description
          <input required maxLength={1000} value={description}
            onChange={(event) => setDescription(event.target.value)} />
        </label>
      </div>
      {error && <p className="error" role="alert">{error}</p>}
      <div className="actions">
        <button className="btn primary" type="submit">Create sensor</button>
        <button className="btn ghost" type="button" onClick={onCancel}>Cancel</button>
      </div>
    </form>
  );
}
