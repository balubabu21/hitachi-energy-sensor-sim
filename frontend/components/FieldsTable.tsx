"use client";

import { useEffect, useState, type FormEvent } from "react";
import type { DataType, EnvelopeField, FieldSpec } from "@/lib/types";

const JSON_TYPES: Record<DataType, string> = {
  float: "number",
  integer: "integer",
  counter: "integer (monotonic)",
  boolean: "boolean",
  enum: "string (enum)",
  float_array: "object<label, number>",
};

const ENVELOPE_NAMES = new Set(["timestamp", "asset_id", "sensor_id", "sequence", "quality"]);
const NUMERIC_TYPES = new Set<DataType>(["float", "integer", "counter", "float_array"]);

function range(f: FieldSpec): string {
  switch (f.dtype) {
    case "boolean":
      return `true | false  (P(true) ≈ ${f.p_true})`;
    case "enum":
      return Object.keys(f.options ?? {}).join(" | ");
    case "counter":
      return `${f.min?.toLocaleString()} → ${f.max?.toLocaleString()} (+0…${f.step}/sample)`;
    default:
      return `${f.min} … ${f.max}`;
  }
}

interface FieldDraft {
  name: string;
  dtype: DataType;
  description: string;
  unit: string;
  min: string;
  max: string;
  nominal: string;
  precision: string;
  options: string;
  pTrue: string;
  labels: string;
  step: string;
}

const EMPTY_DRAFT: FieldDraft = {
  name: "",
  dtype: "float",
  description: "",
  unit: "",
  min: "0",
  max: "100",
  nominal: "50",
  precision: "2",
  options: "NORMAL=0.8, ALARM=0.2",
  pTrue: "0.05",
  labels: "L1, L2, L3",
  step: "1",
};

function numberValue(value: string): number | undefined {
  if (!value.trim()) return undefined;
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : undefined;
}

function parseEnumOptions(value: string): Record<string, number> | undefined {
  const options: Record<string, number> = {};
  for (const entry of value.split(",")) {
    const [rawName, rawWeight, ...extra] = entry.split("=").map((part) => part.trim());
    const weight = numberValue(rawWeight ?? "");
    if (!rawName || weight === undefined || weight < 0 || extra.length || rawName in options) return undefined;
    options[rawName] = weight;
  }
  if (!Object.keys(options).length || Object.values(options).every((weight) => weight === 0)) return undefined;
  return options;
}

