"use client";

import { useState, useCallback, useEffect } from "react";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface PersonaResult {
  label: string;
  confidence: number;
  reasons: string[];
}

interface IntentResult {
  score: number;
  stage: string;
  reasons: string[];
}

interface RecommendedSalesAction {
  priority: "high" | "medium" | "low";
  actions: string[];
  outreach_angle: string;
}

interface TechStackItem {
  category: string;
  name: string;
  confidence: number;
  source: "builtwith" | "page_scan" | "other";
}

interface BusinessSignal {
  type: "hiring" | "funding" | "expansion" | "product_launch" | "other";
  summary: string;
  published_at: string | null;
  source_url: string | null;
  confidence: number;
}

interface LeadershipContact {
  name: string;
  title: string;
  source_url: string | null;
  confidence: number;
}

interface AnalyzeResponse {
  input_type: string;
  input_id: string;
  account_name: string | null;
  domain: string | null;
  industry: string | null;
  headquarters: string | null;
  company_size: string | null;
  founded_year: string | null;
  business_description: string | null;
  persona: PersonaResult;
  intent: IntentResult;
  technology_stack: TechStackItem[];
  business_signals: BusinessSignal[];
  leadership: LeadershipContact[];
  key_signals_observed: string[];
  ai_summary: string;
  recommended_sales_action: RecommendedSalesAction;
  overall_confidence: number;
  source_links: string[];
  generated_at: string;
}

interface BatchItemSummary {
  index: number;
  label: string;
  job_id: string | null;
  success: boolean;
  account_name: string | null;
  domain: string | null;
  intent_score: number | null;
  intent_stage: string | null;
  overall_confidence: number | null;
  error: string | null;
}

interface BatchResult {
  batch_id: string;
  total: number;
  completed: number;
  failed: number;
  status: string;
  elapsed_seconds: number | null;
  items: BatchItemSummary[];
}

interface AccountSummary {
  account_id: string;
  account_name: string | null;
  domain: string | null;
  industry: string | null;
  visit_count_total: number;
  last_seen_at: string | null;
  latest_intent_score: number | null;
  latest_intent_stage: string | null;
  intent_direction: "rising" | "falling" | "stable" | "unknown";
  run_count: number;
  crm_sync_status: string;
}

const SAMPLE_VISITOR_HIGH_INTENT = {
  visitor_id: "v_high_intent_demo",
  ip_address: "104.28.45.123",
  pages_visited: [
    "/",
    "/features",
    "/pricing",
    "/case-studies",
    "/case-studies/acme-corp",
    "/pricing",
    "/contact-sales",
  ],
  time_on_site_seconds: 480,
  visits_this_week: 4,
  referral_source: "google",
};

const SAMPLE_VISITOR_TECHNICAL = {
  visitor_id: "v_tech_eval_demo",
  ip_address: "203.45.67.89",
  pages_visited: [
    "/",
    "/docs",
    "/docs/getting-started",
    "/api",
    "/api/reference",
    "/docs/integrations",
    "/features",
  ],
  time_on_site_seconds: 720,
  visits_this_week: 2,
  referral_source: "linkedin",
};

const SAMPLE_COMPANY = {
  company_name: "Stripe",
  partial_domain: "stripe.com",
};

const SAMPLE_COMPANY_NO_DOMAIN = {
  company_name: "Notion",
  partial_domain: "",
};

const SAMPLE_BATCH_COMPANIES = [
  { company_name: "Stripe", partial_domain: "stripe.com" },
  { company_name: "HubSpot", partial_domain: "hubspot.com" },
  { company_name: "Notion", partial_domain: "" },
];

function IntentGauge({ score, stage }: { score: number; stage: string }) {
  const percentage = (score / 10) * 100;
  const color =
    score >= 8
      ? "#ef4444"
      : score >= 5
      ? "#f59e0b"
      : score >= 3
      ? "#3b82f6"
      : "#94a3b8";

  return (
    <div className="relative">
      <div className="flex items-end gap-3">
        <span className="text-4xl font-bold" style={{ color }}>
          {score.toFixed(1)}
        </span>
        <span className="text-lg text-[var(--secondary)] mb-1">/ 10</span>
      </div>
      <div className="mt-3 h-2 bg-[var(--card-border)] rounded-full overflow-hidden">
        <div
          className="h-full rounded-full transition-all duration-500"
          style={{ width: `${percentage}%`, backgroundColor: color }}
        />
      </div>
      <div className="mt-2 flex justify-between text-xs text-[var(--muted)]">
        <span>Awareness</span>
        <span>Research</span>
        <span>Evaluation</span>
        <span>Decision</span>
      </div>
    </div>
  );
}

