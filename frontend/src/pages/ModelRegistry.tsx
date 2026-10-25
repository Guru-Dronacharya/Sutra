import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  Boxes,
  Plus,
  Compass,
  AlertTriangle,
  Globe2,
  CheckCircle2,
  XCircle,
  ToggleLeft,
  ToggleRight,
  Shield,
} from "lucide-react";
import { api } from "../api/client";
import { AIModel, RiskTier } from "../types";
import { useAuth } from "../context/AuthContext";

export const ModelRegistry: React.FC = () => {
  const { hasRole } = useAuth();
  const [models, setModels] = useState<AIModel[]>([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // New model form state
  const [name, setName] = useState("");
  const [owner, setOwner] = useState("");
  const [description, setDescription] = useState("");
  const [provider, setProvider] = useState("mock");
  const [endpointUrl, setEndpointUrl] = useState("http://mock-llm:8000/v1");
  const [euExposure, setEuExposure] = useState(false);

  const fetchModels = async () => {
    try {
      setLoading(true);
      const data = await api.getModels();
      setModels(data);
    } catch (err: any) {
      setError(err.message || "Failed to load models");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchModels();
  }, []);

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await api.registerModel({
        name,
        owner,
        description,
        provider,
        endpoint_url: endpointUrl,
        eu_exposure: euExposure,
        active_proxy_target: true,
      });
      setShowModal(false);
      setName("");
      setOwner("");
      setDescription("");
      fetchModels();
    } catch (err: any) {
      alert(err.message);
    }
  };

  const handleToggleActive = async (model: AIModel) => {
    if (!model.active_proxy_target && model.current_tier === "prohibited") {
      alert("Safety Enforcement: Prohibited tier models cannot be activated as proxy targets.");
      return;
    }
    try {
      await api.updateModel(model.id, {
        active_proxy_target: !model.active_proxy_target,
      });
      fetchModels();
    } catch (err: any) {
      alert(err.message);
    }
  };

  const getTierBadge = (tier: RiskTier) => {
    switch (tier) {
      case "low":
        return <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">LOW TIER</span>;
      case "medium":
        return <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-amber-500/10 text-amber-400 border border-amber-500/20">MEDIUM TIER</span>;
      case "high":
        return <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-rose-500/10 text-rose-400 border border-rose-500/20">HIGH TIER</span>;
      case "prohibited":
        return <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-red-950 text-red-400 border border-red-800 animate-pulse">PROHIBITED</span>;
    }
  };

  return (
    <div className="p-8 space-y-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white flex items-center gap-2">
            <Boxes className="w-6 h-6 text-indigo-400" />
            <span>AI Model Registry</span>
          </h1>
          <p className="text-xs text-slate-400 mt-1">
            Registered LLM assets under MeitY, DPDP Act 2023, and RBI FREE-AI Governance Oversight
          </p>
        </div>

        {hasRole(["admin", "engineer"]) && (
          <button
            onClick={() => setShowModal(true)}
            className="flex items-center gap-2 px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg text-xs font-semibold transition-colors shadow-lg shadow-indigo-600/20"
          >
            <Plus className="w-4 h-4" />
            <span>Register New AI Model</span>
          </button>
        )}
      </div>

      {/* Model Cards Grid */}
      {loading ? (
        <div className="p-12 text-center text-slate-400 text-sm">Loading registered models...</div>
      ) : models.length === 0 ? (
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-12 text-center">
          <p className="text-slate-400 text-sm mb-4">No AI models registered in governance registry yet.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {models.map((model) => (
            <div
              key={model.id}
              className="bg-slate-900 border border-slate-800 hover:border-slate-700/80 rounded-xl p-5 shadow-sm transition-all flex flex-col justify-between space-y-4"
            >
              <div>
                <div className="flex items-start justify-between gap-2 mb-2">
                  <h3 className="font-semibold text-white text-sm">{model.name}</h3>
                  {getTierBadge(model.current_tier)}
                </div>

                <p className="text-xs text-slate-400 line-clamp-2 mb-3">
                  {model.description || "No description provided."}
                </p>

                <div className="space-y-1.5 text-xs text-slate-300">
                  <div className="flex items-center justify-between text-[11px] py-1 border-b border-slate-800/80">
                    <span className="text-slate-500">Business Unit:</span>
                    <span className="font-medium text-slate-300">{model.owner}</span>
                  </div>
                  <div className="flex items-center justify-between text-[11px] py-1 border-b border-slate-800/80">
                    <span className="text-slate-500">Provider & Target:</span>
                    <span className="font-mono text-[10px] text-indigo-300">{model.provider}</span>
                  </div>
                  <div className="flex items-center justify-between text-[11px] py-1 border-b border-slate-800/80">
                    <span className="text-slate-500">EU Cross-Exposure:</span>
                    <span className="flex items-center gap-1 font-medium">
                      {model.eu_exposure ? (
                        <span className="text-blue-400 flex items-center gap-1">
                          <Globe2 className="w-3 h-3" /> EU Act (Tier: {model.eu_tier?.toUpperCase() || "UNASSESSED"})
                        </span>
                      ) : (
                        <span className="text-slate-400">India Only</span>
                      )}
                    </span>
                  </div>
                </div>

                {/* Needs Review Alert Banner (REQ-1.6) */}
                {model.needs_review && (
                  <div className="mt-3 p-2 rounded-lg bg-amber-950/40 border border-amber-800/50 text-amber-300 text-[11px] flex items-center gap-1.5">
                    <AlertTriangle className="w-3.5 h-3.5 flex-shrink-0" />
                    <span>Logic version updated. Re-assessment required.</span>
                  </div>
                )}
              </div>

              {/* Bottom Actions */}
              <div className="pt-3 border-t border-slate-800 flex items-center justify-between gap-2">
                <div className="flex items-center gap-1.5">
                  <button
                    onClick={() => handleToggleActive(model)}
                    title={model.active_proxy_target ? "Proxy Active" : "Proxy Inactive"}
                    className="text-xs text-slate-400 hover:text-white flex items-center gap-1"
                  >
                    {model.active_proxy_target ? (
                      <ToggleRight className="w-5 h-5 text-emerald-400" />
                    ) : (
                      <ToggleLeft className="w-5 h-5 text-slate-500" />
                    )}
                    <span className="text-[10px]">
                      {model.active_proxy_target ? "Proxy Active" : "Inactive"}
                    </span>
                  </button>
                </div>

                <Link
                  to={`/risk-profiler?modelId=${model.id}`}
                  className="flex items-center gap-1 px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-xs font-semibold text-slate-200 transition-colors"
                >
                  <Compass className="w-3.5 h-3.5 text-amber-400" />
                  <span>Assess Risk</span>
                </Link>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Register Model Dialog Modal */}
      {showModal && (
        <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-xl max-w-lg w-full p-6 shadow-2xl space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-base font-bold text-white flex items-center gap-2">
                <Boxes className="w-5 h-5 text-indigo-400" />
                <span>Register AI Model for Governance</span>
              </h3>
              <button
                onClick={() => setShowModal(false)}
                className="text-slate-400 hover:text-white text-sm"
              >
                ✕
              </button>
            </div>

            <form onSubmit={handleRegister} className="space-y-3 text-xs">
              <div>
                <label className="block text-slate-300 font-medium mb-1">Model Name</label>
                <input
                  type="text"
                  required
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="e.g. FinSure-Customer-Copilot"
                  className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-white"
                />
              </div>

              <div>
                <label className="block text-slate-300 font-medium mb-1">Business Owner / Department</label>
                <input
                  type="text"
                  required
                  value={owner}
                  onChange={(e) => setOwner(e.target.value)}
                  placeholder="e.g. Retail Banking & Underwriting"
                  className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-white"
                />
              </div>

              <div>
                <label className="block text-slate-300 font-medium mb-1">Operational Description</label>
                <textarea
                  rows={2}
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  placeholder="Summarize model purpose and end-user exposure scope..."
                  className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-white"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-slate-300 font-medium mb-1">Provider Adapter</label>
                  <select
                    value={provider}
                    onChange={(e) => setProvider(e.target.value)}
                    className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-white"
                  >
                    <option value="mock">Local Mock (Zero-Cost Offline)</option>
                    <option value="openai_compatible">OpenAI-Compatible Endpoint</option>
                  </select>
                </div>

                <div>
                  <label className="block text-slate-300 font-medium mb-1">Endpoint URL</label>
                  <input
                    type="text"
                    value={endpointUrl}
                    onChange={(e) => setEndpointUrl(e.target.value)}
                    placeholder="http://mock-llm:8000/v1"
                    className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-white font-mono text-[11px]"
                  />
                </div>
              </div>

              <div className="pt-2">
                <label className="flex items-center gap-2 cursor-pointer text-slate-300">
                  <input
                    type="checkbox"
                    checked={euExposure}
                    onChange={(e) => setEuExposure(e.target.checked)}
                    className="w-4 h-4 rounded text-indigo-600 focus:ring-indigo-500 bg-slate-800 border-slate-700"
                  />
                  <span>European Union Exposure (Subject to EU AI Act Reg. 2024/1689)</span>
                </label>
              </div>

              <div className="flex items-center justify-end gap-2 pt-4 border-t border-slate-800">
                <button
                  type="button"
                  onClick={() => setShowModal(false)}
                  className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg text-xs font-semibold"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg text-xs font-semibold shadow-lg shadow-indigo-600/30"
                >
                  Confirm Registration
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
