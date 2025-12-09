import BulkMailer from "./BulkMailer";
import "./App.css";

function App() {
  return (
    <div className="app-shell">
      <h1>Bulk Freshdesk Mailer</h1>
      <p className="subtitle">
        Upload a CSV or Excel file, map the email column, and send personalised
        tickets via Freshdesk.
      </p>
      <BulkMailer />
    </div>
  );
}

export default App;

