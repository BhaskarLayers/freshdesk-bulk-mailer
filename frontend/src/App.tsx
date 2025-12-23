import BulkMailer from "./BulkMailer";
import "./App.css";

function App() {
  return (
    <div className="app-background">
      <div className="container">
        <div className="header">
          <h1>Email Automation Platform</h1>
          <p className="subtitle">
            Upload a CSV or Excel file to automate your Freshdesk tickets
          </p>
        </div>
        <BulkMailer />
      </div>
    </div>
  );
}

export default App;
