import React, { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import {
  Compass,
  ShieldAlert,
  AlertTriangle,
  ArrowRight,
  ArrowLeft,
  CheckCircle,
  AlertOctagon,
  Award,
  Globe2,
  FileEdit,
  Info,
} from "lucide-react";
import { api } from "../api/client";
import { AIModel, FactorRationale, RiskTier } from "../types";
import { useAuth } from "../context/AuthContext";

export const RiskProfiler: React.FC = () => {
  const [searchParams] = useSearchParams();
  const modelIdFromUrl = searchParams.get("modelId");
  const { user, hasRole } = useAuth();

  const [models, setModels] = useState<AIModel[]>([]);
  const [selectedModelId, setSelectedModelId] = useState<string>(modelIdFromUrl || "");
  const [questionnaire, setQuestionnaire] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  // Current wizard step
  const [currentStepIndex, setCurrentStepIndex] = useState(0);

  // Dynamic answers state
  const [answers, setAnswers] = useState<Record<string, any>>({
    social_scoring: false,
    real_time_biometric_surveillance: false,
    manipulative_subliminal_techniques: false,
    vulnerability_exploitation: false,
    processes_personal_data: false,
    sensitive_data_categories: ["none"],
    data_volume_scale: "low",
    processes_children_data: false,
    public_facing: false,
    sector: "general_enterprise",
    decision_impact: "advisory_with_human_in_loop",
    human_override_available: true,
    autonomous_action_execution: false,
    generates_synthetic_media: false,
    public_dissemination: false,
    automated_provenance_labelling: true,
    serves_eu_residents: false,
    annex_iii_domain: false,
  });

  // Assessment result
  const [assessmentResult, setAssessmentResult] = useState<any>(null);
  const [submitting, setSubmitting] = useState(false);

  // Manual Override Modal state (REQ-1.5)
  const [showOverrideModal, setShowOverrideModal] = useState(false);
  const [overrideTier, setOverrideTier] = useState<RiskTier>("high");
  const [overrideJustification, setOverrideJustification] = useState("");
  const [overriding, setOverriding] = useState(false);

  useEffect(() => {
    const init = async () => {
      try {
        setLoading(true);
        const [modelsData, qData] = await Promise.all([
          api.getModels(),
          api.getQuestionnaire(),
        ]);
        setModels(modelsData);
        setQuestionnaire(qData);
        if (!selectedModelId && modelsData.length > 0) {
          setSelectedModelId(modelsData[0].id);
        }
      } catch (err) {
        console.error(err);
      } finally {
        setLoading(false);
      }
    };
    init();
  }, []);

  const handleAnswerChange = (key: string, value: any) => {
    setAnswers((prev) => ({ ...prev, [key]: value }));
  };

  const handleToggleMultiSelect = (key: string, option: string) => {
    const current = (answers[key] as string[]) || [];
    if (option === "none") {
      setAnswers((prev) => ({ ...prev, [key]: ["none"] }));
      return;
    }
    const filtered = current.filter((x) => x !== "none");
    if (filtered.includes(option)) {
      const updated = filtered.filter((x) => x !== option);
      setAnswers((prev) => ({ ...prev, [key]: updated.length ? updated : ["none"] }));
    } else {
      setAnswers((prev) => ({ ...prev, [key]: [...filtered, option] }));
    }
  };

  const handleSubmitAssessment = async () => {
    if (!selectedModelId) {
      alert("Please select a target model to assess.");
      return;
    }
    try {
      setSubmitting(true);
      const res = await api.assessModel(selectedModelId, answers);
      setAssessmentResult(res);
    } catch (err: any) {
      alert(err.message || "Assessment submission failed.");
    } finally {
      setSubmitting(false);
    }
  };

  const handleApplyOverride = async (e: React.FormEvent) => {
    e.preventDefault();
    if (overrideJustification.trim().length < 10) {
      alert("Please provide a substantive justification (minimum 10 characters).");
      return;
    }
    try {
      setOverriding(true);
      const res = await api.overrideTier(selectedModelId, overrideTier, overrideJustification);
      alert(`Model tier successfully overridden to ${overrideTier.toUpperCase()}.`);
      setShowOverrideModal(false);
      // Refresh assessment
      setAssessmentResult((prev: any) => ({
        ...prev,
        computed_tier: overrideTier,
        override_tier: overrideTier,
        override_justification: overrideJustification,
      }));
    } catch (err: any) {
      alert(err.message || "Failed to apply override.");
    } finally {
      setOverriding(false);
    }
  };

  const currentCategory = questionnaire?.categories?.[currentStepIndex];
  const totalCategories = questionnaire?.categories?.length || 0;

  return (
    <div className="p-8 space-y-6 max-w-5xl mx-auto">
      {/* Header with Legal Disclaimer */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white flex items-center gap-2">
            <Compass className="w-6 h-6 text-amber-400" />
            <span>Model Risk Profiler Wizard</span>
          </h1>
          <p className="text-xs text-slate-400 mt-1">
            Config-Driven Risk Scoring Engine Aligned with MeitY 7 Sutras, DPDP Act 2023, and RBI FREE-AI
          </p>
        </div>

        {/* Model Selector */}
        <div className="flex items-center gap-2">
          <label className="text-xs text-slate-400 font-medium">Target Model:</label>
          <select
            value={selectedModelId}
            onChange={(e) => {
              setSelectedModelId(e.target.value);
              setAssessmentResult(null);
            }}
            className="bg-slate-800 border border-slate-700 text-xs text-white rounded-lg px-3 py-1.5 font-medium"
          >
            {models.map((m) => (
              <option key={m.id} value={m.id}>
                {m.name} ({m.current_tier.toUpperCase()})
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Mandatory Disclaimer Box */}
      <div className="bg-amber-950/40 border border-amber-800/40 rounded-xl p-3 text-amber-300 text-xs flex items-center gap-2.5">
        <AlertTriangle className="w-4 h-4 flex-shrink-0" />
        <span className="font-medium">
          Decision-support information only; not legal advice. Evaluated against Sutra Tiering Logic v1.0.0.
        </span>
      </div>

      {loading ? (
        <div className="p-12 text-center text-slate-400 text-sm">Loading questionnaire rules...</div>
      ) : assessmentResult ? (
        /* ==================== Assessment Results View ==================== */
        <div className="space-y-6">
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-xl space-y-6">
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-6 border-b border-slate-800">
              <div>
                <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
                  Assessment Completed
                </span>
                <h2 className="text-xl font-bold text-white mt-1">
                  Risk Classification & Regulatory Mapping
                </h2>
                <p className="text-xs text-slate-400 mt-0.5">
                  Logic Version: {assessmentResult.tiering_logic_version}
                </p>
              </div>

              <div className="flex items-center gap-3">
                {/* Computed India Tier */}
                <div className="text-center p-3 rounded-lg bg-slate-800/80 border border-slate-700 min-w-[120px]">
                  <p className="text-[10px] text-slate-400 uppercase font-semibold">India Risk Tier</p>
                  <p
                    className={`text-lg font-black uppercase mt-0.5 ${
                      assessmentResult.computed_tier === "prohibited"
                        ? "text-red-400 animate-pulse"
                        : assessmentResult.computed_tier === "high"
                        ? "text-rose-400"
                        : assessmentResult.computed_tier === "medium"
                        ? "text-amber-400"
                        : "text-emerald-400"
                    }`}
                  >
                    {assessmentResult.computed_tier}
                  </p>
                  <p className="text-[10px] text-slate-500 font-mono">Score: {assessmentResult.score}/100</p>
                </div>

                {/* EU Tier (if exposure true) */}
                {assessmentResult.eu_tier && (
                  <div className="text-center p-3 rounded-lg bg-slate-800/80 border border-slate-700 min-w-[120px]">
                    <p className="text-[10px] text-slate-400 uppercase font-semibold flex items-center justify-center gap-1">
                      <Globe2 className="w-3 h-3 text-blue-400" /> EU AI Act
                    </p>
                    <p className="text-lg font-black uppercase text-blue-400 mt-0.5">
                      {assessmentResult.eu_tier}
                    </p>
                    <p className="text-[9px] text-slate-500">Cross-Walk</p>
                  </div>
                )}
              </div>
            </div>

            {/* Category Sub-Scores Breakdown */}
            {assessmentResult.category_scores && (
              <div>
                <h3 className="text-xs font-semibold text-slate-300 uppercase tracking-wider mb-3">
                  Multi-Dimensional Weighted Breakdown
                </h3>
                <div className="grid grid-cols-2 sm:grid-cols-5 gap-3">
                  {Object.entries(assessmentResult.category_scores).map(([cat, val]) => (
                    <div key={cat} className="p-3 rounded-lg bg-slate-800/40 border border-slate-800 text-xs">
                      <p className="text-[10px] text-slate-400 capitalize truncate">
                        {cat.replace("_", " ")}
                      </p>
                      <p className="text-sm font-bold text-white mt-1">{val as number} / 100</p>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Regulatory Principles & Rationale Cards (REQ-1.3) */}
            <div>
              <h3 className="text-xs font-semibold text-slate-300 uppercase tracking-wider mb-3">
                Contributing Factors & Statutory Principles
              </h3>
              <div className="space-y-3">
                {assessmentResult.rationale?.map((r: FactorRationale, idx: number) => (
                  <div
                    key={idx}
                    className="p-4 rounded-lg bg-slate-800/60 border border-slate-700/60 space-y-2 text-xs"
                  >
                    <div className="flex items-center justify-between">
                      <span className="font-semibold text-slate-200">{r.reason}</span>
                      {r.escalated_to && (
                        <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-rose-950 text-rose-300 border border-rose-800">
                          ESCALATED TO {r.escalated_to.toUpperCase()}
                        </span>
                      )}
                    </div>

                    {/* Mapped Principles Badges */}
                    <div className="flex flex-wrap gap-2 pt-1">
                      {r.principles?.map((p, pIdx) => (
                        <div
                          key={pIdx}
                          className="px-2 py-1 rounded bg-slate-700/50 border border-slate-600/50 text-[10px] text-slate-300 flex items-center gap-1.5"
                        >
                          <Award className="w-3 h-3 text-amber-400" />
                          <span className="font-medium text-amber-300">{p.sutra || p.pillar}</span>
                          <span className="text-slate-400">({p.framework})</span>
                        </div>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Actions: Re-Assess & Manual Override */}
            <div className="pt-6 border-t border-slate-800 flex items-center justify-between">
              <button
                onClick={() => setAssessmentResult(null)}
                className="px-4 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-xs font-semibold text-slate-300"
              >
                Re-Assess Questionnaire
              </button>

              {/* Manual Override Button (REQ-1.5: Role-gated to Compliance Officer / Admin) */}
              {hasRole(["admin", "compliance_officer"]) && (
                <button
                  onClick={() => setShowOverrideModal(true)}
                  className="flex items-center gap-1.5 px-4 py-2 rounded-lg bg-amber-600/20 hover:bg-amber-600/30 border border-amber-500/40 text-amber-300 text-xs font-semibold transition-colors"
                >
                  <FileEdit className="w-3.5 h-3.5" />
                  <span>Manual Risk Tier Override</span>
                </button>
              )}
            </div>
          </div>
        </div>
      ) : (
        /* ==================== Questionnaire Wizard Steps ==================== */
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-xl space-y-6">
          {/* Step Progress Stepper */}
          <div className="space-y-2">
            <div className="flex items-center justify-between text-xs text-slate-400">
              <span>
                Category {currentStepIndex + 1} of {totalCategories}:{" "}
                <b className="text-white">{currentCategory?.name}</b>
              </span>
              <span>{Math.round(((currentStepIndex + 1) / totalCategories) * 100)}% Completed</span>
            </div>
            <div className="w-full bg-slate-800 rounded-full h-1.5 overflow-hidden">
              <div
                className="bg-indigo-500 h-1.5 transition-all duration-300"
                style={{ width: `${((currentStepIndex + 1) / totalCategories) * 100}%` }}
              />
            </div>
          </div>

          <p className="text-xs text-slate-400 pb-2 border-b border-slate-800">
            {currentCategory?.description}
          </p>

          {/* Question List */}
          <div className="space-y-6">
            {currentCategory?.questions?.map((q: any) => (
              <div key={q.id} className="p-4 rounded-lg bg-slate-800/40 border border-slate-800 space-y-2.5">
                <div className="flex items-start justify-between gap-4">
                  <label className="text-xs font-semibold text-slate-200 leading-snug">
                    {q.label}
                  </label>
                  {q.legal_basis && (
                    <span className="text-[10px] font-mono text-slate-500 bg-slate-800 px-2 py-0.5 rounded flex-shrink-0">
                      {q.legal_basis}
                    </span>
                  )}
                </div>

                {/* Boolean Question */}
                {q.type === "boolean" && (
                  <div className="flex items-center gap-3 pt-1">
                    <button
                      type="button"
                      onClick={() => handleAnswerChange(q.id, true)}
                      className={`px-3 py-1.5 rounded-lg text-xs font-medium border transition-all ${
                        answers[q.id] === true
                          ? "bg-indigo-600 border-indigo-500 text-white"
                          : "bg-slate-800/80 border-slate-700 text-slate-400 hover:text-white"
                      }`}
                    >
                      Yes
                    </button>
                    <button
                      type="button"
                      onClick={() => handleAnswerChange(q.id, false)}
                      className={`px-3 py-1.5 rounded-lg text-xs font-medium border transition-all ${
                        answers[q.id] === false
                          ? "bg-slate-700 border-slate-600 text-white"
                          : "bg-slate-800/80 border-slate-700 text-slate-400 hover:text-white"
                      }`}
                    >
                      No
                    </button>
                  </div>
                )}

                {/* Single Select Question */}
                {q.type === "select" && (
                  <div className="space-y-2 pt-1">
                    {q.options.map((opt: string) => {
                      const label = q.option_labels?.[opt] || opt;
                      const selected = answers[q.id] === opt;
                      return (
                        <div
                          key={opt}
                          onClick={() => handleAnswerChange(q.id, opt)}
                          className={`p-3 rounded-lg border text-xs cursor-pointer transition-all flex items-center justify-between ${
                            selected
                              ? "bg-indigo-600/10 border-indigo-500 text-indigo-200"
                              : "bg-slate-800/40 border-slate-700/60 text-slate-400 hover:bg-slate-800/80 hover:text-slate-200"
                          }`}
                        >
                          <span>{label}</span>
                          <span
                            className={`w-3.5 h-3.5 rounded-full border ${
                              selected ? "border-indigo-400 bg-indigo-500" : "border-slate-600"
                            }`}
                          />
                        </div>
                      );
                    })}
                  </div>
                )}

                {/* Multi Select Question */}
                {q.type === "multi_select" && (
                  <div className="flex flex-wrap gap-2 pt-1">
                    {q.options.map((opt: string) => {
                      const selected = (answers[q.id] as string[])?.includes(opt);
                      return (
                        <button
                          key={opt}
                          type="button"
                          onClick={() => handleToggleMultiSelect(q.id, opt)}
                          className={`px-3 py-1.5 rounded-lg text-xs font-medium border transition-all capitalize ${
                            selected
                              ? "bg-indigo-600 border-indigo-500 text-white"
                              : "bg-slate-800/80 border-slate-700 text-slate-400 hover:text-white"
                          }`}
                        >
                          {opt.replace("_", " ")}
                        </button>
                      );
                    })}
                  </div>
                )}
              </div>
            ))}
          </div>

          {/* Navigation Controls */}
          <div className="pt-6 border-t border-slate-800 flex items-center justify-between">
            <button
              type="button"
              disabled={currentStepIndex === 0}
              onClick={() => setCurrentStepIndex((p) => Math.max(0, p - 1))}
              className="flex items-center gap-1.5 px-4 py-2 bg-slate-800 hover:bg-slate-700 disabled:opacity-40 text-xs font-semibold text-slate-300 rounded-lg"
            >
              <ArrowLeft className="w-4 h-4" />
              <span>Previous Category</span>
            </button>

            {currentStepIndex < totalCategories - 1 ? (
              <button
                type="button"
                onClick={() => setCurrentStepIndex((p) => Math.min(totalCategories - 1, p + 1))}
                className="flex items-center gap-1.5 px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-xs font-semibold text-white rounded-lg shadow-lg shadow-indigo-600/30"
              >
                <span>Next Category</span>
                <ArrowRight className="w-4 h-4" />
              </button>
            ) : (
              <button
                type="button"
                disabled={submitting}
                onClick={handleSubmitAssessment}
                className="flex items-center gap-1.5 px-5 py-2.5 bg-emerald-600 hover:bg-emerald-500 text-xs font-semibold text-white rounded-lg shadow-lg shadow-emerald-600/30"
              >
                <CheckCircle className="w-4 h-4" />
                <span>{submitting ? "Computing Risk Profile..." : "Evaluate & Persist Risk Tier"}</span>
              </button>
            )}
          </div>
        </div>
      )}

      {/* Manual Override Modal (REQ-1.5) */}
      {showOverrideModal && (
        <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-xl max-w-lg w-full p-6 shadow-2xl space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-base font-bold text-white flex items-center gap-2">
                <FileEdit className="w-5 h-5 text-amber-400" />
                <span>Manual Risk Tier Override</span>
              </h3>
              <button
                onClick={() => setShowOverrideModal(false)}
                className="text-slate-400 hover:text-white text-sm"
              >
                ✕
              </button>
            </div>

            <p className="text-xs text-slate-400 leading-relaxed">
              Business Rule (REQ-1.5): Only Compliance Officers or Admins can override the computed risk tier.
              A written justification is mandatory and permanently stored in the audit trail.
            </p>

            <form onSubmit={handleApplyOverride} className="space-y-4 text-xs">
              <div>
                <label className="block text-slate-300 font-medium mb-1">Target Override Tier</label>
                <select
                  value={overrideTier}
                  onChange={(e) => setOverrideTier(e.target.value as RiskTier)}
                  className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-white font-semibold"
                >
                  <option value="low">Low Risk</option>
                  <option value="medium">Medium Risk</option>
                  <option value="high">High Risk</option>
                  <option value="prohibited">Prohibited (Unacceptable Risk)</option>
                </select>
              </div>

              <div>
                <label className="block text-slate-300 font-medium mb-1">
                  Written Justification (Mandatory)
                </label>
                <textarea
                  required
                  rows={3}
                  value={overrideJustification}
                  onChange={(e) => setOverrideJustification(e.target.value)}
                  placeholder="Explain why this model's risk classification is being manually adjusted (e.g., enhanced compensating human controls, external regulatory waiver)..."
                  className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-white"
                />
              </div>

              <div className="flex items-center justify-end gap-2 pt-2 border-t border-slate-800">
                <button
                  type="button"
                  onClick={() => setShowOverrideModal(false)}
                  className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg text-xs font-semibold"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={overriding}
                  className="px-4 py-2 bg-amber-600 hover:bg-amber-500 text-white rounded-lg text-xs font-semibold shadow-lg shadow-amber-600/30"
                >
                  {overriding ? "Recording Override..." : "Record Official Override"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
