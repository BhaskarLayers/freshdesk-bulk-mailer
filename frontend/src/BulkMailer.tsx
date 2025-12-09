import { useMemo, useState } from "react";
import axios from "axios";

type ResultRow = {
  row: number;
  status: "sent" | "skipped" | "error";
  ticket_id?: number;
  reason?: string;
  error?: string | Record<string, unknown>;
};

type ApiResponse = {
  total: number;
  results: ResultRow[];
};

const exampleSubject = "Order {order_id} update for {name}";
const exampleBody =
  "Hi {name},\n\nThanks for your order {order_id} with {company}! We will reach out soon if we need anything else.\n\n- Support Team";

const apiBaseEnv = import.meta.env.VITE_API_BASE_URL;
const API_BASE =
  (apiBaseEnv?.toString().replace(/\/$/, "") ||
    "http://localhost:8000") + "/send-bulk";

const BulkMailer = () => {
  const [file, setFile] = useState<File | null>(null);
  const [emailColumn, setEmailColumn] = useState("email");
  const [subjectTemplate, setSubjectTemplate] = useState(exampleSubject);
  const [bodyTemplate, setBodyTemplate] = useState(exampleBody);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [response, setResponse] = useState<ApiResponse | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setResponse(null);

    if (!file) {
      setError("Please choose a CSV/XLSX file before sending.");
      return;
    }

    const formData = new FormData();
    formData.append("file", file);
    formData.append("subject_template", subjectTemplate);
    formData.append("body_template", bodyTemplate);
    formData.append("email_column", emailColumn);

    setSending(true);
    try {
      const res = await axios.post<ApiResponse>(API_BASE, formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      setResponse(res.data);
    } catch (err: any) {
      const message =
        err.response?.data?.detail ||
        err.message ||
        "Unexpected error while sending.";
      setError(typeof message === "string" ? message : JSON.stringify(message));
    } finally {
      setSending(false);
    }
  };

  const placeholderTip = useMemo(() => {
    if (!file) return "Placeholders use column names like {name} or {company}.";
    return "Placeholders use your sheet's column names (e.g., {email}).";
  }, [file]);

  return (
    <div className="card">
      <form onSubmit={handleSubmit} className="form">
        <label className="field">
          <span>Upload file (.csv, .xlsx, .xls)</span>
          <input
            type="file"
            accept=".csv, application/vnd.openxmlformats-officedocument.spreadsheetml.sheet, application/vnd.ms-excel"
            onChange={(e) => setFile(e.target.files?.[0] ?? null)}
          />
        </label>

        <label className="field">
          <span>Email column name</span>
          <input
            type="text"
            value={emailColumn}
            onChange={(e) => setEmailColumn(e.target.value)}
            placeholder="email"
          />
        </label>

        <label className="field">
          <span>Subject template</span>
          <input
            type="text"
            value={subjectTemplate}
            onChange={(e) => setSubjectTemplate(e.target.value)}
            placeholder={exampleSubject}
          />
        </label>

        <label className="field">
          <span>Body template</span>
          <textarea
            value={bodyTemplate}
            onChange={(e) => setBodyTemplate(e.target.value)}
            rows={6}
            placeholder={exampleBody}
          />
        </label>

        <div className="hint">{placeholderTip}</div>

        <button type="submit" disabled={sending}>
          {sending ? "Sending..." : "Start sending"}
        </button>
      </form>

      {error && <div className="error">Error: {error}</div>}

      {response && (
        <div className="results">
          <h2>Results</h2>
          <p>
            Total rows processed: <strong>{response.total}</strong>
          </p>
          <div className="table-wrapper">
            <table>
              <thead>
                <tr>
                  <th>Row</th>
                  <th>Status</th>
                  <th>Ticket ID</th>
                  <th>Error / Reason</th>
                </tr>
              </thead>
              <tbody>
                {response.results.map((r) => (
                  <tr key={r.row}>
                    <td>{r.row}</td>
                    <td className={`status-${r.status}`}>{r.status}</td>
                    <td>{r.ticket_id ?? "-"}</td>
                    <td>{r.error ?? r.reason ?? "-"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
};

export default BulkMailer;

