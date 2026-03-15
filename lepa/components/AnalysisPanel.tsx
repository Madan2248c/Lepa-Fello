"use client";

import React, { useState } from "react";
import { X, Loader2, Search, Sparkles, Copy, Check, ExternalLink, Send } from "lucide-react";

interface AnalyzeResponse {
  account_name: string | null;
  domain: string | null;
  industry: string | null;
  company_size: string | null;
  headquarters: string | null;
  founded_year: string | null;
  business_description: string | null;
  persona: { label: string; confidence: number; reasons: string[] };
  intent: { score: number; stage: string; reasons: string[] };
  technology_stack: Array<{ name: string; category: string; confidence: number }>;
  business_signals: Array<{ type: string; summary: string; confidence: number }>;
  key_signals_observed: string[];
  ai_summary: string;
  recommended_sales_action: { priority: "high" | "medium" | "low"; actions: string[]; outreach_angle: string };
  overall_confidence: number;
  icp_fit?: { overall_score: number; tier: string; dimension_scores: Record<string, number>; fit_reasons: string[]; gap_reasons: string[] };
  buying_committee?: Array<{ name: string; title: string; role: string; source_url?: string | null }>;
  outreach_draft?: { email_subject: string; email_body: string; linkedin_message: string };
}

interface AnalysisPanelProps {
  isOpen: boolean;
  onClose: () => void;
  loading?: boolean;
  result?: AnalyzeResponse | null;
  error?: string | null;
  deepResearch?: Record<string, unknown> | null;
  deepLoading?: boolean;
  onDeepResearch?: (force?: boolean) => void;
  onPushHubspot?: () => void;
}

const priorityColors = {
  high: "bg-red-600 text-white",
  medium: "bg-amber-600 text-white",
  low: "bg-emerald-600 text-white",
};

const roleColors: Record<string, string> = {
  "Economic Buyer": "bg-purple-600 text-white",
  "Champion": "bg-emerald-600 text-white",
  "Technical Evaluator": "bg-[#ff7a59] text-white",
  "Blocker": "bg-red-600 text-white",
  "End User": "bg-amber-600 text-white",
};

// ── Deep Research structured renderer ─────────────────────────────────────

function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false);
  const copy = () => {
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };
  return (
    <button onClick={copy} className="flex items-center gap-1 px-2 py-1 text-xs text-[#516f90] hover:text-[#33475b] border border-[#cbd6e2] rounded hover:bg-[#f5f8fa]">
      {copied ? <Check className="w-3 h-3 text-green-600" /> : <Copy className="w-3 h-3" />}
      {copied ? "Copied" : "Copy"}
    </button>
  );
}

function Section({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="border border-[#cbd6e2] rounded-[4px] overflow-hidden">
      <div className="px-3 py-1.5 bg-[#eaf0f6] border-b border-[#cbd6e2]">
        <span className="text-[11px] font-semibold text-[#516f90] uppercase tracking-wide">{label}</span>
      </div>
      <div className="p-3">{children}</div>
    </div>
  );
}

function IcpRadar({ dims }: { dims: Record<string, number> }) {
  const { RadarChart, Radar, PolarGrid, PolarAngleAxis, ResponsiveContainer } = require("recharts");
  const chartData = Object.entries(dims).map(([key, value]) => ({
    subject: key.charAt(0).toUpperCase() + key.slice(1),
    value,
    fullMark: 100,
  }));
  return (
    <ResponsiveContainer width="100%" height={200}>
      <RadarChart data={chartData}>
        <PolarGrid stroke="#cbd6e2" />
        <PolarAngleAxis dataKey="subject" tick={{ fontSize: 11, fill: "#516f90" }} />
        <Radar dataKey="value" stroke="#7c3aed" fill="#7c3aed" fillOpacity={0.25} strokeWidth={2} />
      </RadarChart>
    </ResponsiveContainer>
  );
}

