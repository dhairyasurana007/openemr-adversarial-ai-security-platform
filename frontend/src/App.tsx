import { Link, Route, Routes } from "react-router-dom";

function Placeholder({ title }: { title: string }) {
  return (
    <section>
      <h2>{title}</h2>
      <p>Commit 14 scaffold ready.</p>
    </section>
  );
}

export default function App() {
  return (
    <main style={{ margin: "0 auto", maxWidth: 960, padding: "1rem" }}>
      <h1>AgentForge</h1>
      <nav style={{ display: "flex", gap: "1rem", marginBottom: "1rem" }}>
        <Link to="/">Dashboard</Link>
        <Link to="/workbench">Workbench</Link>
        <Link to="/findings">Findings</Link>
        <Link to="/approvals">Approvals</Link>
      </nav>
      <Routes>
        <Route path="/" element={<Placeholder title="Dashboard" />} />
        <Route path="/workbench" element={<Placeholder title="Workbench" />} />
        <Route path="/findings" element={<Placeholder title="Findings" />} />
        <Route path="/approvals" element={<Placeholder title="Approval Queue" />} />
      </Routes>
    </main>
  );
}
