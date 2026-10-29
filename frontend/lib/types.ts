export type DataType = "float" | "integer" | "counter" | "boolean" | "enum" | "float_array";

export interface FieldSpec {
  name: string;
  dtype: DataType;
  json_type: string;
  description: string;
  unit?: string;
  min?: number;
  max?: number;
  nominal?: number;
  precision: number;
  options?: Record<string, number>;
  p_true?: number;
  labels?: string[];
  step?: number;
}

export interface SensorSpec {
  id: string;
  name: string;
  description: string;
  principle: string;
  protocol: string;
  sample_interval_s: number;
  fields: FieldSpec[];
}

export interface EnvelopeField {
  name: string;
  json_type: string;
  description: string;
}

export interface ProductSummary {
  id: string;
  name: string;
  group: string;
  description: string;
  url: string;
  sensor_count: number;
  sensors: { id: string; name: string }[];
}

export interface Product extends Omit<ProductSummary, "sensors" | "sensor_count"> {
  examples: string[];
  sensors: SensorSpec[];
  envelope_fields: EnvelopeField[];
}

export interface MockResponse {
  product_id: string;
  sensor_id: string;
  protocol: string;
  interval_s: number;
  count: number;
  seed: number | null;
  readings: Record<string, unknown>[];
}

export interface CodeFile {
  filename: string;
  language: string;
  content: string;
}
