import React from "react";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { AuthProvider, useAuth } from "./context/AuthContext";
import { Navbar } from "./components/Navbar";
import { Sidebar } from "./components/Sidebar";
import { Login } from "./pages/Login";
import { ModelRegistry } from "./pages/ModelRegistry";
import { RiskProfiler } from "./pages/RiskProfiler";
import { GuardrailPlayground } from "./pages/GuardrailPlayground";
import { GapAnalysisStudio } from "./pages/GapAnalysisStudio";
import { AuditExplorer } from "./pages/AuditExplorer";
import { AdminPanel } from "./pages/AdminPanel";

const ProtectedLayout: React.FC = () => {
  const { user } = useAuth();
  if (!user) {
    return <Navigate to="/login" replace />;
  }

  return (
    <div className="min-h-screen flex flex-col bg-slate-950 text-slate-100">
      <Navbar />
      <div className="flex-1 flex overflow-hidden">
        <Sidebar />
        <main className="flex-1 overflow-y-auto">
          <Routes>
            <Route path="/" element={<Navigate to="/models" replace />} />
            <Route path="/models" element={<ModelRegistry />} />
            <Route path="/risk-profiler" element={<RiskProfiler />} />
            <Route path="/guardrails" element={<GuardrailPlayground />} />
            <Route path="/gap-analysis" element={<GapAnalysisStudio />} />
            <Route path="/audit" element={<AuditExplorer />} />
            <Route
              path="/admin"
              element={user.role === "admin" ? <AdminPanel /> : <Navigate to="/models" replace />}
            />
          </Routes>
        </main>
      </div>
    </div>
  );
};

export const App: React.FC = () => {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route path="/*" element={<ProtectedLayout />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
};

export default App;
