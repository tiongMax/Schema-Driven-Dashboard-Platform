import { FormEvent, useMemo, useState } from "react";
import {
  ArrowLeft,
  BarChart3,
  Braces,
  Check,
  ChevronRight,
  CircleAlert,
  Database,
  Eye,
  Layers3,
  LoaderCircle,
  Plus,
  Rows3,
  Send,
  Trash2,
} from "lucide-react";
import { api } from "./api";
import type {
  Aggregation,
  DashboardDefinition,
  DashboardResult,
  DashboardView,
  FieldDefinition,
  FieldType,
  SchemaDefinition,
} from "./types";

type Step = "schema" | "data" | "configure" | "view";
type Notice = { kind: "success" | "error"; message: string } | null;

const steps: Array<{ id: Step; label: string; hint: string; icon: typeof Braces }> = [
  { id: "schema", label: "Schema", hint: "Define fields", icon: Braces },
  { id: "data", label: "Data", hint: "Submit rows", icon: Database },
  { id: "configure", label: "Dashboard", hint: "Choose views", icon: Layers3 },
  { id: "view", label: "Results", hint: "View output", icon: Eye },
];

const emptyField = (): FieldDefinition => ({ name: "", type: "string", required: false, aggregation: null });

const starterFields: FieldDefinition[] = [
  { name: "orderId", type: "string", required: true, aggregation: null },
  { name: "amount", type: "number", required: true, aggregation: "sum" },
  { name: "region", type: "string", required: false, aggregation: null },
  { name: "completed", type: "boolean", required: false, aggregation: null },
];

const sampleRows = `[
  { "orderId": "ORD-101", "amount": 1240, "region": "North", "completed": true },
  { "orderId": "ORD-102", "amount": 860, "region": "South", "completed": false },
  { "orderId": "ORD-103", "amount": 1520, "region": "North", "completed": true }
]`;

function defaultViewsForSchema(schema: SchemaDefinition): DashboardView[] {
  const summaryField = schema.fields.find((field) => field.type === "number") ?? schema.fields[0];
  return [
    {
      type: "summary",
      field: summaryField.name,
      aggregation: summaryField.type === "number" ? (summaryField.aggregation ?? "sum") : "count",
    },
    { type: "table", columns: schema.fields.slice(0, 3).map((field) => field.name) },
  ];
}

function viewsForSchema(views: DashboardView[], schema?: SchemaDefinition): DashboardView[] {
  if (!schema) return views;

  const validFields = new Set(schema.fields.map((field) => field.name));
  const fallbackField = schema.fields.find((field) => field.type === "number") ?? schema.fields[0];
  return views.map((view) => {
    if (view.type === "table") {
      return { ...view, columns: view.columns.filter((column) => validFields.has(column)) };
    }

    const field = validFields.has(view.field) ? view.field : fallbackField.name;
    const fieldType = schema.fields.find((candidate) => candidate.name === field)?.type;
    return { ...view, field, aggregation: fieldType === "number" ? view.aggregation : "count" };
  });
}

