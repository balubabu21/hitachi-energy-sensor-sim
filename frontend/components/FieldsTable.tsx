import type { EnvelopeField, FieldSpec } from "@/lib/types";

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

export function FieldsTable({ fields, envelope }: { fields: FieldSpec[]; envelope: EnvelopeField[] }) {
  return (
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
              <td className="mono small">{range(f)}</td>
              <td className="mono">{f.nominal ?? "—"}</td>
              <td className="small">{f.description}</td>
            </tr>
          ))}
          <tr className="sep"><td colSpan={6}>Envelope fields (on every reading)</td></tr>
          {envelope.map((e) => (
            <tr key={e.name} className="envelope">
              <td className="mono">{e.name}</td>
              <td><span className="type">{e.json_type}</span></td>
              <td>—</td>
              <td>—</td>
              <td>—</td>
              <td className="small">{e.description}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
