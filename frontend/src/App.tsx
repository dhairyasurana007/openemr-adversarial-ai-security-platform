import { Link, Route, Routes, useLocation } from "react-router-dom";

import ApprovalQueue from "./pages/ApprovalQueue";
import Dashboard from "./pages/Dashboard";
import Findings from "./pages/Findings";
import Workbench from "./pages/Workbench";

const navItems = [
  { to: "/",           label: "Dashboard",  icon: "⬡" },
  { to: "/workbench",  label: "Workbench",  icon: "⚙" },
  { to: "/findings",   label: "Findings",   icon: "⚑" },
  { to: "/approvals",  label: "Approvals",  icon: "✓" },
];

export default function App() {
  const { pathname } = useLocation();

  return (
    <div className="layout">
      <aside className="sidebar">
        <div className="sidebar-logo">
          <div className="sidebar-logo-icon">⬡</div>
          <div>
            <div className="sidebar-logo-text">AgentForge</div>
            <div className="sidebar-logo-sub">AI Security Platform</div>
          </div>
        </div>
        <nav className="nav">
          {navItems.map(({ to, label, icon }) => (
            <Link
              key={to}
              to={to}
              className={`nav-link${pathname === to ? " active" : ""}`}
            >
              <span className="nav-icon">{icon}</span>
              {label}
            </Link>
          ))}
        </nav>
      </aside>
      <div className="main-content">
        <Routes>
          <Route path="/"          element={<Dashboard />} />
          <Route path="/workbench" element={<Workbench />} />
          <Route path="/findings"  element={<Findings />} />
          <Route path="/approvals" element={<ApprovalQueue />} />
        </Routes>
      </div>
    </div>
  );
}