function App() {
  const [step, setStep] = useState<Step>("schema");
  const [schemas, setSchemas] = useState<SchemaDefinition[]>([]);
  const [dashboards, setDashboards] = useState<string[]>([]);
  const [schemaName, setSchemaName] = useState("orders");
  const [fields, setFields] = useState<FieldDefinition[]>(starterFields);
  const [dataSchema, setDataSchema] = useState("orders");
  const [rowsText, setRowsText] = useState(sampleRows);
  const [dashboardName, setDashboardName] = useState("orders-overview");
  const [dashboardSchema, setDashboardSchema] = useState("orders");
  const [views, setViews] = useState<DashboardView[]>([
    { type: "summary", field: "amount", aggregation: "sum" },
    { type: "table", columns: ["orderId", "amount", "region"] },
  ]);
  const [resultName, setResultName] = useState("orders-overview");
  const [result, setResult] = useState<DashboardResult | null>(null);
  const [notice, setNotice] = useState<Notice>(null);
  const [loading, setLoading] = useState(false);

  const currentSchema = useMemo(
    () => schemas.find((schema) => schema.name === dashboardSchema),
    [schemas, dashboardSchema],
  );

  const run = async (action: () => Promise<void>) => {
    setLoading(true);
    setNotice(null);
    try {
      await action();
    } catch (error) {
      setNotice({ kind: "error", message: error instanceof Error ? error.message : "Something went wrong." });
    } finally {
      setLoading(false);
    }
  };

  const registerSchema = (event: FormEvent) => {
    event.preventDefault();
    void run(async () => {
      const response = await api<{ schema: SchemaDefinition }>("/schema", {
        method: "POST",
        body: JSON.stringify({ name: schemaName.trim(), fields }),
      });
      setSchemas((items) => [...items.filter((item) => item.name !== response.schema.name), response.schema]);
      setDataSchema(response.schema.name);
      setDashboardSchema(response.schema.name);
      setViews(defaultViewsForSchema(response.schema));
      setNotice({ kind: "success", message: `Schema “${response.schema.name}” is ready.` });
      setStep("data");
    });
  };

  const submitData = (event: FormEvent) => {
    event.preventDefault();
    void run(async () => {
      let rows: unknown;
      try {
        rows = JSON.parse(rowsText);
      } catch {
        throw new Error("Rows must be valid JSON.");
      }
      if (!Array.isArray(rows)) throw new Error("Enter rows as a JSON array.");
      const response = await api<{ rows_ingested: number; duplicates_skipped?: number }>("/ingest", {
        method: "POST",
        body: JSON.stringify({ schema: dataSchema.trim(), rows }),
      });
      setDashboardSchema(dataSchema.trim());
      const skipped = response.duplicates_skipped ?? 0;
      const message = response.rows_ingested > 0
        ? `${response.rows_ingested} row${response.rows_ingested === 1 ? "" : "s"} added${skipped ? `; ${skipped} duplicate${skipped === 1 ? "" : "s"} skipped` : ""}.`
        : `No rows added; ${skipped} duplicate${skipped === 1 ? " was" : "s were"} already stored.`;
      setNotice({ kind: "success", message });
      setStep("configure");
    });
  };

  const registerDashboard = (event: FormEvent) => {
    event.preventDefault();
    void run(async () => {
      const submittedViews = viewsForSchema(views, currentSchema);
      const emptyTable = submittedViews.find((view) => view.type === "table" && view.columns.length === 0);
      if (emptyTable) throw new Error("Select at least one column for every table view.");
      setViews(submittedViews);
      const response = await api<{ dashboard: DashboardDefinition }>("/dashboard", {
        method: "POST",
        body: JSON.stringify({ name: dashboardName.trim(), schema: dashboardSchema.trim(), views: submittedViews }),
      });
      setDashboards((items) => [...new Set([...items, response.dashboard.name])]);
      setResultName(response.dashboard.name);
      setNotice({ kind: "success", message: `Dashboard “${response.dashboard.name}” is ready.` });
      setStep("view");
    });
  };

  const loadDashboard = (event?: FormEvent) => {
    event?.preventDefault();
    void run(async () => {
      const response = await api<DashboardResult>(`/dashboard/${encodeURIComponent(resultName.trim())}`);
      setResult(response);
      setNotice({ kind: "success", message: "Dashboard refreshed with the latest data." });
    });
  };

  const updateField = (index: number, patch: Partial<FieldDefinition>) => {
    setFields((items) => items.map((field, i) => (i === index ? { ...field, ...patch } : field)));
  };

  const chooseSchema = (name: string, target: "data" | "dashboard") => {
    if (target === "data") setDataSchema(name);
    else {
      setDashboardSchema(name);
      const schema = schemas.find((item) => item.name === name);
      if (schema && schema.fields.length) {
        setViews(defaultViewsForSchema(schema));
      }
    }
  };

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <span className="brand-mark"><BarChart3 size={20} /></span>
          <div><strong>Schema Studio</strong><span>Dashboard builder</span></div>
        </div>

        <nav aria-label="Dashboard creation steps">
          {steps.map((item, index) => {
            const Icon = item.icon;
            const active = step === item.id;
            return (
              <button className={`nav-item ${active ? "active" : ""}`} key={item.id} onClick={() => { setStep(item.id); setNotice(null); }}>
                <span className="step-number">{index + 1}</span>
                <Icon size={18} />
                <span><strong>{item.label}</strong><small>{item.hint}</small></span>
                <ChevronRight className="nav-arrow" size={16} />
              </button>
            );
          })}
        </nav>

        <div className="sidebar-note">
          <Database size={17} />
          <div><strong>API connection</strong><span>localhost:8000</span></div>
        </div>
      </aside>

      <main>
        <header className="topbar">
          <div>
            <p className="eyebrow">Schema-driven workspace</p>
            <h1>{steps.find((item) => item.id === step)?.label}</h1>
          </div>
          <span className="stage-pill">Step {steps.findIndex((item) => item.id === step) + 1} of 4</span>
        </header>

        {notice && (
          <div className={`notice ${notice.kind}`} role="status">
            {notice.kind === "success" ? <Check size={18} /> : <CircleAlert size={18} />}
            <span>{notice.message}</span>
          </div>
        )}

        {step === "schema" && (
          <form className="panel" onSubmit={registerSchema}>
            <PanelIntro number="01" title="Register a schema" text="Describe the shape of each row before you send any data." />
            <label className="field-label">Schema name<input value={schemaName} onChange={(event) => setSchemaName(event.target.value)} required placeholder="orders" /></label>
            <div className="section-heading"><div><h2>Fields</h2><p>Add the columns your data should accept.</p></div><button className="button ghost" type="button" onClick={() => setFields((items) => [...items, emptyField()])}><Plus size={16} /> Add field</button></div>
            <div className="field-list">
              {fields.map((field, index) => (
                <div className="field-row" key={index}>
                  <span className="row-index">{String(index + 1).padStart(2, "0")}</span>
                  <label><span>Name</span><input value={field.name} onChange={(event) => updateField(index, { name: event.target.value })} required placeholder="fieldName" /></label>
                  <label><span>Type</span><select value={field.type} onChange={(event) => updateField(index, { type: event.target.value as FieldType, aggregation: null })}><option value="string">String</option><option value="number">Number</option><option value="boolean">Boolean</option></select></label>
                  <label><span>Aggregation</span><select value={field.aggregation ?? ""} onChange={(event) => updateField(index, { aggregation: (event.target.value || null) as Aggregation | null })}><option value="">None</option><option value="count">Count</option>{field.type === "number" && <><option value="sum">Sum</option><option value="avg">Average</option><option value="min">Minimum</option><option value="max">Maximum</option></>}</select></label>
                  <label className="checkbox-label"><input type="checkbox" checked={field.required} onChange={(event) => updateField(index, { required: event.target.checked })} /><span>Required</span></label>
                  <button className="icon-button" type="button" aria-label={`Remove ${field.name || "field"}`} disabled={fields.length === 1} onClick={() => setFields((items) => items.filter((_, i) => i !== index))}><Trash2 size={17} /></button>
                </div>
              ))}
            </div>
            <FormFooter loading={loading} label="Register schema" />
          </form>
        )}

        {step === "data" && (
          <form className="panel" onSubmit={submitData}>
            <PanelIntro number="02" title="Submit data" text="Paste a JSON array. Every row is checked against the selected schema." />
            <SchemaInput label="Target schema" value={dataSchema} schemas={schemas} onChange={(name) => chooseSchema(name, "data")} />
            <label className="field-label code-field">Rows (JSON)<textarea value={rowsText} onChange={(event) => setRowsText(event.target.value)} spellCheck={false} rows={12} /></label>
            <div className="helper"><Rows3 size={17} /><span>The full batch is rejected if one row is invalid. Exact duplicate rows are skipped.</span></div>
            <FormFooter loading={loading} label="Submit rows" />
          </form>
        )}

        {step === "configure" && (
          <form className="panel" onSubmit={registerDashboard}>
            <PanelIntro number="03" title="Configure a dashboard" text="Combine quick summaries with a focused table view." />
            <div className="two-column">
              <label className="field-label">Dashboard name<input value={dashboardName} onChange={(event) => setDashboardName(event.target.value)} required /></label>
              <SchemaInput label="Schema" value={dashboardSchema} schemas={schemas} onChange={(name) => chooseSchema(name, "dashboard")} />
            </div>
            <div className="section-heading"><div><h2>Views</h2><p>Results appear in this order.</p></div><div className="button-group"><button type="button" className="button ghost" onClick={() => setViews((items) => [...items, { type: "summary", field: currentSchema?.fields[0]?.name ?? "", aggregation: "count" }])}><Plus size={16} /> Summary</button><button type="button" className="button ghost" onClick={() => setViews((items) => [...items, { type: "table", columns: currentSchema?.fields.slice(0, 3).map((field) => field.name) ?? [] }])}><Plus size={16} /> Table</button></div></div>
            <div className="view-list">
              {views.map((view, index) => (
                <div className="view-card" key={index}>
                  <div className="view-type"><span>{index + 1}</span><div><strong>{view.type === "summary" ? "Summary" : "Table"}</strong><small>{view.type === "summary" ? "One calculated value" : "Selected row columns"}</small></div></div>
                  {view.type === "summary" ? (
                    <><label><span>Field</span><FieldSelect value={view.field} schema={currentSchema} onChange={(field) => setViews((items) => items.map((item, i) => i === index && item.type === "summary" ? { ...item, field, aggregation: currentSchema?.fields.find((candidate) => candidate.name === field)?.type === "number" || !currentSchema ? item.aggregation : "count" } : item))} /></label><label><span>Calculation</span><select value={view.aggregation} onChange={(event) => setViews((items) => items.map((item, i) => i === index && item.type === "summary" ? { ...item, aggregation: event.target.value as Aggregation } : item))}><option value="count">Count</option>{(!currentSchema || currentSchema.fields.find((field) => field.name === view.field)?.type === "number") && <><option value="sum">Sum</option><option value="avg">Average</option><option value="min">Minimum</option><option value="max">Maximum</option></>}</select></label></>
                  ) : (
                    <label className="column-picker"><span>Columns</span><div>{(currentSchema?.fields ?? []).map((field) => <label className="check-chip" key={field.name}><input type="checkbox" checked={view.columns.includes(field.name)} onChange={(event) => setViews((items) => items.map((item, i) => i === index && item.type === "table" ? { ...item, columns: event.target.checked ? [...item.columns, field.name] : item.columns.filter((name) => name !== field.name) } : item))} /><span>{field.name}</span></label>)}{!currentSchema && <input value={view.columns.join(", ")} onChange={(event) => setViews((items) => items.map((item, i) => i === index && item.type === "table" ? { ...item, columns: event.target.value.split(",").map((value) => value.trim()).filter(Boolean) } : item))} placeholder="orderId, amount, region" />}</div></label>
                  )}
                  <button type="button" className="icon-button" aria-label="Remove view" disabled={views.length === 1} onClick={() => setViews((items) => items.filter((_, i) => i !== index))}><Trash2 size={17} /></button>
                </div>
              ))}
            </div>
            <FormFooter
              loading={loading}
              label="Save dashboard"
              onBack={() => {
                setNotice(null);
                setStep("data");
              }}
            />
          </form>
        )}

        {step === "view" && (
          <section className="results-page">
            <div className="panel result-controls">
              <PanelIntro number="04" title="Generated dashboard" text="Load the latest values computed from your stored rows." />
              <form className="result-search" onSubmit={loadDashboard}>
                <label className="field-label">Dashboard name
                  <input list="dashboard-options" value={resultName} onChange={(event) => setResultName(event.target.value)} required />
                  <datalist id="dashboard-options">{dashboards.map((name) => <option key={name} value={name} />)}</datalist>
                </label>
                <button className="button primary" disabled={loading}>{loading ? <LoaderCircle className="spin" size={18} /> : <Eye size={18} />} Load dashboard</button>
              </form>
            </div>
            {result ? <DashboardOutput result={result} /> : <div className="empty-state"><span><BarChart3 size={28} /></span><h2>Your dashboard will appear here</h2><p>Enter a registered dashboard name, then load its latest data.</p></div>}
          </section>
        )}
      </main>
    </div>
  );
}