function DeepResearchView({ data }: { data: Record<string, unknown> }) {
  const committee = (data.buying_committee as Array<Record<string, string>>) || [];
  const signals = (data.signals as string[]) || [];
  const angles = (data.outreach_angles as string[]) || [];
  const email = data.cold_email as { subject?: string; body?: string } | undefined;
  const score = data.icp_score as number | undefined;
  const dims = data.icp_dimensions as Record<string, number> | undefined;

  return (
    <div className="space-y-3 mt-2">
      {!!data.account_overview && (
        <Section label="Account Overview">
          <p className="text-sm text-[#33475b]">{String(data.account_overview)}</p>
        </Section>
      )}

      {score !== undefined && (
        <Section label={`ICP Fit · ${score}/100 · ${String(data.icp_tier || "")}`}>
          {dims ? (
            <IcpRadar dims={dims} />
          ) : null}
        </Section>
      )}

      {signals.length > 0 && (
        <Section label={`Signal Velocity · ${String(data.signal_velocity || "")}`}>
          <ul className="space-y-1">
            {signals.map((s, i) => (
              <li key={i} className="flex gap-2 text-sm text-[#33475b]">
                <span className="text-purple-500 mt-0.5">•</span>{s}
              </li>
            ))}
          </ul>
        </Section>
      )}

      {committee.length > 0 ? (
        <Section label="Buying Committee">
          <div className="space-y-2">
            {committee.map((m, i) => (
              <div key={i} className="flex items-start justify-between gap-2 py-1.5 border-b border-[#eaf0f6] last:border-0">
                <div className="min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-medium text-[#33475b]">{m.name}</span>
                    <span className={`text-[10px] px-1.5 py-0.5 rounded font-medium ${roleColors[m.role] || "bg-gray-100 text-gray-600"}`}>{m.role}</span>
                    <span className={`text-[10px] px-1.5 py-0.5 rounded ${m.priority === "High" ? "bg-green-100 text-green-700" : m.priority === "Medium" ? "bg-yellow-100 text-yellow-700" : "bg-gray-100 text-gray-600"}`}>{m.priority}</span>
                  </div>
                  <p className="text-xs text-[#516f90]">{m.title}</p>
                  {!!m.engagement_angle && <p className="text-xs text-[#7c98b6] mt-0.5">{m.engagement_angle}</p>}
                </div>
                {!!m.linkedin_url && (
                  <a href={m.linkedin_url} target="_blank" rel="noreferrer" className="shrink-0 text-[#516f90] hover:text-purple-600">
                    <ExternalLink className="w-3.5 h-3.5" />
                  </a>
                )}
              </div>
            ))}
          </div>
        </Section>
      ) : null}

      {angles.length > 0 ? (
        <Section label="Outreach Angles">
          <ol className="space-y-1 list-decimal list-inside">
            {angles.map((a, i) => <li key={i} className="text-sm text-[#33475b]">{a}</li>)}
          </ol>
        </Section>
      ) : null}

      {!!email?.body && (
        <Section label="Cold Email">
          <div className="flex items-start justify-between gap-2 mb-2">
            <p className="text-xs text-[#516f90]"><span className="font-medium">Subject:</span> {email.subject}</p>
            <CopyButton text={`Subject: ${email.subject}\n\n${email.body}`} />
          </div>
          <p className="text-sm text-[#33475b] whitespace-pre-line">{email.body}</p>
        </Section>
      )}

      {!!data.linkedin_message && (
        <Section label="LinkedIn Message">
          <div className="flex items-start justify-between gap-2">
            <p className="text-sm text-[#33475b] whitespace-pre-line flex-1">{String(data.linkedin_message)}</p>
            <CopyButton text={String(data.linkedin_message)} />
          </div>
        </Section>
      )}

      {!!data.next_action && (
        <Section label="Recommended Next Action">
          <p className="text-sm text-[#33475b]">{String(data.next_action)}</p>
        </Section>
      )}
    </div>
  );
}