export function FieldsTable({
  fields,
  envelope,
  customized,
  onUpdateField,
  onRemoveField,
  onAddField,
  onReset,
}: {
  fields: FieldSpec[];
  envelope: EnvelopeField[];
  customized: boolean;
  onUpdateField: (field: FieldSpec) => void;
  onRemoveField: (field: FieldSpec) => void;
  onAddField: (field: FieldSpec) => void;
  onReset: () => void;
}) {
  const [rangeDrafts, setRangeDrafts] = useState<Record<string, { min: string; max: string }>>({});
  const [enumDrafts, setEnumDrafts] = useState<Record<string, string>>({});
  const [rangeError, setRangeError] = useState<string | null>(null);
  const [showAddForm, setShowAddForm] = useState(false);
  const [draft, setDraft] = useState<FieldDraft>(EMPTY_DRAFT);
  const [formError, setFormError] = useState<string | null>(null);

  useEffect(() => {
    setRangeDrafts(Object.fromEntries(
      fields.filter((field) => NUMERIC_TYPES.has(field.dtype)).map((field) => [
        field.name,
        { min: String(field.min ?? ""), max: String(field.max ?? "") },
      ]),
    ));
    setEnumDrafts(Object.fromEntries(
      fields.filter((field) => field.dtype === "enum").map((field) => [
        field.name,
        Object.entries(field.options ?? {}).map(([name, weight]) => `${name}=${weight}`).join(", "),
      ]),
    ));
  }, [fields]);

  function applyRange(field: FieldSpec) {
    const values = rangeDrafts[field.name];
    const min = numberValue(values?.min ?? "");
    const max = numberValue(values?.max ?? "");
    if (min === undefined || max === undefined) {
      setRangeError(`${field.name}: enter finite minimum and maximum values.`);
      return;
    }
    if (min > max) {
      setRangeError(`${field.name}: minimum must not exceed maximum.`);
      return;
    }
    if ((field.dtype === "integer" || field.dtype === "counter") &&
        (!Number.isInteger(min) || !Number.isInteger(max))) {
      setRangeError(`${field.name}: integer and counter bounds must be whole numbers.`);
      return;
    }

    const nominal = Math.min(max, Math.max(min, field.nominal ?? min));
    onUpdateField({ ...field, min, max, nominal });
    setRangeError(null);
  }

  function applyEnumOptions(field: FieldSpec) {
    const options = parseEnumOptions(enumDrafts[field.name] ?? "");
    if (!options) {
      setRangeError(`${field.name}: enter unique NAME=weight pairs with a positive total weight.`);
      return;
    }
    onUpdateField({ ...field, options });
    setRangeError(null);
  }

  function addField(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setFormError(null);

    if (fields.length >= 100) {
      setFormError("A sensor can contain at most 100 fields.");
      return;
    }

    const name = draft.name.trim();
    if (!/^[A-Za-z_][A-Za-z0-9_]{0,63}$/.test(name)) {
      setFormError("Use a field name starting with a letter or underscore, followed by letters, numbers, or underscores.");
      return;
    }
    if (ENVELOPE_NAMES.has(name)) {
      setFormError("That name is reserved for a reading envelope field.");
      return;
    }
    if (fields.some((field) => field.name === name)) {
      setFormError("A field with that name already exists on this sensor.");
      return;
    }
    const description = draft.description.trim();
    if (!description) {
      setFormError("Enter a description for the new field.");
      return;
    }
    const precision = numberValue(draft.precision);
    if (precision === undefined || !Number.isInteger(precision) || precision < 0 || precision > 12) {
      setFormError("Precision must be a whole number from 0 to 12.");
      return;
    }

    const common = {
      name,
      dtype: draft.dtype,
      json_type: JSON_TYPES[draft.dtype],
      description,
      unit: draft.unit.trim() || undefined,
      precision,
    };
    let field: FieldSpec;

    if (NUMERIC_TYPES.has(draft.dtype)) {
      const min = numberValue(draft.min);
      const max = numberValue(draft.max);
      const nominal = numberValue(draft.nominal);
      if (min === undefined || max === undefined || nominal === undefined || min > max ||
          nominal < min || nominal > max) {
        setFormError("Enter finite bounds and a nominal value within the selected range.");
        return;
      }
      if ((draft.dtype === "integer" || draft.dtype === "counter") &&
          (![min, max, nominal].every(Number.isInteger))) {
        setFormError("Integer and counter values must be whole numbers.");
        return;
      }

      if (draft.dtype === "counter") {
        const step = numberValue(draft.step);
        if (step === undefined || !Number.isInteger(step) || step < 1) {
          setFormError("Counter step must be a positive whole number.");
          return;
        }
        field = { ...common, min, max, nominal, step };
      } else if (draft.dtype === "float_array") {
        const labels = draft.labels.split(",").map((label) => label.trim()).filter(Boolean);
        if (!labels.length || new Set(labels).size !== labels.length) {
          setFormError("Enter one or more unique labels separated by commas.");
          return;
        }
        field = { ...common, min, max, nominal, labels };
      } else {
        field = { ...common, min, max, nominal };
      }
    } else if (draft.dtype === "boolean") {
      const p_true = numberValue(draft.pTrue);
      if (p_true === undefined || p_true < 0 || p_true > 1) {
        setFormError("Probability of true must be between 0 and 1.");
        return;
      }
      field = { ...common, p_true };
    } else {
      const options = parseEnumOptions(draft.options);
      if (!options) {
        setFormError("Enter unique enum NAME=weight pairs with a positive total weight.");
        return;
      }
      field = { ...common, options };
    }

    onAddField(field);
    setDraft(EMPTY_DRAFT);
    setShowAddForm(false);
  }

  function updateDraft<K extends keyof FieldDraft>(key: K, value: FieldDraft[K]) {
    setDraft((current) => ({ ...current, [key]: value }));
  }

  return (
    <>
      <div className="schema-toolbar">
        <p className="hint">Changes are saved in this browser and applied to generated data and code.</p>
        <div className="actions">
          <button className="btn ghost" onClick={() => setShowAddForm((shown) => !shown)}>
            {showAddForm ? "Cancel" : "Add custom field"}
          </button>
          <button className="btn ghost" onClick={onReset} disabled={!customized}>Reset schema</button>
        </div>
      </div>
      {rangeError && <p className="error" role="alert">{rangeError}</p>}
      <div className="table-wrap">
        <table className="fields">
          <thead>
            <tr>
              <th>Field</th>
              <th>JSON type</th>
              <th>Unit</th>
              <th>Range / values</th>
              <th>Nominal</th>
              <th>Description</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {fields.map((f) => (
              <tr key={f.name}>
                <td className="mono">
                  {f.name}
                  {f.labels && <span className="muted"> [{f.labels.join(", ")}]</span>}
                </td>
                <td><span className={`type t-${f.dtype}`}>{f.json_type}</span></td>
                <td>{f.unit ?? "—"}</td>
                <td className="mono small">
                  {NUMERIC_TYPES.has(f.dtype) ? (
                    <div className="range-editor">
                      <label>
                        Min
                        <input
                          aria-label={`${f.name} minimum`}
                          type="number"
                          step={f.dtype === "integer" || f.dtype === "counter" ? 1 : "any"}
                          value={rangeDrafts[f.name]?.min ?? String(f.min ?? "")}
                          onChange={(event) => setRangeDrafts((current) => ({
                            ...current,
                            [f.name]: { ...current[f.name], min: event.target.value, max: current[f.name]?.max ?? String(f.max ?? "") },
                          }))}
                        />
                      </label>
                      <label>
                        Max
                        <input
                          aria-label={`${f.name} maximum`}
                          type="number"
                          step={f.dtype === "integer" || f.dtype === "counter" ? 1 : "any"}
                          value={rangeDrafts[f.name]?.max ?? String(f.max ?? "")}
                          onChange={(event) => setRangeDrafts((current) => ({
                            ...current,
                            [f.name]: { ...current[f.name], min: current[f.name]?.min ?? String(f.min ?? ""), max: event.target.value },
                          }))}
                        />
                      </label>
                      <button className="btn ghost" onClick={() => applyRange(f)}>Apply</button>
                    </div>
                  ) : f.dtype === "enum" ? (
                    <div className="range-editor">
                      <label>
                        Options
                        <input
                          aria-label={`${f.name} allowed values`}
                          value={enumDrafts[f.name] ?? ""}
                          onChange={(event) => setEnumDrafts((current) => ({ ...current, [f.name]: event.target.value }))}
                        />
                      </label>
                      <button className="btn ghost" onClick={() => applyEnumOptions(f)}>Apply</button>
                    </div>
                  ) : range(f)}
                </td>
                <td className="mono">{f.nominal ?? "—"}</td>
                <td className="small">{f.description}</td>
                <td>
                  <button
                    className="btn ghost"
                    onClick={() => onRemoveField(f)}
                    disabled={fields.length <= 1}
                    aria-label={`Remove ${f.name}`}
                  >
                    Remove
                  </button>
                </td>
              </tr>
            ))}
            <tr className="sep"><td colSpan={7}>Envelope fields (on every reading)</td></tr>
            {envelope.map((e) => (
              <tr key={e.name} className="envelope">
                <td className="mono">{e.name}</td>
                <td><span className="type">{e.json_type}</span></td>
                <td>—</td>
                <td>—</td>
                <td>—</td>
                <td className="small">{e.description}</td>
                <td>—</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {showAddForm && (
        <form className="field-editor-form" onSubmit={addField}>
          <h4>Add custom field</h4>
          <div className="field-editor-grid">
            <label>
              Name
              <input value={draft.name} onChange={(event) => updateDraft("name", event.target.value)} />
            </label>
            <label>
              Type
              <select value={draft.dtype} onChange={(event) => updateDraft("dtype", event.target.value as DataType)}>
                <option value="float">Float</option>
                <option value="integer">Integer</option>
                <option value="counter">Counter</option>
                <option value="float_array">Float array</option>
                <option value="boolean">Boolean</option>
                <option value="enum">Enum</option>
              </select>
            </label>
            <label>
              Unit (optional)
              <input value={draft.unit} onChange={(event) => updateDraft("unit", event.target.value)} />
            </label>
            <label className="wide">
              Description
              <input value={draft.description} onChange={(event) => updateDraft("description", event.target.value)} />
            </label>
            {NUMERIC_TYPES.has(draft.dtype) && (
              <>
                <label>
                  Minimum
                  <input type="number" step={draft.dtype === "integer" || draft.dtype === "counter" ? 1 : "any"}
                    value={draft.min} onChange={(event) => updateDraft("min", event.target.value)} />
                </label>
                <label>
                  Maximum
                  <input type="number" step={draft.dtype === "integer" || draft.dtype === "counter" ? 1 : "any"}
                    value={draft.max} onChange={(event) => updateDraft("max", event.target.value)} />
                </label>
                <label>
                  Nominal
                  <input type="number" step={draft.dtype === "integer" || draft.dtype === "counter" ? 1 : "any"}
                    value={draft.nominal} onChange={(event) => updateDraft("nominal", event.target.value)} />
                </label>
                <label>
                  Precision
                  <input type="number" min={0} max={12} step={1} value={draft.precision}
                    onChange={(event) => updateDraft("precision", event.target.value)} />
                </label>
              </>
            )}
            {draft.dtype === "counter" && (
              <label>
                Maximum increment per sample
                <input type="number" min={1} step={1} value={draft.step}
                  onChange={(event) => updateDraft("step", event.target.value)} />
              </label>
            )}
            {draft.dtype === "float_array" && (
              <label className="wide">
                Labels (comma-separated)
                <input value={draft.labels} onChange={(event) => updateDraft("labels", event.target.value)} />
              </label>
            )}
            {draft.dtype === "boolean" && (
              <label>
                Probability of true (0–1)
                <input type="number" min={0} max={1} step="any" value={draft.pTrue}
                  onChange={(event) => updateDraft("pTrue", event.target.value)} />
              </label>
            )}
            {draft.dtype === "enum" && (
              <label className="wide">
                Options (comma-separated NAME=weight pairs)
                <input value={draft.options} onChange={(event) => updateDraft("options", event.target.value)} />
              </label>
            )}
          </div>
          {formError && <p className="error" role="alert">{formError}</p>}
          <button className="btn primary" type="submit">Add field</button>
        </form>
      )}
    </>
  );
}