function PanelIntro({ number, title, text }: { number: string; title: string; text: string }) {
  return <div className="panel-intro"><span>{number}</span><div><h2>{title}</h2><p>{text}</p></div></div>;
}

function FormFooter({ loading, label, onBack }: { loading: boolean; label: string; onBack?: () => void }) {
  return <div className="form-footer">
    <span>Fields marked required must be present in every row.</span>
    <div className="form-actions">
      {onBack && <button className="button ghost" type="button" onClick={onBack}><ArrowLeft size={17} /> Back</button>}
      <button className="button primary" disabled={loading}>{loading ? <LoaderCircle className="spin" size={18} /> : <Send size={17} />}{label}</button>
    </div>
  </div>;
}

function SchemaInput({ label, value, schemas, onChange }: { label: string; value: string; schemas: SchemaDefinition[]; onChange: (value: string) => void }) {
  return <label className="field-label">{label}<input list={`${label.replace(" ", "-")}-schemas`} value={value} onChange={(event) => onChange(event.target.value)} required /><datalist id={`${label.replace(" ", "-")}-schemas`}>{schemas.map((schema) => <option key={schema.name} value={schema.name} />)}</datalist></label>;
}

function FieldSelect({ value, schema, onChange }: { value: string; schema?: SchemaDefinition; onChange: (value: string) => void }) {
  if (!schema) return <input value={value} onChange={(event) => onChange(event.target.value)} required placeholder="amount" />;
  return <select value={value} onChange={(event) => onChange(event.target.value)}>{schema.fields.map((field) => <option key={field.name} value={field.name}>{field.name}</option>)}</select>;
}