export default function AnalysisPanel({
  isOpen,
  onClose,
  loading,
  result,
  error,
  deepResearch,
  deepLoading,
  onDeepResearch,
  onPushHubspot,
}: AnalysisPanelProps) {
  if (!isOpen) return null;

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black/20 z-40 transition-opacity"
        onClick={onClose}
        aria-hidden="true"
      />

      {/* Panel */}
      <aside
        className="fixed top-0 right-0 h-full w-full max-w-xl bg-white border-l border-[#cbd6e2] shadow-xl z-50 flex flex-col"
        role="dialog"
        aria-label="Analysis results"
      >
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-[#cbd6e2] shrink-0">
          <h2 className="text-lg font-semibold text-[#33475b]">Account Analysis</h2>
          <div className="flex items-center gap-2">
            {onPushHubspot && result && (
              <button
                onClick={onPushHubspot}
                className="flex items-center gap-1.5 px-3 py-1.5 bg-[#ff7a59] hover:bg-[#ff5c35] text-white text-xs font-medium rounded-[4px] transition-colors"
              >
                <Send className="w-3.5 h-3.5" />
                Push to HubSpot
              </button>
            )}
            <button
              onClick={onClose}
              className="p-2 text-[#516f90] hover:text-[#33475b] hover:bg-[#f5f8fa] rounded-[4px] transition-colors"
              aria-label="Close panel"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6">
          {loading && (
            <div className="flex flex-col items-center justify-center py-16">
              <Loader2 className="w-12 h-12 text-[#ff7a59] animate-spin mb-4" />
              <p className="text-base font-medium text-[#33475b] mb-2">Analyzing account...</p>
              <p className="text-sm text-[#516f90]">Researching company, tech stack, signals & leadership...</p>
            </div>
          )}

          {error && !loading && (
            <div className="py-8 text-center">
              <p className="text-sm text-red-600">{error}</p>
            </div>
          )}

          {result && !loading && !error && (
            <div className="space-y-6">
              {/* Account header */}
              <div className="pb-4 border-b border-[#cbd6e2]">
                <div className="flex items-start justify-between gap-4 mb-3">
                  <div>
                    <h3 className="text-xl font-bold text-[#33475b]">{result.account_name || "Unknown Account"}</h3>
                    {result.domain && (
                      <a
                    href={`https://${result.domain}`}
                    target="_blank"
                    rel="noreferrer"
                    className="text-sm text-[#0091ae] hover:underline"
                      >
                        {result.domain} →
                      </a>
                    )}
                  </div>
                  <span className={`px-3 py-1 rounded-md text-xs font-bold uppercase shrink-0 ${priorityColors[result.recommended_sales_action?.priority]}`}>
                    {result.recommended_sales_action?.priority}
                  </span>
                </div>
                <div className="grid grid-cols-2 gap-3 text-sm">
                  {[
                    { label: "Industry", value: result.industry },
                    { label: "Size", value: result.company_size },
                    { label: "HQ", value: result.headquarters },
                    { label: "Founded", value: result.founded_year },
                  ].map((field, i) => (
                    <div key={i}>
                  <p className="text-xs font-medium text-[#516f90] uppercase mb-0.5">{field.label}</p>
                  <p className="font-medium text-[#33475b]">{field.value || "—"}</p>
                    </div>
                  ))}
                </div>
                {result.business_description && (
                  <p className="mt-3 pt-3 border-t border-[#cbd6e2] text-sm text-[#516f90]">{result.business_description}</p>
                )}
              </div>

              {/* Persona & Intent */}
              <div className="grid grid-cols-2 gap-4">
                <div className="p-4 bg-[#f5f8fa] border border-[#cbd6e2] rounded-[4px]">
                  <h4 className="text-xs font-medium text-[#516f90] uppercase mb-2">Visitor Persona</h4>
                  <p className="text-lg font-bold text-[#33475b] mb-1">{result.persona?.label ?? "—"}</p>
                  <div className="h-1.5 bg-[#cbd6e2] rounded-full overflow-hidden">
                    <div className="h-full bg-[#ff7a59] rounded-full" style={{ width: `${(result.persona?.confidence ?? 0) * 100}%` }} />
                  </div>
                  <p className="text-xs text-[#516f90] mt-1">{Math.round((result.persona?.confidence ?? 0) * 100)}% confidence</p>
                </div>
                <div className="p-4 bg-[#f5f8fa] border border-[#cbd6e2] rounded-[4px]">
                  <h4 className="text-xs font-medium text-[#516f90] uppercase mb-2">Buying Intent</h4>
                  <p className="text-2xl font-bold text-[#ff7a59]">{result.intent?.score?.toFixed(1) ?? "—"}<span className="text-base font-normal text-[#516f90]">/10</span></p>
                  <p className="text-sm font-medium text-[#0091ae] mt-1">{result.intent?.stage ?? "—"} Stage</p>
                </div>
              </div>

              {/* AI Summary */}
              <div>
                <h4 className="text-xs font-medium text-[#516f90] uppercase mb-2">AI Summary</h4>
                <p className="text-sm leading-relaxed text-[#33475b]">{result.ai_summary}</p>
              </div>

              {/* Recommended Actions */}
              {result.recommended_sales_action && (
              <div>
                <h4 className="text-xs font-medium text-[#516f90] uppercase mb-3">Recommended Actions</h4>
                <ol className="space-y-2 mb-3">
                  {(result.recommended_sales_action.actions ?? []).map((action, i) => (
                    <li key={i} className="flex items-start gap-2 text-sm text-[#33475b]">
                      <span className="flex-shrink-0 w-5 h-5 bg-[#ff7a59] text-white font-bold flex items-center justify-center rounded text-xs">
                        {i + 1}
                      </span>
                      {action}
                    </li>
                  ))}
                </ol>
                {result.recommended_sales_action.outreach_angle && (
                <div className="p-3 bg-[#f5f8fa] border border-[#cbd6e2] rounded-[4px]">
                  <p className="text-xs font-medium text-[#0091ae] uppercase mb-1">Outreach Angle</p>
                  <p className="text-sm text-[#33475b]">{result.recommended_sales_action.outreach_angle}</p>
                </div>
                )}
              </div>
              )}

              {/* Key Signals */}
              {result.key_signals_observed?.length > 0 && (
                <div>
                  <h4 className="text-xs font-medium text-[#516f90] uppercase mb-2">Key Signals</h4>
                  <div className="flex flex-wrap gap-2">
                    {result.key_signals_observed?.map((signal, i) => (
                      <span key={i} className="px-2.5 py-1 bg-[#ff7a59]/10 text-[#ff7a59] border border-[#ff7a59]/20 rounded-[4px] text-xs font-medium">
                        {signal}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {/* Tech Stack */}
              {result.technology_stack && result.technology_stack.length > 0 && (
                <div>
                  <h4 className="text-xs font-medium text-[#516f90] uppercase mb-2">Technology Stack</h4>
                  <div className="grid grid-cols-2 gap-2">
                    {result.technology_stack.slice(0, 6).map((tech, i) => (
                      <div key={i} className="p-2 bg-[#f5f8fa] border border-[#cbd6e2] rounded-[4px]">
                        <p className="text-sm font-medium text-[#33475b]">{tech.name}</p>
                        <p className="text-xs text-[#516f90] capitalize">{tech.category.replace("_", " ")}</p>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* ICP Fit */}
              {result.icp_fit && (
                <div>
                  <h4 className="text-xs font-medium text-[#516f90] uppercase mb-2">ICP Fit</h4>
                  <div className="flex items-center gap-2 mb-2">
                    <span className={`px-2.5 py-1 rounded-md text-sm font-bold ${
                      result.icp_fit?.overall_score >= 80 ? "bg-emerald-600 text-white" :
                      result.icp_fit?.overall_score >= 60 ? "bg-[#ff7a59] text-white" :
                      "bg-amber-600 text-white"
                    }`}>
                      {result.icp_fit?.overall_score}/100
                    </span>
                    <span className="text-sm text-[#516f90]">{result.icp_fit.tier}</span>
                  </div>
                </div>
              )}

              {result.buying_committee && result.buying_committee.length > 0 && (
                <div>
                  <h4 className="text-xs font-medium text-[#516f90] uppercase mb-3">Buying Committee</h4>
                  <div className="space-y-2">
                    {result.buying_committee.map((member, i) => (
                      <div key={i} className="flex items-center justify-between p-3 bg-[#f5f8fa] border border-[#cbd6e2] rounded-[4px]">
                        <div className="flex items-center gap-3 min-w-0">
                          <div className="w-8 h-8 bg-[#cbd6e2] rounded-full flex items-center justify-center text-[#33475b] font-bold text-xs shrink-0">
                            {member.name.charAt(0)}
                          </div>
                          <div className="min-w-0">
                            <div className="flex items-center gap-2">
                              <p className="text-sm font-medium text-[#33475b] truncate">{member.name}</p>
                              {member.source_url && (
                                <a href={member.source_url} target="_blank" rel="noopener noreferrer" className="text-[#0091ae] hover:underline text-xs shrink-0">
                                  LinkedIn →
                                </a>
                              )}
                            </div>
                            <p className="text-xs text-[#516f90] truncate">{member.title}</p>
                          </div>
                        </div>
                        <span className={`px-2 py-0.5 rounded-[4px] text-xs font-bold shrink-0 ${roleColors[member.role] || "bg-[#516f90] text-white"}`}>
                          {member.role}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Deep Research */}
              {onDeepResearch && (
                <div className="pt-4 border-t border-[#cbd6e2]">
                  <div className="flex items-center justify-between mb-3">
                    <h4 className="text-xs font-medium text-[#516f90] uppercase">Deep Research</h4>
                    <button
                      onClick={() => onDeepResearch?.()}
                      disabled={deepLoading}
                      className="flex items-center gap-2 px-3 py-1.5 bg-purple-600 text-white text-sm font-medium rounded-md hover:bg-purple-700 disabled:opacity-50"
                    >
                      {deepLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Sparkles className="w-4 h-4" />}
                      {deepLoading ? "Researching..." : "Run Deep Research"}
                    </button>
                  </div>
                  {deepLoading && (
                    <p className="text-sm text-purple-600">Agent researching — Apollo, Exa, BuiltWith, LinkedIn...</p>
                  )}
                  {deepResearch && !deepLoading && (
                    deepResearch.error
                      ? <p className="text-sm text-red-600">{String(deepResearch.error)}</p>
                      : <>
                          {deepResearch._cached && (
                            <p className="text-xs text-[#7c98b6] mb-2 flex items-center gap-1">
                              Showing cached result —
                              <button onClick={() => onDeepResearch?.(true)} className="text-purple-600 underline hover:no-underline">re-run</button>
                            </p>
                          )}
                          <DeepResearchView data={deepResearch} />
                        </>
                  )}
                </div>
              )}

              <p className="text-xs text-[#7c98b6]">Confidence: {Math.round(result.overall_confidence * 100)}%</p>
            </div>
          )}
        </div>
      </aside>
    </>
  );
}
