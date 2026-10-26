import React, { useState } from "react";
import { Shield, ArrowRight, Lock, Mail, AlertTriangle } from "lucide-react";
import { useAuth, DEMO_CREDENTIALS } from "../context/AuthContext";
import { UserRole } from "../types";

export const Login: React.FC = () => {
  const { user, login } = useAuth();
  const [email, setEmail] = useState("compliance@sutra.ai");
  const [password, setPassword] = useState("compliance123");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      await login(email, password);
    } catch (err: any) {
      setError(err.message || "Failed to authenticate");
    } finally {
      setLoading(false);
    }
  };

  const handleQuickFill = (role: UserRole) => {
    const creds = DEMO_CREDENTIALS[role];
    setEmail(creds.email);
    setPassword(creds.pass);
  };
  if (user) return <Navigate to="/models" replace />;
  return (
    <div className="min-h-screen bg-slate-950 flex flex-col justify-center py-12 sm:px-6 lg:px-8">
      {/* Disclaimer Banner */}
      <div className="max-w-md mx-auto w-full mb-6 px-4">
        <div className="bg-amber-950/60 border border-amber-800/40 rounded-lg p-3 text-amber-300 text-xs flex items-center gap-2">
          <AlertTriangle className="w-4 h-4 flex-shrink-0" />
          <span>Decision-support information only; not legal advice.</span>
        </div>
      </div>

      <div className="sm:mx-auto sm:w-full sm:max-w-md">
        <div className="flex justify-center">
          <div className="w-12 h-12 rounded-xl bg-gradient-to-tr from-amber-600 to-orange-500 flex items-center justify-center shadow-lg shadow-orange-500/20 text-white font-bold">
            <Shield className="w-7 h-7 text-white" />
          </div>
        </div>
        <h2 className="mt-4 text-center text-2xl font-bold tracking-tight text-white">
          Sutra AI Governance Platform
        </h2>
        <p className="mt-1 text-center text-xs text-slate-400">
          Unified Compliance Intelligence for LLM Deployments in India
        </p>
      </div>

      <div className="mt-8 sm:mx-auto sm:w-full sm:max-w-md px-4">
        <div className="bg-slate-900 py-8 px-6 shadow-xl rounded-xl border border-slate-800 sm:px-10">
          {error && (
            <div className="mb-4 p-3 rounded-lg bg-rose-950/50 border border-rose-800/50 text-rose-300 text-xs">
              {error}
            </div>
          )}

          <form className="space-y-4" onSubmit={handleSubmit}>
            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1">Email address</label>
              <div className="relative">
                <Mail className="w-4 h-4 text-slate-500 absolute left-3 top-3" />
                <input
                  type="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="w-full bg-slate-800/80 border border-slate-700/80 rounded-lg pl-9 pr-3 py-2 text-sm text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                  placeholder="user@sutra.ai"
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1">Password</label>
              <div className="relative">
                <Lock className="w-4 h-4 text-slate-500 absolute left-3 top-3" />
                <input
                  type="password"
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="w-full bg-slate-800/80 border border-slate-700/80 rounded-lg pl-9 pr-3 py-2 text-sm text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                  placeholder="••••••••"
                />
              </div>
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full mt-2 flex items-center justify-center gap-2 py-2.5 px-4 rounded-lg text-sm font-semibold text-white bg-indigo-600 hover:bg-indigo-500 transition-colors shadow-lg shadow-indigo-600/30 disabled:opacity-50"
            >
              <span>{loading ? "Authenticating..." : "Sign in to Console"}</span>
              <ArrowRight className="w-4 h-4" />
            </button>
          </form>

          {/* Demo User One-Click Selectors */}
          <div className="mt-6 pt-6 border-t border-slate-800">
            <p className="text-[11px] font-semibold text-slate-400 mb-2 uppercase tracking-wider">
              Quick Pre-Fill Demo Roles:
            </p>
            <div className="grid grid-cols-2 gap-2">
              {(["admin", "compliance_officer", "engineer", "auditor"] as UserRole[]).map((r) => {
                const creds = DEMO_CREDENTIALS[r];
                return (
                  <button
                    key={r}
                    type="button"
                    onClick={() => handleQuickFill(r)}
                    className="p-2 text-left rounded-lg bg-slate-800/60 hover:bg-slate-800 border border-slate-700/60 text-xs transition-colors"
                  >
                    <p className="font-semibold text-slate-200 capitalize">{r.replace("_", " ")}</p>
                    <p className="text-[10px] text-slate-400 truncate">{creds.email}</p>
                  </button>
                );
              })}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
