/**
 * Centralized API Client for Sutra Monorepo Services.
 */

const isNginx = typeof window !== "undefined" && (window.location.port === "3000" || window.location.port === "");
const API_BASE = isNginx ? "/api" : "http://localhost:8000";
const GATEWAY_BASE = isNginx ? "/gateway" : "http://localhost:8001";
const AUDIT_BASE = isNginx ? "/audit" : "http://localhost:8002";
const RAG_BASE = isNginx ? "/rag" : "http://localhost:8003";

function getHeaders(token?: string | null): Record<string, string> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
  };
  const activeToken = token || localStorage.getItem("sutra_token");
  if (activeToken) {
    headers["Authorization"] = `Bearer ${activeToken}`;
  }
  return headers;
}

export const api = {
  // ==================== Auth ====================
  async login(email: string, password: string) {
    const res = await fetch(`${API_BASE}/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || "Authentication failed");
    }
    return res.json();
  },

  async getMe() {
    const res = await fetch(`${API_BASE}/auth/me`, {
      headers: getHeaders(),
    });
    if (!res.ok) throw new Error("Failed to fetch user session");
    return res.json();
  },

  // ==================== Model Registry ====================
  async getModels() {
    const res = await fetch(`${API_BASE}/models`, {
      headers: getHeaders(),
    });
    if (!res.ok) throw new Error("Failed to fetch models");
    return res.json();
  },

  async getModel(id: string) {
    const res = await fetch(`${API_BASE}/models/${id}`, {
      headers: getHeaders(),
    });
    if (!res.ok) throw new Error("Failed to fetch model");
    return res.json();
  },

  async registerModel(data: any) {
    const res = await fetch(`${API_BASE}/models`, {
      method: "POST",
      headers: getHeaders(),
      body: JSON.stringify(data),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || "Failed to register model");
    }
    return res.json();
  },

  async updateModel(id: string, data: any) {
    const res = await fetch(`${API_BASE}/models/${id}`, {
      method: "PATCH",
      headers: getHeaders(),
      body: JSON.stringify(data),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || "Failed to update model");
    }
    return res.json();
  },

  async getQuestionnaire() {
    const res = await fetch(`${API_BASE}/models/questionnaire`, {
      headers: getHeaders(),
    });
    if (!res.ok) throw new Error("Failed to fetch questionnaire");
    return res.json();
  },

  async assessModel(id: string, answers: any) {
    const res = await fetch(`${API_BASE}/models/${id}/assess`, {
      method: "POST",
      headers: getHeaders(),
      body: JSON.stringify({ answers }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || "Risk assessment failed");
    }
    return res.json();
  },

  async overrideTier(id: string, override_tier: string, justification: string) {
    const res = await fetch(`${API_BASE}/models/${id}/override`, {
      method: "POST",
      headers: getHeaders(),
      body: JSON.stringify({ override_tier, justification }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || "Tier override failed");
    }
    return res.json();
  },

  async getModelAssessments(id: string) {
    const res = await fetch(`${API_BASE}/models/${id}/assessments`, {
      headers: getHeaders(),
    });
    if (!res.ok) return [];
    return res.json();
  },

  async bumpLogicVersion(new_version: string) {
    const res = await fetch(`${API_BASE}/models/bump-logic-version`, {
      method: "POST",
      headers: getHeaders(),
      body: JSON.stringify({ new_version }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || "Failed to bump logic version");
    }
    return res.json();
  },

  // ==================== Guardrail Gateway Playground ====================
  async chatCompletions(apiKey: string, messages: any[], modelName: string) {
    const res = await fetch(`${GATEWAY_BASE}/v1/chat/completions`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Authorization": `Bearer ${apiKey}`,
      },
      body: JSON.stringify({
        model: modelName,
        messages,
      }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || `Proxy Error (${res.status})`);
    }
    return res.json();
  },

  // ==================== Audit Ledger ====================
  async getAuditEntries(params?: { model_id?: string; limit?: number }) {
    const query = new URLSearchParams();
    if (params?.model_id) query.append("model_id", params.model_id);
    if (params?.limit) query.append("limit", String(params.limit));

    const res = await fetch(`${AUDIT_BASE}/audit/entries?${query.toString()}`, {
      headers: getHeaders(),
    });
    if (!res.ok) throw new Error("Failed to fetch audit entries");
    return res.json();
  },

  async verifyAuditLedger() {
    const res = await fetch(`${AUDIT_BASE}/audit/verify`, {
      headers: getHeaders(),
    });
    if (!res.ok) throw new Error("Verification failed");
    return res.json();
  },

  getAuditExportUrl(format: "json" | "csv") {
    return `${AUDIT_BASE}/audit/export?format=${format}`;
  },

  // ==================== Regulatory RAG & Gap Analysis ====================
  async uploadPolicy(modelId: string, filename: string, content: string) {
    const res = await fetch(`${RAG_BASE}/rag/policies`, {
      method: "POST",
      headers: getHeaders(),
      body: JSON.stringify({
        model_id: modelId,
        filename,
        content,
      }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || "Failed to upload policy");
    }
    return res.json();
  },

  async runGapAnalysis(modelId: string, policyDocId: string, exposureProfile: string) {
    const res = await fetch(`${RAG_BASE}/rag/gap-analysis`, {
      method: "POST",
      headers: getHeaders(),
      body: JSON.stringify({
        model_id: modelId,
        policy_document_id: policyDocId,
        exposure_profile: exposureProfile,
      }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || "Gap analysis failed");
    }
    return res.json();
  },

  async getGapReport(reportId: string) {
    const res = await fetch(`${RAG_BASE}/rag/gap-reports/${reportId}`, {
      headers: getHeaders(),
    });
    if (!res.ok) throw new Error("Failed to fetch gap report");
    return res.json();
  },

  getGapReportPdfUrl(reportId: string) {
    return `${RAG_BASE}/rag/gap-reports/${reportId}/pdf`;
  },
};
