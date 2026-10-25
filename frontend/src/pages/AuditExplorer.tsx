import React, { useEffect, useState } from "react";
import {
  Database,
  CheckCircle2,
  AlertTriangle,
  Download,
  RefreshCw,
  ShieldCheck,
  ShieldAlert,
  Search,
} from "lucide-react";
import { api } from "../api/client";
import { AuditDecision, AuditEntry, AuditVerifyResult } from "../types";

export const AuditExplorer: React.FC = () => {
  const [entries, setEntries] = useState<AuditEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [verifying, setVerifying] = useState(false);
  const [verifyResult, setVerifyResult] = useState<AuditVerifyResult | null>(null);

  const fetchEntries = async () => {
    try {
      setLoading(true);
      const data = await api.getAuditEntries({ limit: 100 });
      setEntries(data);
    } catch (err: any) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchEntries();
  }, []);

  const handleVerify = async () => {
    try {
      setVerifying(true);
      const res = await api.verifyAuditLedger();
      setVerifyResult(res);
    } catch (err: any) {
      alert(err.message || "Verification request failed");
    } finally {
      setVerifying(false);
    }
  };

  const getDecisionBadge = (decision: AuditDecision) => {
    switch (decision) {
      case "allowed":
        return <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">ALLOWED</span>;
      case "redacted":
        return <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-amber-500/10 text-amber-400 border border-amber-500/20">REDACTED</span>;
      case "blocked":
        return <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-rose-500/10 text-rose-400 border border-rose-500/20">BLOCKED</span>;
    }
  };

  return (
    <div className="p-8 space-y-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white flex items-center gap-2">
            <Database className="w-6 h-6 text-indigo-400" />
            <span>Immutable Audit Log Explorer</span>
          </h1>
          <p className="text-xs text-slate-400 mt-1">
            Append-Only Cryptographically Chained Ledger (SHA-256) with DB Trigger Immutability
          </p>
        </div>

        <div className="flex items-center gap-2">
          {/* Verify Integrity Action */}
          <button
            onClick={handleVerify}
            disabled={verifying}
            className="flex items-center gap-1.5 px-3.5 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg text-xs font-semibold shadow-lg shadow-indigo-600/30 transition-colors disabled:opacity-50"
          >
            <ShieldCheck className="w-4 h-4" />
            <span>{verifying ? "Verifying Hash Chain..." : "Verify Ledger Integrity"}</span>
          </button>

          {/* Export Actions */}
          <a
            href={api.getAuditExportUrl("json")}
            target="_blank"
            rel="noreferrer"
            className="flex items-center gap-1 px-3 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg text-xs font-semibold border border-slate-700 transition-colors"
          >
            <Download className="w-3.5 h-3.5" />
            <span>JSON</span>
          </a>
          <a
            href={api.getAuditExportUrl("csv")}
            target="_blank"
            rel="noreferrer"
            className="flex items-center gap-1 px-3 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg text-xs font-semibold border border-slate-700 transition-colors"
          >
            <Download className="w-3.5 h-3.5" />
            <span>CSV</span>
          </a>
        </div>
      </div>

      {/* Verification Result Banner */}
      {verifyResult && (
        <div
          className={`p-4 rounded-xl border flex items-start gap-3 shadow-lg ${
            verifyResult.intact
              ? "bg-emerald-950/40 border-emerald-800/60 text-emerald-200"
              : "bg-rose-950/70 border-rose-800/80 text-rose-200"
          }`}
        >
          {verifyResult.intact ? (
            <CheckCircle2 className="w-5 h-5 text-emerald-400 flex-shrink-0 mt-0.5" />
          ) : (
            <ShieldAlert className="w-5 h-5 text-rose-400 flex-shrink-0 mt-0.5" />
          )}
          <div className="space-y-1 text-xs">
            <p className="font-bold text-sm">
              {verifyResult.intact
                ? "Cryptographic Hash Chain Verified Intact"
                : "CRITICAL: Audit Ledger Tampering Detected!"}
            </p>
            <p className="font-mono text-[11px]">{verifyResult.message}</p>
            <p className="text-[10px] opacity-75">
              Verified {verifyResult.checked} records in {verifyResult.verification_time_ms} ms.
              {verifyResult.first_break_id !== null && (
                <span className="font-bold underline ml-1">
                  Compromised record ID: #{verifyResult.first_break_id} (Range: [
                  {verifyResult.broken_range?.join(", ")}])
                </span>
              )}
            </p>
          </div>
        </div>
      )}

      {/* Audit Entries Table */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl shadow-xl overflow-hidden">
        <div className="p-4 border-b border-slate-800 flex items-center justify-between text-xs">
          <span className="font-semibold text-slate-300">
            Consecutive Chained Records ({entries.length})
          </span>
          <button
            onClick={fetchEntries}
            className="text-slate-400 hover:text-white flex items-center gap-1"
          >
            <RefreshCw className="w-3.5 h-3.5" />
            <span>Refresh</span>
          </button>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-800/60 text-slate-400 uppercase text-[10px] font-semibold tracking-wider">
              <tr>
                <th className="px-4 py-3">ID</th>
                <th className="px-4 py-3">Timestamp</th>
                <th className="px-4 py-3">Direction</th>
                <th className="px-4 py-3">Decision</th>
                <th className="px-4 py-3">Risk Tier</th>
                <th className="px-4 py-3">PII Entities</th>
                <th className="px-4 py-3">Injection</th>
                <th className="px-4 py-3">SHA-256 Entry Hash</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60 font-mono text-[11px]">
              {loading ? (
                <tr>
                  <td colSpan={8} className="text-center py-8 text-slate-500 font-sans">
                    Loading audit ledger entries...
                  </td>
                </tr>
              ) : entries.length === 0 ? (
                <tr>
                  <td colSpan={8} className="text-center py-8 text-slate-500 font-sans">
                    Audit ledger is currently empty.
                  </td>
                </tr>
              ) : (
                entries.map((e) => (
                  <tr key={e.id} className="hover:bg-slate-800/40 transition-colors">
                    <td className="px-4 py-3 font-bold text-slate-400">#{e.id}</td>
                    <td className="px-4 py-3 text-slate-300 font-sans text-xs">
                      {new Date(e.ts).toLocaleTimeString()}
                    </td>
                    <td className="px-4 py-3 uppercase text-slate-400">{e.direction}</td>
                    <td className="px-4 py-3">{getDecisionBadge(e.decision)}</td>
                    <td className="px-4 py-3 uppercase font-sans text-[10px] font-bold text-slate-300">
                      {e.tier}
                    </td>
                    <td className="px-4 py-3 font-sans text-xs">
                      {Object.keys(e.pii_entities || {}).length > 0 ? (
                        <span className="text-amber-300">
                          {Object.entries(e.pii_entities)
                            .map(([k, v]) => `${k}:${v}`)
                            .join(", ")}
                        </span>
                      ) : (
                        <span className="text-slate-600">None</span>
                      )}
                    </td>
                    <td className="px-4 py-3 font-sans text-xs">
                      {e.injection_flag ? (
                        <span className="text-rose-400 font-bold">FLAGGED ({e.injection_score})</span>
                      ) : (
                        <span className="text-slate-500">{e.injection_score}</span>
                      )}
                    </td>
                    <td className="px-4 py-3 text-indigo-400 truncate max-w-[150px]" title={e.entry_hash}>
                      {e.entry_hash.substring(0, 16)}...
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