function DashboardOutput({ result }: { result: DashboardResult }) {
  return <div className="dashboard-output">
    <div className="dashboard-title"><div><p className="eyebrow">Live result</p><h2>{result.dashboard}</h2></div><span className="live-badge"><span /> Up to date</span></div>
    <div className="summary-grid">
      {result.views.filter((view) => view.type === "summary").map((view, index) => view.type === "summary" && <article className="summary-card" key={index}><span>{view.aggregation}</span><strong>{view.value === null ? "—" : typeof view.value === "number" ? view.value.toLocaleString() : String(view.value)}</strong><p>{view.field}</p></article>)}
    </div>
    {result.views.map((view, index) => view.type === "table" && <div className="table-card" key={index}><div className="table-heading"><div><h3>Data table</h3><p>{view.rows.length} row{view.rows.length === 1 ? "" : "s"}</p></div></div><div className="table-scroll"><table><thead><tr>{view.columns.map((column) => <th key={column}>{column}</th>)}</tr></thead><tbody>{view.rows.length ? view.rows.map((row, rowIndex) => <tr key={rowIndex}>{view.columns.map((column) => <td key={column}>{row[column] === null || row[column] === undefined ? <span className="muted">—</span> : typeof row[column] === "boolean" ? <span className={`boolean ${row[column] ? "yes" : "no"}`}>{row[column] ? "True" : "False"}</span> : String(row[column])}</td>)}</tr>) : <tr><td className="no-rows" colSpan={view.columns.length}>No data has been submitted yet.</td></tr>}</tbody></table></div></div>)}
  </div>;
}

export default App;
