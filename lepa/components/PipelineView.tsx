"use client";

import { useState, useEffect } from "react";
import { ChevronDown, ChevronRight, Building2, TrendingUp, Users, Sparkles, Filter, Download, Loader2 } from "lucide-react";
import { useTenantId } from "@/hooks/useTenantId";
import { apiFetch } from "@/lib/api";

interface Prospect {
  id: string;
  company: string;
  domain: string;
  industry: string;
  employees: string;
  intentScore: number;
  trend: "rising" | "stable" | "declining";
  lastActivity: string;
  buyingCommittee: number;
  aiRecommendation: string;
  stage: string;
}

const STAGES = [
  { id: "research", label: "Research" },
  { id: "qualified", label: "Qualified" },
  { id: "engaged", label: "Engaged" },
  { id: "opportunity", label: "Opportunity" }
];

export default function PipelineView() {
  const tenantId = useTenantId();
  const [prospects, setProspects] = useState<Prospect[]>([]);
  const [loading, setLoading] = useState(true);
  const [expandedProspect, setExpandedProspect] = useState<string | null>(null);
  const [selectedStage, setSelectedStage] = useState("research");

  useEffect(() => {
    apiFetch("/analyze/results?limit=100", tenantId)
      .then((res) => res.json())
      .then((data) => {
        const mapped = (data.results || []).map((result: Record<string, unknown>) => {
          const intentScore = (result.intent_score as number) || 0;
          const stage = intentScore >= 8 ? "opportunity" : 
                       intentScore >= 6 ? "engaged" : 
                       intentScore >= 4 ? "qualified" : "research";
          
          return {
            id: result.cache_key as string,
            company: (result.company_name as string) || "Unknown Company",
            domain: (result.domain as string) || "—",
            industry: "—", // Not available in cache summary
            employees: "Unknown",
            intentScore: intentScore,
            trend: "stable" as const,
            lastActivity: `Analyzed ${new Date(result.cached_at as string).toLocaleDateString()}`,
            buyingCommittee: Math.floor(Math.random() * 4) + 1,
            aiRecommendation: "Click to view detailed analysis results.",
            stage: stage
          };
        });
        setProspects(mapped);
        setLoading(false);
      })
      .catch((err) => {
        console.error(err);
        setLoading(false);
      });
  }, [tenantId]);

  const getIntentColor = (score: number) => {
    if (score >= 8) return "text-emerald-700 bg-emerald-100 border-emerald-200";
    if (score >= 6) return "text-[#5B9BD5] bg-[#5B9BD5]/10 border-[#5B9BD5]/20";
    return "text-[#6B6A67] bg-gray-100 border-[#E8E9EA]";
  };

  const getTrendIcon = (trend: string) => {
    switch (trend) {
      case "rising":
        return <TrendingUp className="w-4 h-4 text-emerald-600" />;
      case "declining":
        return <TrendingUp className="w-4 h-4 text-red-600 rotate-180" />;
      default:
        return <TrendingUp className="w-4 h-4 text-[#6B6A67]" />;
    }
  };

  const filteredProspects = prospects.filter(p => p.stage === selectedStage);

  return (
    <div className="h-full flex flex-col space-y-5">
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-semibold text-[#1C1D20] tracking-tight">
            Sales Pipeline
          </h1>
          <p className="text-sm text-[#6B6A67] mt-0.5">Manage and track your highest-intent accounts.</p>
        </div>

        <div className="flex items-center gap-2">
          <button className="h-8 px-3 bg-white border border-[#E8E9EA] text-[#1C1D20] text-sm font-medium rounded-md hover:bg-[#F5F5F6] transition-colors flex items-center gap-2">
            <Filter className="w-4 h-4 text-[#6B6A67]" />
            Filters
          </button>
          <button className="h-8 px-3 bg-[#5B9BD5] text-white text-sm font-medium rounded-md hover:bg-[#4A8BC4] transition-colors flex items-center gap-2">
            <Download className="w-4 h-4" />
            Export
          </button>
        </div>
      </div>

      {/* Stage Tabs */}
      <div className="flex bg-white p-1 rounded-md border border-[#E8E9EA] w-fit">
        {STAGES.map((stage) => {
          const count = prospects.filter((p) => p.stage === stage.id).length;
          return (
            <button
              key={stage.id}
              onClick={() => setSelectedStage(stage.id)}
              className={`px-4 py-2 text-sm font-medium rounded-md transition-colors flex items-center gap-2 ${
                selectedStage === stage.id
                  ? "bg-[#F5F5F6] text-[#1C1D20] border border-[#E8E9EA]"
                  : "text-[#6B6A67] hover:text-[#1C1D20]"
              }`}
            >
              {stage.label}
              <span className="px-1.5 py-0.5 rounded text-[11px] text-[#6B6A67] bg-white border border-[#E8E9EA]">{count}</span>
            </button>
          );
        })}
      </div>

      {/* Prospects List */}
      <div className="flex-1 overflow-auto rounded-lg border border-[#E8E9EA] bg-white">
        <div className="divide-y divide-[#E8E9EA]">
          {loading ? (
            <div className="p-12 text-center flex flex-col items-center justify-center">
              <Loader2 className="w-6 h-6 text-[#5B9BD5] animate-spin mb-3" />
              <p className="text-[#6B6A67] text-sm">Loading prospects...</p>
            </div>
          ) : filteredProspects.map((prospect) => (
            <ProspectCard
              key={prospect.id}
              prospect={prospect}
              expanded={expandedProspect === prospect.id}
              onToggle={() => setExpandedProspect(
                expandedProspect === prospect.id ? null : prospect.id
              )}
              getIntentColor={getIntentColor}
              getTrendIcon={getTrendIcon}
            />
          ))}
          {!loading && filteredProspects.length === 0 && (
            <div className="p-12 text-center">
              <p className="text-[#6B6A67] text-sm">No prospects found in this stage.</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function ProspectCard({
  prospect,
  expanded,
  onToggle,
  getIntentColor,
  getTrendIcon
}: {
  prospect: Prospect;
  expanded: boolean;
  onToggle: () => void;
  getIntentColor: (score: number) => string;
  getTrendIcon: (trend: string) => React.ReactNode;
}) {
  return (
    <div className="bg-white overflow-hidden transition-colors hover:bg-[#FAFBFC]">
      {/* Main Card */}
      <div
        className="p-4 cursor-pointer flex items-center justify-between"
        onClick={onToggle}
      >
        <div className="flex items-center gap-4">
          <button className="text-[#6B6A67] hover:text-[#1C1D20] transition-colors rounded p-0.5">
            {expanded ? (
              <ChevronDown className="w-4 h-4" />
            ) : (
              <ChevronRight className="w-4 h-4" />
            )}
          </button>

          <div className="flex items-center gap-3">
            <div className="w-9 h-9 bg-[#F5F5F6] border border-[#E8E9EA] rounded-lg flex items-center justify-center">
              <Building2 className="w-4 h-4 text-[#6B6A67]" />
            </div>
            <div>
              <div className="text-sm font-medium text-[#1C1D20] flex items-center gap-2 tracking-tight">
                {prospect.company}
                <span className={`px-2 py-0.5 text-[10px] font-medium uppercase tracking-wider rounded border ${getIntentColor(prospect.intentScore)}`}>
                  {prospect.intentScore} Intent
                </span>
              </div>
              <div className="text-[13px] text-[#6B6A67] mt-0.5">
                {prospect.domain} • {prospect.industry} • {prospect.employees}
              </div>
            </div>
          </div>
        </div>

        <div className="flex flex-col items-end gap-1.5">
          <div className="flex items-center gap-1.5 text-xs font-medium text-[#6B6A67]">
            {getTrendIcon(prospect.trend)}
            <span className="capitalize">{prospect.trend}</span>
          </div>
          <div className="text-xs text-[#6B6A67] bg-[#F5F5F6] px-2 py-1 rounded border border-[#E8E9EA]">
            Activity: {prospect.lastActivity}
          </div>
        </div>
      </div>

      {expanded && (
        <div className="border-t border-[#E8E9EA] p-5 bg-[#FAFBFC]">
          {/* AI Recommendation */}
          <div className="mb-5 p-4 rounded-lg border border-[#5B9BD5]/30 bg-[#5B9BD5]/5 flex items-start gap-3">
            <div className="p-1.5 rounded-md bg-[#5B9BD5]/10">
              <Sparkles className="w-4 h-4 text-[#5B9BD5]" />
            </div>
            <div>
              <h4 className="text-[13px] font-semibold text-[#5B9BD5] uppercase tracking-wide mb-0.5">AI Recommendation</h4>
              <p className="text-[#6B6A67] text-[13px] leading-relaxed">{prospect.aiRecommendation}</p>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
            {/* Buying Committee */}
            <div className="bg-white p-4 rounded-lg border border-[#E8E9EA]">
              <h4 className="font-medium text-[#1C1D20] mb-3 text-[13px] flex items-center gap-2">
                <Users className="w-4 h-4 text-[#6B6A67]" />
                Power Base ({prospect.buyingCommittee})
              </h4>
              <div className="space-y-2">
                <div className="flex items-center gap-3 p-2.5 bg-[#FAFBFC] border border-[#E8E9EA] rounded-md hover:border-[#5B9BD5]/30 transition-colors cursor-pointer">
                  <div className="w-8 h-8 bg-[#F5F5F6] rounded-md flex items-center justify-center font-bold text-xs text-[#5B9BD5]">
                    I
                  </div>
                  <div className="flex-1">
                    <div className="text-[13px] font-medium text-[#1C1D20]">Ivan Zhao</div>
                    <div className="text-[11px] text-[#6B6A67]">CEO & Co-founder</div>
                  </div>
                  <span className="text-[9px] font-medium uppercase tracking-wider bg-emerald-100 text-emerald-700 border border-emerald-200 px-1.5 py-0.5 rounded">
                    Economic Buyer
                  </span>
                </div>
                {prospect.buyingCommittee > 1 && (
                  <div className="text-[11px] text-[#6B6A67] font-medium pl-2">
                    + {prospect.buyingCommittee - 1} connected contacts
                  </div>
                )}
              </div>
            </div>

            {/* Intelligence Summary */}
            <div className="bg-white p-4 rounded-lg border border-[#E8E9EA]">
              <h4 className="font-medium text-[#1C1D20] mb-3 text-[13px] flex items-center gap-2">
                <TrendingUp className="w-4 h-4 text-[#6B6A67]" />
                Key Signals
              </h4>
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-[13px] text-[#6B6A67]">Buying Intent</span>
                  <div className="flex items-center gap-2">
                    <div className="h-1.5 w-20 bg-[#E8E9EA] rounded-full overflow-hidden">
                      <div className="h-full bg-[#5B9BD5] rounded-full" style={{ width: `${(prospect.intentScore / 10) * 100}%` }} />
                    </div>
                    <span className="text-[13px] font-medium text-[#1C1D20]">{prospect.intentScore}</span>
                  </div>
                </div>
                <div className="flex justify-between items-center border-t border-[#E8E9EA] pt-2">
                  <span className="text-[13px] text-[#6B6A67]">Site Traffic</span>
                  <span className="text-[13px] font-medium text-[#1C1D20]">{prospect.lastActivity}</span>
                </div>
                <div className="flex justify-between items-center border-t border-[#E8E9EA] pt-2">
                  <span className="text-[13px] text-[#6B6A67]">ICP Match</span>
                  <span className="text-[11px] font-medium text-emerald-700 bg-emerald-100 border border-emerald-200 px-1.5 py-0.5 rounded uppercase tracking-wide">High</span>
                </div>
              </div>
            </div>
          </div>

          {/* Actions */}
          <div className="mt-5 pt-4 border-t border-[#E8E9EA] flex flex-wrap items-center justify-end gap-2">
            <button className="h-8 px-3 bg-white border border-[#E8E9EA] text-[#1C1D20] text-[13px] font-medium rounded-md hover:bg-[#F5F5F6] transition-colors">
              Deep Dive
            </button>
            <button className="h-8 px-3 bg-amber-500 text-white text-[13px] font-medium rounded-md hover:bg-amber-600 transition-colors">
              Generate Draft
            </button>
            <button className="h-8 px-3 bg-[#5B9BD5] text-white text-[13px] font-medium rounded-md hover:bg-[#4A8BC4] transition-colors">
              Qualify
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
