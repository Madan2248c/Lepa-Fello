"use client";

import { useState, useEffect, useCallback } from "react";
import { Users, Search, Plus, Loader2 } from "lucide-react";
import { useUser } from "@clerk/nextjs";
import { useTenantId } from "@/hooks/useTenantId";
import { apiFetch, AGENT_BASE } from "@/lib/api";
import { useApiFetch } from "@/hooks/useApiFetch";
import AnalysisPanel from "@/components/AnalysisPanel";
import { TableSkeleton } from "@/components/Skeleton";

interface Visitor {
  id: string;
  ip_address: string;
  pages_visited: string;
  time_on_site_seconds: number | null;
  visits_this_week: number | null;
  referral_source: string;
  created_at: string;
}

export default function VisitorsPage() {
  const apiFetch = useApiFetch();
  const tenantId = useTenantId();
  const { user } = useUser();
  const senderName = user ? `${user.firstName || ""} ${user.lastName || ""}`.trim() : "";
  const [visitors, setVisitors] = useState<Visitor[]>([]);
  const [search, setSearch] = useState("");
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [addModalOpen, setAddModalOpen] = useState(false);
  const [panelOpen, setPanelOpen] = useState(false);
  const [selectedVisitor, setSelectedVisitor] = useState<Visitor | null>(null);
  const [result, setResult] = useState<Record<string, unknown> | null>(null);
  const [loading, setLoading] = useState(false);
  const [pageLoading, setPageLoading] = useState(true);
  const [deepResearch, setDeepResearch] = useState<Record<string, unknown> | null>(null);
  const [deepLoading, setDeepLoading] = useState(false);

  const loadVisitors = useCallback(() => {
    apiFetch("/analyze/visitors", tenantId)
      .then((r) => r.json())
      .then((data) => setVisitors(data.visitors || []))
      .catch(() => setVisitors([]))
      .finally(() => setPageLoading(false));
  }, [tenantId]);

  useEffect(() => loadVisitors(), [loadVisitors]);

  const filteredVisitors = visitors.filter(
    (v) =>
      v.ip_address.toLowerCase().includes(search.toLowerCase()) ||
      v.pages_visited.toLowerCase().includes(search.toLowerCase()) ||
      v.referral_source.toLowerCase().includes(search.toLowerCase())
  );

  const allPageSelected = filteredVisitors.length > 0 && filteredVisitors.every((v) => selected.has(v.id));
  const toggleSelect = (id: string) =>
    setSelected((prev) => {
      const next = new Set(prev);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });
  const toggleSelectAll = () =>
    setSelected(allPageSelected ? new Set() : new Set(filteredVisitors.map((v) => v.id)));

  const handleAdd = async (data: Partial<Visitor>) => {
    await apiFetch("/analyze/visitors", tenantId, {
      method: "POST",
      body: JSON.stringify({
        visitor_id: `v_${Date.now()}`,
        ip_address: data.ip_address || "",
        pages_visited: data.pages_visited || "",
        time_on_site_seconds: data.time_on_site_seconds ?? null,
        visits_this_week: data.visits_this_week ?? null,
        referral_source: data.referral_source || "",
      }),
    });
    loadVisitors();
    setAddModalOpen(false);
  };

  const handleRowClick = async (visitor: Visitor) => {
    setSelectedVisitor(visitor);
    setPanelOpen(true);
    setResult(null);
    setDeepResearch(null);
    setLoading(true);

    try {
      const res = await apiFetch("/analyze/visitor", tenantId, {
        method: "POST",
        body: JSON.stringify({
          visitor_id: visitor.id,
          ip_address: visitor.ip_address || undefined,
          pages_visited: visitor.pages_visited ? visitor.pages_visited.split(",").map((p) => p.trim()).filter(Boolean) : [],
          time_on_site_seconds: visitor.time_on_site_seconds ?? undefined,
          visits_this_week: visitor.visits_this_week ?? undefined,
          referral_source: visitor.referral_source || undefined,
        }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Analysis failed");
      setResult(data);
    } catch (err) {
      setResult({ error: err instanceof Error ? err.message : "Analysis failed" });
    } finally {
      setLoading(false);
    }
  };

  const handleDeepResearch = useCallback(async (force = false) => {
    if (!result?.account_name) return;
    setDeepLoading(true);
    setDeepResearch(null);
    try {
      const res = await fetch(`${AGENT_BASE}/research`, {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-Tenant-Id": tenantId ?? "" },
        body: JSON.stringify({ company_name: result.account_name, domain: result.domain || "", tenant_id: tenantId ?? "", sender_name: senderName, force }),
      });
      const data = await res.json();
      setDeepResearch(data);
    } catch (err) {
      setDeepResearch({ error: "Deep research agent unavailable." });
    } finally {
      setDeepLoading(false);
    }
  }, [result, tenantId, senderName]);

  const handlePushHubspot = useCallback(async () => {
    const accountId = (result as { domain?: string })?.domain ||
      (result as { account_name?: string })?.account_name?.toLowerCase().replace(/\s/g, "_");
    if (!accountId) return;
    try {
      const res = await apiFetch("/analyze/push-hubspot", tenantId, {
        method: "POST",
        body: JSON.stringify({ account_id: accountId }),
      });
      const data = await res.json();
      if (!data.success) alert(`HubSpot push failed: ${data.error}`);
      else alert(`✓ ${data.action === "updated" ? "Updated" : "Created"} in HubSpot (ID: ${data.hubspot_id})`);
    } catch {
      alert("HubSpot push failed");
    }
  }, [result, tenantId]);

  return (
    <div className="flex flex-col flex-1 min-w-0">
      {/* Tabs bar - HubSpot style */}
      <div className="flex items-center border-b border-[#DDDDDD] bg-white px-4 py-0 min-h-[48px] mb-0">
        <button className="flex items-center gap-1.5 px-3 py-3 text-[14px] text-[#484848] font-medium border-b-2 border-[#FF5A5F] -mb-px">
          <span>All visitors</span>
          <span className="bg-[#FF5A5F] text-white text-[11px] font-bold rounded-[3px] px-[6px] py-[1px] min-w-[18px] text-center">
            {filteredVisitors.length}
          </span>
        </button>
        <div className="flex-1" />
        <button
          onClick={() => setAddModalOpen(true)}
          className="flex items-center gap-1.5 bg-[#FF5A5F] hover:bg-[#e0504a] text-white text-[14px] font-medium px-4 py-[7px] rounded-[4px] transition-colors"
        >
          <Plus className="w-[14px] h-[14px]" />
          Add visitors
        </button>
      </div>

      {/* Toolbar - HubSpot style */}
      <div className="bg-white px-4 pt-4 pb-0">
        <div className="flex items-center gap-3 mb-4">
          <div className="flex items-center border border-[#DDDDDD] rounded-[4px] px-3 py-[6px] w-[280px] bg-white">
            <input
              type="text"
              placeholder="Search"
              className="flex-1 text-[14px] text-[#484848] placeholder-[#767676] outline-none bg-transparent"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
            <Search className="w-[14px] h-[14px] text-[#767676] flex-shrink-0" />
          </div>
          <div className="flex-1" />
          <div className="flex items-center gap-2">
            <button
              onClick={() => {
                const toExport = selected.size > 0
                  ? filteredVisitors.filter((v) => selected.has(v.id))
                  : filteredVisitors;
                const rows = [["IP Address","Pages Visited","Time on Site (s)","Visits This Week","Referral Source","Added"]];
                toExport.forEach((v) =>
                  rows.push([
                    v.ip_address,
                    v.pages_visited,
                    String(v.time_on_site_seconds ?? ""),
                    String(v.visits_this_week ?? ""),
                    v.referral_source,
                    v.created_at,
                  ])
                );
                const csv = rows.map((r) => r.map((v) => `"${String(v).replace(/"/g, '""')}"`).join(",")).join("\n");
                const a = document.createElement("a");
                a.href = URL.createObjectURL(new Blob([csv], { type: "text/csv" }));
                a.download = "visitors.csv";
                a.click();
              }}
              className="flex items-center gap-1.5 px-3 py-[6px] border border-[#DDDDDD] rounded-[4px] text-[13px] text-[#484848] hover:bg-[#F7F7F7] transition-colors"
            >
              Export CSV
            </button>
          </div>
        </div>
      </div>

      {/* Table - HubSpot style */}
      <div className="flex-1 flex flex-col bg-white overflow-hidden">
        {pageLoading ? (
          <TableSkeleton rows={10} cols={6} />
        ) : filteredVisitors.length === 0 ? (
          <div className="text-center py-16">
            <Users className="w-14 h-14 text-[#767676] mx-auto mb-4" />
            <p className="text-[#767676] mb-4">No visitors yet</p>
            <button
              onClick={() => setAddModalOpen(true)}
              className="inline-block px-5 py-2.5 bg-[#FF5A5F] text-white text-sm font-medium rounded-[4px] hover:bg-[#e0504a]"
            >
              Add your first visitor
            </button>
          </div>
        ) : (
          <>
            <div className="flex-1 overflow-x-auto">
              <table className="w-full min-w-[900px]">
                <thead>
                  <tr className="bg-[#F7F7F7] border-y border-[#DDDDDD]">
                    <th className="w-[44px] px-3 py-2.5">
                      <input
                        type="checkbox"
                        checked={allPageSelected}
                        onChange={toggleSelectAll}
                        className="w-[16px] h-[16px] rounded border-[#DDDDDD] accent-[#FF5A5F]"
                      />
                    </th>
                    <th className="text-left px-3 py-2.5 text-[12px] font-semibold text-[#484848] tracking-wide">IP Address</th>
                    <th className="text-left px-3 py-2.5 text-[12px] font-semibold text-[#484848] tracking-wide">Pages Visited</th>
                    <th className="text-left px-3 py-2.5 text-[12px] font-semibold text-[#484848] tracking-wide">Time on Site</th>
                    <th className="text-left px-3 py-2.5 text-[12px] font-semibold text-[#484848] tracking-wide">Visits This Week</th>
                    <th className="text-left px-3 py-2.5 text-[12px] font-semibold text-[#484848] tracking-wide">Referral Source</th>
                    <th className="text-left px-3 py-2.5 text-[12px] font-semibold text-[#484848] tracking-wide">Added</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredVisitors.map((visitor) => (
                    <tr
                      key={visitor.id}
                      onClick={() => handleRowClick(visitor)}
                      className="border-b border-[#DDDDDD] hover:bg-[#F7F7F7] transition-colors cursor-pointer"
                    >
                      <td className="px-3 py-2.5" onClick={(e) => e.stopPropagation()}>
                        <input
                          type="checkbox"
                          checked={selected.has(visitor.id)}
                          onChange={() => toggleSelect(visitor.id)}
                          className="w-[16px] h-[16px] rounded border-[#DDDDDD] accent-[#FF5A5F]"
                        />
                      </td>
                      <td className="px-3 py-2.5">
                        <a href="#" onClick={(e) => { e.preventDefault(); handleRowClick(visitor); }} className="text-[14px] text-[#0091ae] hover:underline">
                          {visitor.ip_address}
                        </a>
                      </td>
                      <td className="px-3 py-2.5 text-[14px] text-[#484848] max-w-[200px] truncate">{visitor.pages_visited || "—"}</td>
                      <td className="px-3 py-2.5 text-[14px] text-[#484848]">{visitor.time_on_site_seconds != null ? `${visitor.time_on_site_seconds}s` : "—"}</td>
                      <td className="px-3 py-2.5 text-[14px] text-[#484848]">{visitor.visits_this_week ?? "—"}</td>
                      <td className="px-3 py-2.5 text-[14px] text-[#484848]">{visitor.referral_source || "—"}</td>
                      <td className="px-3 py-2.5 text-[14px] text-[#484848]">{new Date(visitor.created_at).toLocaleDateString()}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            {/* Pagination */}
            <div className="flex items-center justify-center gap-2 py-4 border-t border-[#DDDDDD]">
              <button className="flex items-center gap-1 text-[14px] text-[#767676] hover:text-[#484848] transition-colors">Prev</button>
              <span className="w-[28px] h-[28px] flex items-center justify-center border border-[#DDDDDD] rounded-[4px] text-[14px] text-[#484848] font-medium bg-white">1</span>
              <button className="flex items-center gap-1 text-[14px] text-[#767676] hover:text-[#484848] transition-colors">Next</button>
              <div className="ml-4" />
              <button className="flex items-center gap-1 text-[14px] text-[#484848] hover:bg-[#F7F7F7] px-2 py-1 rounded transition-colors">25 per page</button>
            </div>
          </>
        )}
      </div>

      {/* Add Visitor Modal */}
      {addModalOpen && (
        <AddVisitorModal
          onClose={() => setAddModalOpen(false)}
          onAdd={handleAdd}
        />
      )}

      <AnalysisPanel
        isOpen={panelOpen}
        onClose={() => { setPanelOpen(false); setSelectedVisitor(null); }}
        loading={loading}
        result={result && !(result as { error?: string }).error ? (result as unknown as Parameters<typeof AnalysisPanel>[0]["result"]) : null}
        error={(result as { error?: string })?.error}
        deepResearch={deepResearch}
        deepLoading={deepLoading}
        onDeepResearch={result && (result as { account_name?: string }).account_name ? handleDeepResearch : undefined}
        onPushHubspot={result && !(result as { error?: string }).error ? handlePushHubspot : undefined}
      />
    </div>
  );
}

function AddVisitorModal({ onClose, onAdd }: { onClose: () => void; onAdd: (data: Partial<Visitor>) => void }) {
  const [ip, setIp] = useState("");
  const [pages, setPages] = useState("");
  const [timeOnSite, setTimeOnSite] = useState("");
  const [visitsThisWeek, setVisitsThisWeek] = useState("");
  const [referral, setReferral] = useState("");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!ip.trim()) return;
    onAdd({
      ip_address: ip.trim(),
      pages_visited: pages.trim(),
      time_on_site_seconds: timeOnSite ? parseInt(timeOnSite) : null,
      visits_this_week: visitsThisWeek ? parseInt(visitsThisWeek) : null,
      referral_source: referral.trim(),
    });
  };

  return (
    <>
      <div className="fixed inset-0 bg-black/20 z-40" onClick={onClose} />
      <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
        <div className="bg-white rounded-lg shadow-xl max-w-md w-full p-6" onClick={(e) => e.stopPropagation()}>
          <h2 className="text-lg font-semibold text-[#484848] mb-4">Add Visitor</h2>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-[#484848] mb-1.5">IP Address *</label>
              <input
                type="text"
                required
                className="w-full border border-[#DDDDDD] rounded-[4px] px-3 py-2 text-[#484848] focus:border-[#FF5A5F] focus:ring-1 focus:ring-[#FF5A5F]/30"
                value={ip}
                onChange={(e) => setIp(e.target.value)}
                placeholder="104.28.45.123"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-[#484848] mb-1.5">Pages Visited</label>
              <input
                type="text"
                className="w-full border border-[#DDDDDD] rounded-[4px] px-3 py-2 text-[#484848] focus:border-[#FF5A5F] focus:ring-1 focus:ring-[#FF5A5F]/30"
                value={pages}
                onChange={(e) => setPages(e.target.value)}
                placeholder="/pricing, /docs, /case-studies"
              />
              <p className="text-xs text-[#767676] mt-1">Comma-separated</p>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-sm font-medium text-[#484848] mb-1.5">Time on Site (sec)</label>
                <input
                  type="number"
                  className="w-full border border-[#DDDDDD] rounded-[4px] px-3 py-2 text-[#484848] focus:border-[#FF5A5F] focus:ring-1 focus:ring-[#FF5A5F]/30"
                  value={timeOnSite}
                  onChange={(e) => setTimeOnSite(e.target.value)}
                  placeholder="300"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-[#484848] mb-1.5">Visits This Week</label>
                <input
                  type="number"
                  className="w-full border border-[#DDDDDD] rounded-[4px] px-3 py-2 text-[#484848] focus:border-[#FF5A5F] focus:ring-1 focus:ring-[#FF5A5F]/30"
                  value={visitsThisWeek}
                  onChange={(e) => setVisitsThisWeek(e.target.value)}
                  placeholder="3"
                />
              </div>
            </div>
            <div>
              <label className="block text-sm font-medium text-[#484848] mb-1.5">Referral Source</label>
              <input
                type="text"
                className="w-full border border-[#DDDDDD] rounded-[4px] px-3 py-2 text-[#484848] focus:border-[#FF5A5F] focus:ring-1 focus:ring-[#FF5A5F]/30"
                value={referral}
                onChange={(e) => setReferral(e.target.value)}
                placeholder="google, linkedin, direct"
              />
            </div>
            <div className="flex gap-2 pt-4">
              <button
                type="button"
                onClick={onClose}
                className="flex-1 px-4 py-2 border border-[#DDDDDD] text-[#484848] rounded-[4px] hover:bg-[#F7F7F7]"
              >
                Cancel
              </button>
              <button
                type="submit"
                className="flex-1 px-4 py-2 bg-[#FF5A5F] text-white rounded-[4px] hover:bg-[#e0504a]"
              >
                Add
              </button>
            </div>
          </form>
        </div>
      </div>
    </>
  );
}
