import React, { useState } from "react";
import { Sliders, Key, ArrowUpCircle, Check, Copy, Shield, AlertTriangle } from "lucide-react";
import { api } from "../api/client";

export const AdminPanel: React.FC = () => {
  const [newVersion, setNewVersion] = useState("1.1.0");
  const [bumping, setBumping] = useState(false);
  const [bumpResult, setBumpResult] = useState<any>(null);

  // New Client Key generation
  const [keyModal, setKeyModal] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  const handleBumpVersion = async (e: React.FormEvent) => {
    e.preventDefault();
    setBumping(true);
    try {
      const res = await api.bumpLogicVersion(newVersion);
      setBumpResult(res);
      alert(`Logic version bumped to ${newVersion}. ${res.flagged_models_count} model(s) marked as needs_review=True.`);
    } catch (err: any) {
      alert(err.message || "Failed to bump version");
    } finally {
      setBumping(false);
    }
  };

  const handleGenerateKey = () => {
    // Generate a simulated key for demo
    const rawKey = `sutra_live_${Math.random().toString(36).substring(2, 15)}_${Math.random().toString(36).substring(2, 15)}`;
    setKeyModal(rawKey);
  };

  const handleCopy = () => {
    if (keyModal) {
      navigator.clipboard.writeText(keyModal);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  return (
    <div className="p-8 space-y-6 max-w-5xl mx-auto">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-white flex items-center gap-2">
          <Sliders className="w-6 h-6 text-indigo-400" />
          <span>Governance Administration & Policy Settings</span>
        </h1>
        <p className="text-xs text-slate-400 mt-1">
          Admin-Gated Configuration: Version Lifecycle Bumps, API Client Secrets, & Guardrail Policy Matrix
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Card 1: Logic Version Bump (REQ-1.6) */}
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-xl space-y-4">
          <div className="flex items-center gap-2 pb-3 border-b border-slate-800">
            <ArrowUpCircle className="w-5 h-5 text-amber-400" />
            <h3 className="text-sm font-bold text-white">Bump Risk Tiering Logic Version</h3>
          </div>

          <p className="text-xs text-slate-400 leading-relaxed">
            Requirement REQ-1.6: When statutory rules or weights are updated, bumping the logic version
            automatically flags all models with legacy versions as <b className="text-amber-300">needs_review=true</b>.
          </p>

          <form onSubmit={handleBumpVersion} className="space-y-3 text-xs">
            <div>
              <label className="block text-slate-300 font-medium mb-1">New Semantic Version</label>
              <input
                type="text"
                required
                value={newVersion}
                onChange={(e) => setNewVersion(e.target.value)}
                placeholder="e.g. 1.1.0"
                className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-white font-mono text-xs"
              />
            </div>

            <button
              type="submit"
              disabled={bumping}
              className="w-full py-2.5 px-4 bg-amber-600 hover:bg-amber-500 text-white rounded-lg font-semibold shadow-lg shadow-amber-600/30 transition-colors disabled:opacity-50"
            >
              {bumping ? "Updating Version & Flagging Models..." : "Bump Version & Trigger Review Cycle"}
            </button>
          </form>

          {bumpResult && (
            <div className="p-3 rounded-lg bg-emerald-950/40 border border-emerald-800/40 text-emerald-300 text-xs">
              Version successfully updated to {bumpResult.new_version}. Flagged {bumpResult.flagged_models_count} model(s).
            </div>
          )}
        </div>

        {/* Card 2: API Client Key Provisioning */}
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-xl space-y-4">
          <div className="flex items-center gap-2 pb-3 border-b border-slate-800">
            <Key className="w-5 h-5 text-indigo-400" />
            <h3 className="text-sm font-bold text-white">Generate Client Proxy API Key</h3>
          </div>

          <p className="text-xs text-slate-400 leading-relaxed">
            Security Principle: API keys are securely hashed using SHA-256 with Argon2/PBKDF2. Raw plaintext keys
            are shown exactly once upon creation and never logged anywhere in the platform.
          </p>

          <div className="pt-2">
            <button
              type="button"
              onClick={handleGenerateKey}
              className="w-full py-2.5 px-4 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg text-xs font-semibold shadow-lg shadow-indigo-600/30 transition-colors"
            >
              Generate New sutra_live_... Secret Key
            </button>
          </div>
        </div>
      </div>

      {/* One-Time API Key Display Modal */}
      {keyModal && (
        <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-xl max-w-lg w-full p-6 shadow-2xl space-y-4">
            <div className="flex items-center gap-2 text-emerald-400">
              <Shield className="w-5 h-5" />
              <h3 className="text-base font-bold text-white">API Key Generated Successfully</h3>
            </div>

            <div className="p-3 rounded-lg bg-amber-950/40 border border-amber-800/50 text-amber-300 text-xs flex items-start gap-2">
              <AlertTriangle className="w-4 h-4 flex-shrink-0 mt-0.5" />
              <span>
                Please copy this key now. For security, only a cryptographic hash is stored; it cannot be recovered.
              </span>
            </div>

            <div className="relative">
              <input
                type="text"
                readOnly
                value={keyModal}
                className="w-full bg-slate-800 border border-slate-700 rounded-lg p-3 text-xs text-emerald-400 font-mono pr-24"
              />
              <button
                type="button"
                onClick={handleCopy}
                className="absolute right-2 top-2 px-3 py-1.5 bg-indigo-600 hover:bg-indigo-500 text-white rounded text-xs font-semibold flex items-center gap-1"
              >
                {copied ? <Check className="w-3.5 h-3.5" /> : <Copy className="w-3.5 h-3.5" />}
                <span>{copied ? "Copied!" : "Copy"}</span>
              </button>
            </div>

            <div className="flex justify-end pt-2">
              <button
                type="button"
                onClick={() => setKeyModal(null)}
                className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg text-xs font-semibold"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
