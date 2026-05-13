import { Link, Route, Routes } from "react-router-dom";

import ApprovalQueue from "./pages/ApprovalQueue";
import Dashboard from "./pages/Dashboard";
import Findings from "./pages/Findings";
import Workbench from "./pages/Workbench";

export default function App() {
  return (
    <main style={{ margin: "0 auto", maxWidth: 1080, padding: "1rem" }}>
      <h1>AgentForge</h1>
      <nav style={{ display: "flex", gap: "1rem", marginBottom: "1rem" }}>
        <Link to="/">Dashboard</Link>
        <Link to="/workbench">Workbench</Link>
        <Link to="/findings">Findings</Link>
        <Link to="/approvals">Approvals</Link>
      </nav>
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/workbench" element={<Workbench />} />
        <Route path="/findings" element={<Findings />} />
        <Route path="/approvals" element={<ApprovalQueue />} />
      </Routes>
    </main>
  );
}
