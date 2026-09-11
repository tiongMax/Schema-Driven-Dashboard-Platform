export type FieldType = "string" | "number" | "boolean";
export type Aggregation = "sum" | "avg" | "count" | "min" | "max";

export interface FieldDefinition {
  name: string;
  type: FieldType;
  required: boolean;
  aggregation: Aggregation | null;
}

export interface SchemaDefinition {
  name: string;
  fields: FieldDefinition[];
}

export type DashboardView =
  | { type: "summary"; field: string; aggregation: Aggregation }
  | { type: "table"; columns: string[] };

export interface DashboardDefinition {
  name: string;
  schema: string;
  views: DashboardView[];
}

export interface DashboardResult {
  success: boolean;
  dashboard: string;
  views: Array<
    | { type: "summary"; field: string; aggregation: Aggregation; value: number | null }
    | { type: "table"; columns: string[]; rows: Record<string, unknown>[] }
  >;
}
