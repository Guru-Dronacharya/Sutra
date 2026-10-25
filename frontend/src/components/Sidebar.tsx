import React from "react";
import { NavLink } from "react-router-dom";
import {
  Boxes,
  Compass,
  ShieldAlert,
  FileCheck2,
  Database,
  Sliders,
} from "lucide-react";
import { useAuth } from "../context/AuthContext";

export const Sidebar: React.FC = () => {
  const { user } = useAuth();

  const navItems = [
    { to: "/models", label: "Model Registry", icon: Boxes },
    { to: "/risk-profiler", label: "Risk Profiler Wizard", icon: Compass },
    { to: "/guardrails", label: "Guardrail Playground", icon: ShieldAlert },
    { to: "/gap-analysis", label: "Gap Analysis Studio", icon: FileCheck2 },
    { to: "/audit", label: "Immutable Audit Ledger", icon: Database },
  ];

  // RBAC Gating: Admin Panel is visible to Admin only
  if (user?.role === "admin") {
    navItems.push({ to: "/admin", label: "Admin & Policies", icon: Sliders });
  }

  return (
    <aside className="w-64 bg-slate-900 border-r border-slate-800 flex flex-col flex-shrink-0">
      <div className="p-4 space-y-1">
        <p className="px-3 text-[11px] font-semibold text-slate-500 uppercase tracking-wider mb-2">
          Governance Modules
        </p>
        {navItems.map((item) => {
          const Icon = item.icon;
          return (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) =>
                `flex items-center gap-3 px-3 py-2.5 rounded-lg text-xs font-medium transition-all ${
                  isActive
                    ? "bg-indigo-600/20 text-indigo-400 border border-indigo-500/30"
                    : "text-slate-400 hover:text-slate-200 hover:bg-slate-800/60"
                }`
              }
            >
              <Icon className="w-4 h-4 flex-shrink-0" />
              <span>{item.label}</span>
            </NavLink>
          );
        })}
      </div>

      {/* Regulatory Badge Footer */}
      <div className="mt-auto p-4 border-t border-slate-800/80">
        <div className="p-3 rounded-lg bg-slate-800/50 border border-slate-700/40 text-[11px] text-slate-400 space-y-1">
          <p className="font-semibold text-slate-300">Statutory Alignments</p>
          <div className="flex flex-wrap gap-1 pt-1">
            <span className="px-1.5 py-0.5 rounded bg-slate-700/60 text-[9px] text-slate-300">DPDP 2023</span>
            <span className="px-1.5 py-0.5 rounded bg-slate-700/60 text-[9px] text-slate-300">IT Rules '26</span>
            <span className="px-1.5 py-0.5 rounded bg-slate-700/60 text-[9px] text-slate-300">MeitY Sutras</span>
            <span className="px-1.5 py-0.5 rounded bg-slate-700/60 text-[9px] text-slate-300">RBI FREE-AI</span>
            <span className="px-1.5 py-0.5 rounded bg-slate-700/60 text-[9px] text-slate-300">EU AI Act</span>
          </div>
        </div>
      </div>
    </aside>
  );
};
