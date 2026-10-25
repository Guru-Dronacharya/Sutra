import React from "react";
import { Shield, UserCheck, AlertTriangle, LogOut } from "lucide-react";
import { useAuth, DEMO_CREDENTIALS } from "../context/AuthContext";
import { UserRole } from "../types";

export const Navbar: React.FC = () => {
  const { user, logout, quickSwitchRole } = useAuth();

  return (
    <header className="sticky top-0 z-40 bg-slate-900 border-b border-slate-800">
      {/* Top Legal Disclaimer Ribbon */}
      <div className="bg-amber-950/70 border-b border-amber-800/40 text-amber-300 px-4 py-1.5 text-xs flex items-center justify-center font-medium gap-2">
        <AlertTriangle className="w-3.5 h-3.5 flex-shrink-0" />
        <span>Decision-support information only; not legal advice.</span>
      </div>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        {/* Brand */}
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-lg bg-gradient-to-tr from-amber-600 to-orange-500 flex items-center justify-center shadow-lg shadow-orange-500/20 text-white font-bold">
            <Shield className="w-5 h-5 text-white" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="font-bold text-xl tracking-tight text-white">SUTRA</span>
              <span className="px-1.5 py-0.5 rounded text-[10px] font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                AI GOVERNANCE
              </span>
            </div>
            <p className="text-[10px] text-slate-400 font-medium">India & EU Compliance Intelligence Platform</p>
          </div>
        </div>

        {/* Right Section: Role Switcher & User Profile */}
        <div className="flex items-center gap-4">
          {/* Quick Role Switcher (For Pair Programming / Demo) */}
          <div className="hidden lg:flex items-center gap-1.5 bg-slate-800/80 p-1 rounded-lg border border-slate-700/60 text-xs">
            <span className="text-slate-400 px-2 font-medium">Switch Role:</span>
            {(["admin", "compliance_officer", "engineer", "auditor"] as UserRole[]).map((r) => (
              <button
                key={r}
                onClick={() => quickSwitchRole(r)}
                className={`px-2.5 py-1 rounded text-xs font-medium transition-all ${
                  user?.role === r
                    ? "bg-indigo-600 text-white shadow"
                    : "text-slate-300 hover:text-white hover:bg-slate-700/50"
                }`}
              >
                {r === "admin"
                  ? "Admin"
                  : r === "compliance_officer"
                  ? "Compliance"
                  : r === "engineer"
                  ? "Engineer"
                  : "Auditor"}
              </button>
            ))}
          </div>

          {/* User Profile */}
          {user && (
            <div className="flex items-center gap-3 pl-3 border-l border-slate-800">
              <div className="text-right hidden sm:block">
                <p className="text-xs font-semibold text-slate-200">{user.email}</p>
                <span className="inline-block text-[10px] font-medium px-1.5 py-0.5 rounded bg-slate-800 text-slate-400 border border-slate-700">
                  {user.role.replace("_", " ").toUpperCase()}
                </span>
              </div>
              <button
                onClick={logout}
                title="Logout"
                className="p-2 text-slate-400 hover:text-rose-400 hover:bg-slate-800 rounded-lg transition-colors"
              >
                <LogOut className="w-4 h-4" />
              </button>
            </div>
          )}
        </div>
      </div>
    </header>
  );
};
