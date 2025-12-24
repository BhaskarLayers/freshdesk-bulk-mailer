import { useMemo, useState, useEffect } from "react";
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

type TicketField = {
  name: string;
  label: string;
  choices?: string[] | Record<string, unknown>;
  required_for_agents?: boolean;
  type?: string;
};

const exampleSubject = "Your Subject Here";
const exampleBody =
  "Hi {name},\n\nYour email content here.\n\n- Support Team";

const apiBaseEnv = import.meta.env.VITE_API_BASE_URL;
const API_BASE =
  (apiBaseEnv?.toString().replace(/\/$/, "") ||
    "http://localhost:8000") + "/send-bulk";

const BulkMailer = () => {
  const [file, setFile] = useState<File | null>(null);
  const [emailColumn, setEmailColumn] = useState("email");
  const [subjectTemplate, setSubjectTemplate] = useState(exampleSubject);
  const [bodyTemplate, setBodyTemplate] = useState(exampleBody);
  
  // Specific hardcoded disposition field
  const [dispositions, setDispositions] = useState<string[]>([]);
  const [selectedDisposition, setSelectedDisposition] = useState("");
  
  // Dynamic mandatory fields
  const [dynamicFields, setDynamicFields] = useState<TicketField[]>([]);
  const [dynamicValues, setDynamicValues] = useState<Record<string, string>>({});

  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [response, setResponse] = useState<ApiResponse | null>(null);

  useEffect(() => {
    const fetchFields = async () => {
      try {
        const baseUrl = API_BASE.replace("/send-bulk", "");
        const res = await axios.get<TicketField[]>(`${baseUrl}/ticket-fields`);
        const allFields = res.data;

        // 1. Handle hardcoded disposition
        const dispositionField = allFields.find(
          (f) => f.name === "cf_choose_your_inquiry"
        );
        if (dispositionField && dispositionField.choices) {
          const choices = Array.isArray(dispositionField.choices)
            ? dispositionField.choices
            : Object.keys(dispositionField.choices);
          setDispositions(choices as string[]);
          if (choices.length > 0) {
            setSelectedDisposition((choices as string[])[0]);
          }
        }

        // 2. Handle other mandatory fields
        // Exclude standard fields that we handle separately or have defaults
        const ignoredFields = [
          'subject', 
          'description', 
          'email', 
          'requester', 
          'status', 
          'priority', 
          'source', 
          'group_id', 
          'agent_id', 
          'type', 
          'company',
          'company_id',
          'cf_choose_your_inquiry' // Already handled
        ];

        const required = allFields.filter(f => 
          f.required_for_agents && 
          !ignoredFields.includes(f.name)
        );
        
        setDynamicFields(required);

        // Initialize values for new dynamic fields
        const initialValues: Record<string, string> = {};
        required.forEach(f => {
             // If it has choices, maybe pick the first one? Or let user choose.
             // We'll leave it empty to force selection/input unless we want defaults.
        });
        setDynamicValues(prev => ({...initialValues, ...prev}));

      } catch (err) {
        console.error("Failed to fetch ticket fields", err);
      }
    };
    fetchFields();
  }, []);

  const handleDynamicChange = (name: string, value: string) => {
    setDynamicValues(prev => ({
      ...prev,
      [name]: value
    }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setResponse(null);

    if (!file) {
      setError("Please choose a CSV/XLSX file before sending.");
      return;
    }

    if (dispositions.length > 0 && !selectedDisposition) {
      setError("Please select a disposition.");
      return;
    }

    // Validate dynamic fields
    for (const field of dynamicFields) {
      if (!dynamicValues[field.name]) {
        setError(`Please fill in the mandatory field: ${field.label}`);
        return;
      }
    }

    const formData = new FormData();
    formData.append("file", file);
    formData.append("subject_template", subjectTemplate);
    formData.append("body_template", bodyTemplate);
    formData.append("email_column", emailColumn);
    formData.append("disposition", selectedDisposition);
    
    // Add dynamic fields as JSON
    formData.append("custom_fields_json", JSON.stringify(dynamicValues));

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
    if (!file) return "Placeholders use column names like {name}.";
    return "Placeholders use your sheet's column names (e.g., {email}).";
  }, [file]);

  return (
    <div>
      <form onSubmit={handleSubmit}>
        <div className="form-group">
          <label>Upload File</label>
          <div className="file-upload">
            <input
              type="file"
              accept=".csv, application/vnd.openxmlformats-officedocument.spreadsheetml.sheet, application/vnd.ms-excel"
              onChange={(e) => setFile(e.target.files?.[0] ?? null)}
            />
            <div className="upload-icon">📂</div>
            <div className="upload-text">
              {file ? file.name : "Click to upload or drag and drop"}
            </div>
            <div className="upload-subtext">
              {file ? "File selected" : "CSV, XLS, XLSX up to 10MB"}
            </div>
          </div>
        </div>

        <div className="form-group">
          <label>Email Column Name</label>
          <input
            type="text"
            value={emailColumn}
            onChange={(e) => setEmailColumn(e.target.value)}
            placeholder="email"
          />
        </div>

        <div className="form-group">
          <label>Subject Template</label>
          <input
            type="text"
            value={subjectTemplate}
            onChange={(e) => setSubjectTemplate(e.target.value)}
            placeholder={exampleSubject}
          />
        </div>

        <div className="form-group">
          <label>Body Template</label>
          <textarea
            value={bodyTemplate}
            onChange={(e) => setBodyTemplate(e.target.value)}
            rows={6}
            placeholder={exampleBody}
          />
          <div style={{ marginTop: '8px', fontSize: '13px', color: '#666' }}>
            ℹ️ {placeholderTip}
          </div>
        </div>

        <div className="form-group">
          <label>Ticket Disposition</label>
          {dispositions.length === 0 ? (
            <select disabled>
              <option>Not required</option>
            </select>
          ) : (
            <select
              value={selectedDisposition}
              onChange={(e) => setSelectedDisposition(e.target.value)}
            >
              {dispositions.map((d) => (
                <option key={d} value={d}>
                  {d}
                </option>
              ))}
            </select>
          )}
        </div>

        {/* Dynamic Mandatory Fields */}
        {dynamicFields.map((field) => (
          <div key={field.name} className="form-group">
            <label>
              {field.label} {field.required_for_agents && <span style={{color: 'red'}}>*</span>}
            </label>
            {field.choices ? (
              <select
                value={dynamicValues[field.name] || ""}
                onChange={(e) => handleDynamicChange(field.name, e.target.value)}
              >
                 <option value="" disabled>Select {field.label}</option>
                 {Array.isArray(field.choices) 
                   ? field.choices.map((c: string) => <option key={c} value={c}>{c}</option>)
                   : Object.keys(field.choices).map((c) => <option key={c} value={c}>{c}</option>)
                 }
              </select>
            ) : (
              <input
                type={field.type === 'number' ? 'number' : 'text'}
                value={dynamicValues[field.name] || ""}
                onChange={(e) => handleDynamicChange(field.name, e.target.value)}
                placeholder={`Enter ${field.label}`}
              />
            )}
          </div>
        ))}

        <button type="submit" className="button" disabled={sending}>
          {sending ? "Sending..." : "Start Sending"}
        </button>
      </form>

      {error && (
        <div style={{ marginTop: '20px', padding: '15px', background: '#fee2e2', color: '#991b1b', borderRadius: '12px', fontSize: '14px' }}>
          <strong>Error:</strong> {error}
        </div>
      )}

      {response && (
        <div style={{ marginTop: '30px' }}>
          <h2 style={{ fontSize: '18px', fontWeight: 'bold', marginBottom: '15px', color: '#1a1a1a' }}>
            Results (Total: {response.total})
          </h2>
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '14px' }}>
              <thead>
                <tr style={{ background: '#f8f9fa', borderBottom: '2px solid #e9ecef' }}>
                  <th style={{ padding: '12px', textAlign: 'left', color: '#495057' }}>Row</th>
                  <th style={{ padding: '12px', textAlign: 'left', color: '#495057' }}>Status</th>
                  <th style={{ padding: '12px', textAlign: 'left', color: '#495057' }}>Ticket ID</th>
                  <th style={{ padding: '12px', textAlign: 'left', color: '#495057' }}>Details</th>
                </tr>
              </thead>
              <tbody>
                {response.results.map((r) => (
                  <tr key={r.row} style={{ borderBottom: '1px solid #f1f3f5' }}>
                    <td style={{ padding: '12px', color: '#212529' }}>{r.row}</td>
                    <td style={{ padding: '12px' }}>
                      <span className={`status-badge status-${r.status}`}>
                        {r.status}
                      </span>
                    </td>
                    <td style={{ padding: '12px', color: '#212529' }}>{r.ticket_id ?? "-"}</td>
                    <td style={{ padding: '12px', color: '#666' }}>
                      {typeof r.error === "object"
                        ? JSON.stringify(r.error)
                        : r.error ?? r.reason ?? "-"}
                    </td>
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
