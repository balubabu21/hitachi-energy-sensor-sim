import type { FieldSpec, MockResponse, SensorSpec } from "./types";

const QUALITY_WEIGHTS = { GOOD: 0.96, UNCERTAIN: 0.03, BAD: 0.01 };

function createRandom(seed?: number) {
  let state = (seed ?? Math.floor(Math.random() * 2 ** 32)) >>> 0;
  return () => {
    state = (1664525 * state + 1013904223) >>> 0;
    return state / 2 ** 32;
  };
}

function weightedChoice(options: Record<string, number>, random: () => number) {
  const entries = Object.entries(options);
  const total = entries.reduce((sum, [, weight]) => sum + weight, 0);
  let target = random() * total;
  for (const [value, weight] of entries) {
    target -= weight;
    if (target < 0) return value;
  }
  return entries.at(-1)?.[0] ?? "";
}

function gaussian(random: () => number) {
  const u = Math.max(random(), Number.EPSILON);
  const v = random();
  return Math.sqrt(-2 * Math.log(u)) * Math.cos(2 * Math.PI * v);
}

function clip(value: number, min: number, max: number) {
  return Math.max(min, Math.min(max, value));
}

export function generateLocalReadings(
  productId: string,
  sensor: SensorSpec,
  count: number,
  anomalyRate: number,
  seed?: number,
): MockResponse {
  const random = createRandom(seed);
  const states: unknown[] = sensor.fields.map(() => null);
  const span = (field: FieldSpec) => (field.max ?? 1) - (field.min ?? 0);
  const walk = (field: FieldSpec, previous: number | null) => {
    const min = field.min ?? 0;
    const max = field.max ?? 1;
    const nominal = field.nominal ?? min;
    const value = previous ?? nominal + gaussian(random) * span(field) * 0.02;
    return clip(value + 0.15 * (nominal - value) + gaussian(random) * span(field) * 0.015, min, max);
  };
  const anomalousValue = (field: FieldSpec) => {
    const min = field.min ?? 0;
    const max = field.max ?? 1;
    const nominal = field.nominal ?? min;
    const target = max - nominal >= nominal - min ? max : min;
    return nominal + (target - nominal) * (0.8 + random() * 0.2);
  };
  const initials = productId.split("-").map((part) => part[0] ?? "").join("").toUpperCase();
  const assetId = `HE-${initials}-0001`;
  const start = Date.now() - sensor.sample_interval_s * 1000 * (count - 1);
  const readings: Record<string, unknown>[] = [];

  for (let sequence = 0; sequence < count; sequence += 1) {
    const isAnomaly = random() < anomalyRate;
    const anomalousField = isAnomaly ? Math.floor(random() * sensor.fields.length) : -1;
    const values: Record<string, unknown> = {};

    sensor.fields.forEach((field, index) => {
      const anomaly = index === anomalousField;
      let value: unknown;
      if (field.dtype === "float" || field.dtype === "integer") {
        const next = anomaly
          ? anomalousValue(field)
          : walk(field, typeof states[index] === "number" ? states[index] as number : null);
        states[index] = next;
        value = field.dtype === "integer" ? Math.round(next) : Number(next.toFixed(field.precision));
      } else if (field.dtype === "float_array") {
        const labels = field.labels ?? ["0"];
        const previous = Array.isArray(states[index]) ? states[index] as (number | null)[] : labels.map(() => null);
        const next = previous.map((last) => {
          const current = anomaly ? anomalousValue(field) : walk(field, last);
          return Number(current.toFixed(field.precision));
        });
        states[index] = next;
        value = Object.fromEntries(labels.map((label, labelIndex) => [label, next[labelIndex]]));
      } else if (field.dtype === "counter") {
        const previous = typeof states[index] === "number" ? states[index] : field.min ?? 0;
        const next = Math.min(field.max ?? Number.MAX_SAFE_INTEGER, previous + Math.floor(random() * ((field.step ?? 1) + 1)));
        states[index] = next;
        value = next;
      } else if (field.dtype === "boolean") {
        value = anomaly || random() < (field.p_true ?? 0.05);
      } else {
        const options = field.options ?? {};
        if (anomaly) {
          value = Object.entries(options).sort((a, b) => a[1] - b[1])[0]?.[0] ?? "";
        } else {
          if (typeof states[index] !== "string" || random() > 0.9) {
            states[index] = weightedChoice(options, random);
          }
          value = states[index];
        }
      }
      values[field.name] = value;
    });

    const timestamp = new Date(start + sensor.sample_interval_s * 1000 * sequence).toISOString();
    readings.push({
      timestamp,
      asset_id: assetId,
      sensor_id: sensor.id,
      sequence,
      quality: isAnomaly ? "UNCERTAIN" : weightedChoice(QUALITY_WEIGHTS, random),
      values,
      ...(isAnomaly ? { anomaly: { field: sensor.fields[anomalousField].name } } : {}),
    });
  }

  return {
    product_id: productId,
    sensor_id: sensor.id,
    protocol: sensor.protocol,
    interval_s: sensor.sample_interval_s,
    count,
    seed: seed ?? null,
    readings,
  };
}