function ConfidenceBar({
  confidence,
  label,
}: {
  confidence: number;
  label: string;
}) {
  return (
    <div>
      <div className="flex justify-between text-sm mb-1">
        <span className="font-medium">{label}</span>
        <span className="text-[var(--secondary)]">
          {Math.round(confidence * 100)}%
        </span>
      </div>
      <div className="h-1.5 bg-[var(--card-border)] rounded-full overflow-hidden">
        <div
          className="h-full bg-[var(--primary)] rounded-full transition-all duration-300"
          style={{ width: `${confidence * 100}%` }}
        />
      </div>
    </div>
  );
}

export default function Dashboard() {
  const [mode, setMode] = useState<"company" | "visitor" | "batch">("company");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<AnalyzeResponse | null>(null);
  const [showJson, setShowJson] = useState(false);
  const [analysisTime, setAnalysisTime] = useState<number | null>(null);

  const [companyName, setCompanyName] = useState("");
  const [partialDomain, setPartialDomain] = useState("");

  const [visitorId, setVisitorId] = useState("");
  const [ipAddress, setIpAddress] = useState("");
  const [pagesVisited, setPagesVisited] = useState("");
  const [timeOnSite, setTimeOnSite] = useState("");
  const [visitsThisWeek, setVisitsThisWeek] = useState("");
  const [referralSource, setReferralSource] = useState("");

  const [batchInput, setBatchInput] = useState(
    SAMPLE_BATCH_COMPANIES.map((c) => c.company_name).join("\n")
  );
  const [batchResult, setBatchResult] = useState<BatchResult | null>(null);

  const [accounts, setAccounts] = useState<AccountSummary[]>([]);
  const [showHistory, setShowHistory] = useState(false);
  const [historyLoading, setHistoryLoading] = useState(false);

  const [crmLoading, setCrmLoading] = useState(false);
  const [crmStatus, setCrmStatus] = useState<{ status: string; external_id?: string; error?: string } | null>(null);

  const handleSubmit = useCallback(
    async (e: React.FormEvent) => {
      e.preventDefault();
      setLoading(true);
      setError(null);
      setResult(null);
      setCrmStatus(null);

      const startTime = performance.now();

      try {
        let endpoint: string;
        let body: object;

        if (mode === "company") {
          endpoint = `${API_BASE}/analyze/company`;
          body = {
            company_name: companyName.trim(),
            partial_domain: partialDomain.trim() || undefined,
          };
        } else {
          endpoint = `${API_BASE}/analyze/visitor`;
          body = {
            visitor_id: visitorId.trim() || `v_${Date.now()}`,
            ip_address: ipAddress.trim() || undefined,
            pages_visited: pagesVisited
              ? pagesVisited
                  .split(",")
                  .map((p) => p.trim())
                  .filter(Boolean)
              : [],
            time_on_site_seconds: timeOnSite ? parseInt(timeOnSite) : undefined,
            visits_this_week: visitsThisWeek
              ? parseInt(visitsThisWeek)
              : undefined,
            referral_source: referralSource.trim() || undefined,
          };
        }

        const res = await fetch(endpoint, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(body),
        });

        const data = await res.json();

        if (!res.ok) {
          throw new Error(data.detail || `Request failed: ${res.status}`);
        }

        setResult(data);
        setAnalysisTime(Math.round(performance.now() - startTime));
      } catch (err) {
        setError(
          err instanceof Error ? err.message : "An unexpected error occurred"
        );
      } finally {
        setLoading(false);
      }
    },
    [
      mode,
      companyName,
      partialDomain,
      visitorId,
      ipAddress,
      pagesVisited,
      timeOnSite,
      visitsThisWeek,
      referralSource,
    ]
  );

  const loadSample = useCallback(
    (sample: Record<string, unknown>) => {
      setResult(null);
      setError(null);

      if ("company_name" in sample) {
        setMode("company");
        setCompanyName(sample.company_name as string);
        setPartialDomain((sample.partial_domain as string) || "");
      } else {
        setMode("visitor");
        setVisitorId(sample.visitor_id as string);
        setIpAddress(sample.ip_address as string);
        setPagesVisited((sample.pages_visited as string[]).join(", "));
        setTimeOnSite((sample.time_on_site_seconds as number).toString());
        setVisitsThisWeek((sample.visits_this_week as number).toString());
        setReferralSource(sample.referral_source as string);
      }
    },
    []
  );

  const handleBatchSubmit = useCallback(async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setBatchResult(null);

    const names = batchInput
      .split("\n")
      .map((n) => n.trim())
      .filter(Boolean)
      .slice(0, 10);

    if (names.length === 0) {
      setError("Enter at least one company name.");
      setLoading(false);
      return;
    }

    try {
      const res = await fetch(`${API_BASE}/batch/analyze`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          companies: names.map((n) => ({ company_name: n })),
          visitors: [],
        }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || `Request failed: ${res.status}`);
      setBatchResult(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Batch failed");
    } finally {
      setLoading(false);
    }
  }, [batchInput]);

  const loadHistory = useCallback(async () => {
    setHistoryLoading(true);
    try {
      const res = await fetch(`${API_BASE}/accounts?limit=20`);
      const data = await res.json();
      setAccounts(data.accounts || []);
      setShowHistory(true);
    } catch {
      setAccounts([]);
    } finally {
      setHistoryLoading(false);
    }
  }, []);

  const handleCrmExport = useCallback(async () => {
    if (!result) return;
    setCrmLoading(true);
    setCrmStatus(null);

    const accountId =
      result.domain?.replace(/[^a-z0-9.\-]/g, "") ||
      result.account_name?.toLowerCase().replace(/[^a-z0-9]/g, "_") ||
      result.input_id;

    try {
      const res = await fetch(`${API_BASE}/crm/export/${accountId}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          provider: "hubspot",
          result_json: result,
        }),
      });
      const data = await res.json();
      setCrmStatus({
        status: data.status,
        external_id: data.external_id,
        error: data.error,
      });
    } catch (err) {
      setCrmStatus({ status: "failed", error: "Network error" });
    } finally {
      setCrmLoading(false);
    }
  }, [result]);

  const priorityConfig = {
    high: { bg: "bg-red-500/10", text: "text-red-500", border: "border-red-500/20" },
    medium: { bg: "bg-amber-500/10", text: "text-amber-500", border: "border-amber-500/20" },
    low: { bg: "bg-green-500/10", text: "text-green-500", border: "border-green-500/20" },
  };

  return (
    <div className="min-h-screen bg-[var(--background)]">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <header className="mb-8">
          <div className="flex items-center gap-3 mb-2">
            <div className="w-10 h-10 rounded-lg bg-[var(--primary)] flex items-center justify-center">
              <span className="text-white font-bold text-lg">L</span>
            </div>
            <div>
              <h1 className="text-2xl font-bold">LEPA</h1>
              <p className="text-sm text-[var(--secondary)]">
                Account Intelligence Platform
              </p>
            </div>
          </div>
        </header>

        <div className="grid gap-8 lg:grid-cols-[420px_1fr]">
          <div className="space-y-6">
            <div className="card">
              <h2 className="text-lg font-semibold mb-4">Analyze Account</h2>

              <div className="toggle-group mb-6">
                <button
                  className={`toggle-btn ${mode === "company" ? "active" : ""}`}
                  onClick={() => { setMode("company"); setError(null); setBatchResult(null); }}
                >
                  Company
                </button>
                <button
                  className={`toggle-btn ${mode === "visitor" ? "active" : ""}`}
                  onClick={() => { setMode("visitor"); setError(null); setBatchResult(null); }}
                >
                  Visitor
                </button>
                <button
                  className={`toggle-btn ${mode === "batch" ? "active" : ""}`}
                  onClick={() => { setMode("batch"); setError(null); setResult(null); }}
                >
                  Batch
                </button>
              </div>

              {mode === "batch" ? (
                <form onSubmit={handleBatchSubmit} className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium mb-1.5">
                      Company Names{" "}
                      <span className="text-[var(--muted)]">(one per line, max 10)</span>
                    </label>
                    <textarea
                      className="input font-mono text-sm"
                      rows={6}
                      value={batchInput}
                      onChange={(e) => setBatchInput(e.target.value)}
                      placeholder={"Stripe\nHubSpot\nNotion\nFigma"}
                    />
                    <p className="text-xs text-[var(--muted)] mt-1">
                      Each company will be fully analyzed in parallel.
                    </p>
                  </div>
                  <button
                    type="submit"
                    className="btn-primary w-full flex items-center justify-center gap-2"
                    disabled={loading}
                  >
                    {loading ? (
                      <>
                        <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                        Running Batch...
                      </>
                    ) : (
                      "Run Batch Analysis"
                    )}
                  </button>
                  {error && (
                    <div className="p-3 bg-red-500/10 border border-red-500/20 text-red-500 rounded-lg text-sm">
                      <strong>Error:</strong> {error}
                    </div>
                  )}
                </form>
              ) : (
              <form onSubmit={handleSubmit} className="space-y-4">
                {mode === "company" ? (
                  <>
                    <div>
                      <label className="block text-sm font-medium mb-1.5">
                        Company Name <span className="text-red-500">*</span>
                      </label>
                      <input
                        type="text"
                        className="input"
                        value={companyName}
                        onChange={(e) => setCompanyName(e.target.value)}
                        placeholder="e.g., Stripe, Notion, Figma"
                        required
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium mb-1.5">
                        Domain{" "}
                        <span className="text-[var(--muted)]">(optional)</span>
                      </label>
                      <input
                        type="text"
                        className="input"
                        value={partialDomain}
                        onChange={(e) => setPartialDomain(e.target.value)}
                        placeholder="e.g., stripe.com"
                      />
                      <p className="text-xs text-[var(--muted)] mt-1">
                        Helps with faster, more accurate enrichment
                      </p>
                    </div>
                  </>
                ) : (
                  <>
                    <div className="grid grid-cols-2 gap-3">
                      <div>
                        <label className="block text-sm font-medium mb-1.5">
                          Visitor ID
                        </label>
                        <input
                          type="text"
                          className="input"
                          value={visitorId}
                          onChange={(e) => setVisitorId(e.target.value)}
                          placeholder="Auto-generated"
                        />
                      </div>
                      <div>
                        <label className="block text-sm font-medium mb-1.5">
                          IP Address
                        </label>
                        <input
                          type="text"
                          className="input"
                          value={ipAddress}
                          onChange={(e) => setIpAddress(e.target.value)}
                          placeholder="104.28.45.123"
                        />
                      </div>
                    </div>
                    <div>
                      <label className="block text-sm font-medium mb-1.5">
                        Pages Visited{" "}
                        <span className="text-[var(--muted)]">
                          (comma-separated)
                        </span>
                      </label>
                      <input
                        type="text"
                        className="input"
                        value={pagesVisited}
                        onChange={(e) => setPagesVisited(e.target.value)}
                        placeholder="/pricing, /docs, /case-studies"
                      />
                    </div>
                    <div className="grid grid-cols-2 gap-3">
                      <div>
                        <label className="block text-sm font-medium mb-1.5">
                          Time on Site (sec)
                        </label>
                        <input
                          type="number"
                          className="input"
                          value={timeOnSite}
                          onChange={(e) => setTimeOnSite(e.target.value)}
                          placeholder="300"
                          min="0"
                        />
                      </div>
                      <div>
                        <label className="block text-sm font-medium mb-1.5">
                          Visits This Week
                        </label>
                        <input
                          type="number"
                          className="input"
                          value={visitsThisWeek}
                          onChange={(e) => setVisitsThisWeek(e.target.value)}
                          placeholder="3"
                          min="0"
                        />
                      </div>
                    </div>
                    <div>
                      <label className="block text-sm font-medium mb-1.5">
                        Referral Source
                      </label>
                      <input
                        type="text"
                        className="input"
                        value={referralSource}
                        onChange={(e) => setReferralSource(e.target.value)}
                        placeholder="google, linkedin, direct"
                      />
                    </div>
                  </>
                )}

                <button
                  type="submit"
                  className="btn-primary w-full flex items-center justify-center gap-2"
                  disabled={loading || (mode === "company" && !companyName.trim())}
                >
                  {loading ? (
                    <>
                      <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                      Analyzing...
                    </>
                  ) : (
                    "Analyze Account"
                  )}
                </button>
              </form>
              )}

              {error && mode !== "batch" && (
                <div className="mt-4 p-3 bg-red-500/10 border border-red-500/20 text-red-500 rounded-lg text-sm">
                  <strong>Error:</strong> {error}
                </div>
              )}
            </div>

            <div className="card">
              <h3 className="text-sm font-medium text-[var(--secondary)] mb-3">
                Quick Examples
              </h3>
              <div className="space-y-2">
                <button
                  className="btn-secondary w-full text-left"
                  onClick={() => loadSample(SAMPLE_COMPANY)}
                >
                  Company: Stripe (with domain)
                </button>
                <button
                  className="btn-secondary w-full text-left"
                  onClick={() => loadSample(SAMPLE_COMPANY_NO_DOMAIN)}
                >
                  Company: Notion (no domain)
                </button>
                <button
                  className="btn-secondary w-full text-left"
                  onClick={() => loadSample(SAMPLE_VISITOR_HIGH_INTENT)}
                >
                  Visitor: High Intent Buyer
                </button>
                <button
                  className="btn-secondary w-full text-left"
                  onClick={() => loadSample(SAMPLE_VISITOR_TECHNICAL)}
                >
                  Visitor: Technical Evaluator
                </button>
              </div>
            </div>

            <div className="card">
              <h3 className="text-sm font-medium text-[var(--secondary)] mb-3">
                Account History
              </h3>
              <button
                className="btn-secondary w-full flex items-center justify-center gap-2"
                onClick={loadHistory}
                disabled={historyLoading}
              >
                {historyLoading ? (
                  <div className="w-4 h-4 border-2 border-current/30 border-t-current rounded-full animate-spin" />
                ) : null}
                {showHistory ? "Refresh History" : "View Tracked Accounts"}
              </button>
              {showHistory && accounts.length === 0 && (
                <p className="text-xs text-[var(--muted)] mt-3 text-center">
                  No accounts tracked yet. Run an analysis first.
                </p>
              )}
              {showHistory && accounts.length > 0 && (
                <div className="mt-3 space-y-2 max-h-64 overflow-y-auto">
                  {accounts.map((acc) => (
                    <div key={acc.account_id} className="p-2.5 bg-[var(--background)] rounded-lg border border-[var(--card-border)]">
                      <div className="flex items-center justify-between">
                        <span className="text-sm font-medium truncate">{acc.account_name || acc.account_id}</span>
                        <span className={`text-xs ml-2 flex-shrink-0 ${
                          acc.intent_direction === "rising" ? "text-emerald-500" :
                          acc.intent_direction === "falling" ? "text-red-400" : "text-[var(--muted)]"
                        }`}>
                          {acc.intent_direction === "rising" ? "↑" : acc.intent_direction === "falling" ? "↓" : "→"}
                          {" "}{acc.latest_intent_score?.toFixed(1) ?? "—"}
                        </span>
                      </div>
                      <div className="flex items-center gap-2 mt-1 text-xs text-[var(--muted)]">
                        <span>{acc.run_count} run{acc.run_count !== 1 ? "s" : ""}</span>
                        <span>•</span>
                        <span>{acc.visit_count_total} visit{acc.visit_count_total !== 1 ? "s" : ""}</span>
                        {acc.crm_sync_status === "synced" && (
                          <><span>•</span><span className="text-emerald-500">CRM ✓</span></>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>

          <div className="space-y-6">
            {loading && (
              <div className="card">
                <div className="flex items-center gap-4">
                  <div className="w-8 h-8 border-3 border-[var(--primary)] border-t-transparent rounded-full animate-spin" />
                  <div>
                    <p className="font-medium">{mode === "batch" ? "Running batch analysis..." : "Analyzing account..."}</p>
                    <p className="text-sm text-[var(--secondary)]">
                      {mode === "batch"
                        ? "Processing each company through the full pipeline..."
                        : "Researching company, detecting tech stack, discovering signals & leadership..."}
                    </p>
                  </div>
                </div>
              </div>
            )}

            {batchResult && !loading && (
              <div className="card">
                <div className="flex items-center justify-between mb-4">
                  <h2 className="text-lg font-semibold">Batch Results</h2>
                  <div className="flex items-center gap-3 text-sm">
                    <span className="text-emerald-500 font-medium">{batchResult.completed} succeeded</span>
                    {batchResult.failed > 0 && <span className="text-red-400">{batchResult.failed} failed</span>}
                    {batchResult.elapsed_seconds && <span className="text-[var(--muted)]">{batchResult.elapsed_seconds}s</span>}
                  </div>
                </div>
                <div className="space-y-2">
                  {batchResult.items.map((item) => (
                    <div key={item.index} className={`p-3 rounded-lg border ${item.success ? "bg-[var(--background)] border-[var(--card-border)]" : "bg-red-500/5 border-red-500/20"}`}>
                      <div className="flex items-center justify-between">
                        <div>
                          <span className="text-sm font-medium">{item.account_name || item.label}</span>
                          {item.domain && <span className="text-xs text-[var(--muted)] ml-2">{item.domain}</span>}
                        </div>
                        {item.success && item.intent_score !== null && (
                          <div className="flex items-center gap-2 text-xs">
                            <span className="text-[var(--secondary)]">{item.intent_stage}</span>
                            <span className="font-semibold">{item.intent_score.toFixed(1)}/10</span>
                            <span className="text-[var(--muted)]">{Math.round((item.overall_confidence || 0) * 100)}% conf</span>
                          </div>
                        )}
                        {!item.success && <span className="text-xs text-red-400">Failed</span>}
                      </div>
                      {item.error && <p className="text-xs text-red-400 mt-1 truncate">{item.error}</p>}
                    </div>
                  ))}
                </div>
                <p className="mt-3 text-xs text-[var(--muted)]">Batch ID: {batchResult.batch_id}</p>
              </div>
            )}

            {result && !loading && (
              <>
                <div className="card">
                  <div className="flex items-start justify-between gap-4 mb-6">
                    <div>
                      <h2 className="text-2xl font-bold">
                        {result.account_name || "Unknown Account"}
                      </h2>
                      {result.domain && (
                        <a
                          href={`https://${result.domain}`}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-[var(--primary)] text-sm hover:underline"
                        >
                          {result.domain} ↗
                        </a>
                      )}
                    </div>
                    <div className="flex items-center gap-2 flex-shrink-0">
                      <span
                        className={`px-3 py-1.5 rounded-full text-xs font-semibold border ${
                          priorityConfig[result.recommended_sales_action.priority].bg
                        } ${priorityConfig[result.recommended_sales_action.priority].text} ${
                          priorityConfig[result.recommended_sales_action.priority].border
                        }`}
                      >
                        {result.recommended_sales_action.priority.toUpperCase()} PRIORITY
                      </span>
                      <button
                        onClick={handleCrmExport}
                        disabled={crmLoading}
                        className="px-3 py-1.5 rounded-full text-xs font-semibold border bg-[var(--primary)]/10 text-[var(--primary)] border-[var(--primary)]/20 hover:bg-[var(--primary)]/20 transition-colors disabled:opacity-50"
                        title="Push to HubSpot CRM"
                      >
                        {crmLoading ? "Syncing..." : "→ HubSpot"}
                      </button>
                    </div>
                  </div>
                  {crmStatus && (
                    <div className={`mb-4 p-3 rounded-lg text-sm border ${
                      crmStatus.status === "synced"
                        ? "bg-emerald-500/10 border-emerald-500/20 text-emerald-600"
                        : crmStatus.status === "skipped"
                        ? "bg-amber-500/10 border-amber-500/20 text-amber-600"
                        : "bg-red-500/10 border-red-500/20 text-red-500"
                    }`}>
                      {crmStatus.status === "synced" && `✓ Synced to HubSpot${crmStatus.external_id ? ` (ID: ${crmStatus.external_id})` : ""}`}
                      {crmStatus.status === "skipped" && "HubSpot token not configured — set HUBSPOT_ACCESS_TOKEN to enable."}
                      {crmStatus.status === "failed" && `CRM sync failed: ${crmStatus.error}`}
                    </div>
                  )}

                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                    <div>
                      <span className="text-[var(--secondary)] block text-xs uppercase tracking-wide mb-1">
                        Industry
                      </span>
                      <span className="font-medium">
                        {result.industry || "—"}
                      </span>
                    </div>
                    <div>
                      <span className="text-[var(--secondary)] block text-xs uppercase tracking-wide mb-1">
                        Size
                      </span>
                      <span className="font-medium">
                        {result.company_size
                          ? `${result.company_size} employees`
                          : "—"}
                      </span>
                    </div>
                    <div>
                      <span className="text-[var(--secondary)] block text-xs uppercase tracking-wide mb-1">
                        Headquarters
                      </span>
                      <span className="font-medium">
                        {result.headquarters || "—"}
                      </span>
                    </div>
                    <div>
                      <span className="text-[var(--secondary)] block text-xs uppercase tracking-wide mb-1">
                        Founded
                      </span>
                      <span className="font-medium">
                        {result.founded_year || "—"}
                      </span>
                    </div>
                  </div>

                  {result.business_description && (
                    <p className="mt-4 text-sm text-[var(--secondary)] border-t border-[var(--card-border)] pt-4">
                      {result.business_description}
                    </p>
                  )}
                </div>

                <div className="grid md:grid-cols-2 gap-6">
                  <div className="card">
                    <h3 className="text-xs uppercase tracking-wide text-[var(--secondary)] mb-4">
                      Visitor Persona
                    </h3>
                    <div className="flex items-center gap-3 mb-4">
                      <span className="text-xl font-bold">
                        {result.persona.label}
                      </span>
                    </div>
                    <ConfidenceBar
                      confidence={result.persona.confidence}
                      label="Confidence"
                    />
                    {result.persona.reasons.length > 0 && (
                      <ul className="mt-4 text-sm text-[var(--secondary)] space-y-1">
                        {result.persona.reasons.map((r, i) => (
                          <li key={i} className="flex gap-2">
                            <span className="text-[var(--primary)]">•</span>
                            {r}
                          </li>
                        ))}
                      </ul>
                    )}
                  </div>

                  <div className="card">
                    <h3 className="text-xs uppercase tracking-wide text-[var(--secondary)] mb-4">
                      Buying Intent
                    </h3>
                    <IntentGauge
                      score={result.intent.score}
                      stage={result.intent.stage}
                    />
                    <div className="mt-4 inline-flex px-3 py-1 rounded-full bg-[var(--primary)]/10 text-[var(--primary)] text-sm font-medium">
                      {result.intent.stage} Stage
                    </div>
                    {result.intent.reasons.length > 0 && (
                      <ul className="mt-4 text-sm text-[var(--secondary)] space-y-1">
                        {result.intent.reasons.slice(0, 4).map((r, i) => (
                          <li key={i} className="flex gap-2">
                            <span className="text-[var(--primary)]">•</span>
                            {r}
                          </li>
                        ))}
                      </ul>
                    )}
                  </div>
                </div>

                <div className="card">
                  <h3 className="text-xs uppercase tracking-wide text-[var(--secondary)] mb-3">
                    AI Account Summary
                  </h3>
                  <p className="text-lg leading-relaxed">{result.ai_summary}</p>
                </div>

                <div className="card">
                  <h3 className="text-xs uppercase tracking-wide text-[var(--secondary)] mb-4">
                    Recommended Actions
                  </h3>
                  <ol className="space-y-3 mb-4">
                    {result.recommended_sales_action.actions.map((action, i) => (
                      <li key={i} className="flex items-start gap-3">
                        <span className="flex-shrink-0 w-6 h-6 rounded-full bg-[var(--primary)] text-white text-xs flex items-center justify-center font-medium">
                          {i + 1}
                        </span>
                        <span>{action}</span>
                      </li>
                    ))}
                  </ol>
                  <div className="p-4 bg-[var(--background)] rounded-lg border border-[var(--card-border)]">
                    <span className="text-xs uppercase tracking-wide text-[var(--secondary)]">
                      Outreach Angle
                    </span>
                    <p className="mt-1 text-sm">
                      {result.recommended_sales_action.outreach_angle}
                    </p>
                  </div>
                </div>

                {result.key_signals_observed.length > 0 && (
                  <div className="card">
                    <h3 className="text-xs uppercase tracking-wide text-[var(--secondary)] mb-3">
                      Key Signals Observed
                    </h3>
                    <div className="flex flex-wrap gap-2">
                      {result.key_signals_observed.map((signal, i) => (
                        <span
                          key={i}
                          className="px-3 py-1.5 bg-[var(--primary)]/10 text-[var(--primary)] rounded-full text-sm"
                        >
                          {signal}
                        </span>
                      ))}
                    </div>
                  </div>
                )}

                {result.technology_stack && result.technology_stack.length > 0 && (
                  <div className="card">
                    <h3 className="text-xs uppercase tracking-wide text-[var(--secondary)] mb-4">
                      Technology Stack
                    </h3>
                    <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
                      {result.technology_stack.slice(0, 12).map((tech, i) => (
                        <div
                          key={i}
                          className="flex items-center justify-between px-3 py-2 bg-[var(--background)] rounded-lg border border-[var(--card-border)]"
                        >
                          <div>
                            <p className="text-sm font-medium">{tech.name}</p>
                            <p className="text-xs text-[var(--muted)] capitalize">{tech.category.replace("_", " ")}</p>
                          </div>
                          <span className="text-xs text-[var(--secondary)] ml-2 flex-shrink-0">
                            {Math.round(tech.confidence * 100)}%
                          </span>
                        </div>
                      ))}
                    </div>
                    <p className="mt-3 text-xs text-[var(--muted)]">
                      Source: {result.technology_stack[0]?.source === "builtwith" ? "BuiltWith API" : "Page scan"}
                    </p>
                  </div>
                )}

                {result.business_signals && result.business_signals.length > 0 && (
                  <div className="card">
                    <h3 className="text-xs uppercase tracking-wide text-[var(--secondary)] mb-4">
                      Business Signals
                    </h3>
                    <div className="space-y-3">
                      {result.business_signals.map((signal, i) => {
                        const signalColors: Record<string, string> = {
                          funding: "bg-emerald-500/10 text-emerald-500 border-emerald-500/20",
                          hiring: "bg-blue-500/10 text-blue-500 border-blue-500/20",
                          expansion: "bg-purple-500/10 text-purple-500 border-purple-500/20",
                          product_launch: "bg-amber-500/10 text-amber-500 border-amber-500/20",
                          other: "bg-[var(--primary)]/10 text-[var(--primary)] border-[var(--primary)]/20",
                        };
                        const colorClass = signalColors[signal.type] || signalColors.other;
                        return (
                          <div key={i} className="flex items-start gap-3 p-3 bg-[var(--background)] rounded-lg border border-[var(--card-border)]">
                            <span className={`px-2 py-0.5 rounded-full text-xs font-semibold border flex-shrink-0 mt-0.5 ${colorClass}`}>
                              {signal.type.replace("_", " ")}
                            </span>
                            <div className="min-w-0">
                              <p className="text-sm leading-snug">{signal.summary}</p>
                              <div className="flex items-center gap-3 mt-1.5">
                                {signal.published_at && (
                                  <span className="text-xs text-[var(--muted)]">{signal.published_at}</span>
                                )}
                                {signal.source_url && (
                                  <a
                                    href={signal.source_url}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    className="text-xs text-[var(--primary)] hover:underline truncate max-w-[200px]"
                                  >
                                    Source ↗
                                  </a>
                                )}
                                <span className="text-xs text-[var(--muted)] ml-auto flex-shrink-0">
                                  {Math.round(signal.confidence * 100)}% confidence
                                </span>
                              </div>
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                )}

                {result.leadership && result.leadership.length > 0 && (
                  <div className="card">
                    <h3 className="text-xs uppercase tracking-wide text-[var(--secondary)] mb-4">
                      Key Decision-Makers
                    </h3>
                    <div className="space-y-2">
                      {result.leadership.map((contact, i) => (
                        <div key={i} className="flex items-center justify-between p-3 bg-[var(--background)] rounded-lg border border-[var(--card-border)]">
                          <div className="flex items-center gap-3">
                            <div className="w-8 h-8 rounded-full bg-[var(--primary)]/10 flex items-center justify-center flex-shrink-0">
                              <span className="text-[var(--primary)] text-sm font-semibold">
                                {contact.name.charAt(0).toUpperCase()}
                              </span>
                            </div>
                            <div>
                              <p className="text-sm font-medium">{contact.name}</p>
                              <p className="text-xs text-[var(--secondary)]">{contact.title}</p>
                            </div>
                          </div>
                          <div className="flex items-center gap-2 flex-shrink-0">
                            {contact.source_url && (
                              <a
                                href={contact.source_url}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="text-xs text-[var(--primary)] hover:underline"
                              >
                                ↗
                              </a>
                            )}
                            <span className="text-xs text-[var(--muted)]">
                              {Math.round(contact.confidence * 100)}%
                            </span>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                <div className="card">
                  <button
                    className="flex items-center justify-between w-full text-left"
                    onClick={() => setShowJson(!showJson)}
                  >
                    <h3 className="text-xs uppercase tracking-wide text-[var(--secondary)]">
                      Raw JSON Response
                    </h3>
                    <span className="text-[var(--secondary)] text-lg">
                      {showJson ? "−" : "+"}
                    </span>
                  </button>
                  {showJson && (
                    <pre className="json-viewer mt-4">
                      {JSON.stringify(result, null, 2)}
                    </pre>
                  )}
                </div>

                <div className="flex items-center justify-between text-xs text-[var(--muted)]">
                  <span>
                    Confidence: {Math.round(result.overall_confidence * 100)}%
                    {result.source_links.length > 0 &&
                      ` • ${result.source_links.length} source(s)`}
                  </span>
                  <span>
                    {analysisTime && `${(analysisTime / 1000).toFixed(1)}s • `}
                    {new Date(result.generated_at).toLocaleString()}
                  </span>
                </div>
              </>
            )}

            {!result && !loading && (
              <div className="card text-center py-16">
                <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-[var(--primary)]/10 flex items-center justify-center">
                  <svg
                    className="w-8 h-8 text-[var(--primary)]"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
                    />
                  </svg>
                </div>
                <h3 className="text-xl font-semibold mb-2">
                  Ready to Analyze
                </h3>
                <p className="text-[var(--secondary)] max-w-md mx-auto">
                  Enter a company name or visitor signals to generate AI-powered
                  account intelligence, or try one of the quick examples.
                </p>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
