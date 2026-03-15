"use client";

import { useEffect, useState, useCallback } from "react";
import { Building2, Search, Plus, Loader2 } from "lucide-react";
import { TableSkeleton } from "@/components/Skeleton";
import { useUser } from "@clerk/nextjs";
import { useTenantId } from "@/hooks/useTenantId";
import { apiFetch, AGENT_BASE } from "@/lib/api";
import { useApiFetch } from "@/hooks/useApiFetch";
import AnalysisPanel from "@/components/AnalysisPanel";

interface Account {
  account_id: string;
  account_name: string | null;
  domain: string | null;
  industry: string | null;
  latest_intent_score: number | null;
  latest_intent_stage: string | null;
  intent_direction: string;
  run_count: number;
  visit_count_total: number;
}

export default function CompaniesPage() {
  const apiFetch = useApiFetch();
  const tenantId = useTenantId();
  const { user } = useUser();
  const senderName = user ? `${user.firstName || ""} ${user.lastName || ""}`.trim() : "";
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [page, setPage] = useState(1);
  const PAGE_SIZE = 25;
  const [addModalOpen, setAddModalOpen] = useState(false);
  const [addLoading, setAddLoading] = useState(false);
  const [panelOpen, setPanelOpen] = useState(false);
  const [selectedAccount, setSelectedAccount] = useState<Account | null>(null);
  const [result, setResult] = useState<Record<string, unknown> | null>(null);
  const [analysisLoading, setAnalysisLoading] = useState(false);
  const [deepResearch, setDeepResearch] = useState<Record<string, unknown> | null>(null);
  const [deepLoading, setDeepLoading] = useState(false);
  const [icpProfile, setIcpProfile] = useState<{ target_industries?: string[]; target_company_sizes?: string[] } | null>(null);
  const [pushingHs, setPushingHs] = useState<Set<string>>(new Set());

  const loadAccounts = useCallback(() => {
    apiFetch("/accounts?limit=100", tenantId)
      .then((res) => res.json())
      .then((data) => setAccounts(data.accounts || []))
      .catch(() => setAccounts([]))
      .finally(() => setLoading(false));
  }, [tenantId]);

  useEffect(() => {
    loadAccounts();
    apiFetch("/icp", tenantId)
      .then((r) => r.ok ? r.json() : null)
      .then((data) => { if (data?.profile) setIcpProfile(data.profile); })
      .catch(() => {});
  }, [loadAccounts, tenantId]);

  const icpPayload = () => {
    if (!icpProfile) return {};
    const sizes = icpProfile.target_company_sizes || [];
    const sizeNums = sizes.map((s) => parseInt(s)).filter(Boolean);
    return {
      icp_industries: icpProfile.target_industries || [],
      icp_size_min: sizeNums.length ? Math.min(...sizeNums) : undefined,
      icp_size_max: sizeNums.length ? Math.max(...sizeNums) : undefined,
    };
  };

  const filteredAccounts = accounts.filter(
    (a) =>
      (a.account_name || "").toLowerCase().includes(search.toLowerCase()) ||
      (a.domain || "").toLowerCase().includes(search.toLowerCase()) ||
      (a.industry || "").toLowerCase().includes(search.toLowerCase())
  );
  const totalPages = Math.max(1, Math.ceil(filteredAccounts.length / PAGE_SIZE));
  const pagedAccounts = filteredAccounts.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE);
  const allPageSelected = pagedAccounts.length > 0 && pagedAccounts.every(a => selected.has(a.account_id));

  const toggleSelect = (id: string) => setSelected(prev => {
    const next = new Set(prev); next.has(id) ? next.delete(id) : next.add(id); return next;
  });
  const toggleSelectAll = () => setSelected(
    allPageSelected ? new Set() : new Set(pagedAccounts.map(a => a.account_id))
  );

  const pushToHubspot = async (accountId: string) => {
    const key = accountId;
    setPushingHs(prev => new Set(prev).add(key));
    try {
      const res = await apiFetch("/analyze/push-hubspot", tenantId, {
        method: "POST", body: JSON.stringify({ account_id: accountId }),
      });
      return res.json();
    } finally {
      setPushingHs(prev => { const s = new Set(prev); s.delete(key); return s; });
    }
  };

  const handleAdd = async (companyName: string, domain: string) => {
    if (!companyName.trim()) return;
    setAddLoading(true);
    try {
      const res = await apiFetch("/analyze/company", tenantId, {
        method: "POST",
        body: JSON.stringify({
          company_name: companyName.trim(),
          partial_domain: domain.trim() || undefined,
          ...icpPayload(),
        }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Analysis failed");
      loadAccounts();
      setAddModalOpen(false);
      setSelectedAccount({
        account_id: data.domain || data.account_name?.toLowerCase().replace(/\s/g, "_") || "",
        account_name: data.account_name,
        domain: data.domain,
        industry: data.industry,
        latest_intent_score: data.intent?.score,
        latest_intent_stage: data.intent?.stage,
        intent_direction: "unknown",
        run_count: 1,
        visit_count_total: 0,
      });
      setResult(data);
      setPanelOpen(true);
    } catch (err) {
      setResult({ error: err instanceof Error ? err.message : "Analysis failed" });
      setPanelOpen(true);
    } finally {
      setAddLoading(false);
    }
  };

  const handleRowClick = async (account: Account) => {
    setSelectedAccount(account);
    setPanelOpen(true);
    setResult(null);
    setDeepResearch(null);
    setAnalysisLoading(true);

    try {
      const res = await apiFetch("/analyze/company", tenantId, {
        method: "POST",
        body: JSON.stringify({
          company_name: account.account_name || account.account_id,
          partial_domain: account.domain || undefined,
          ...icpPayload(),
        }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Analysis failed");
      setResult(data);
    } catch (err) {
      setResult({ error: err instanceof Error ? err.message : "Analysis failed" });
    } finally {
      setAnalysisLoading(false);
    }
  };

  const handleDeepResearch = useCallback(async (force = false) => {
    const name = (result as { account_name?: string })?.account_name;
    if (!name) return;
    const domain = (result as { domain?: string }).domain;
    setDeepLoading(true);
    setDeepResearch(null);
    try {
      const res = await fetch(`${AGENT_BASE}/research`, {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-Tenant-Id": tenantId ?? "" },
        body: JSON.stringify({ company_name: name, domain: domain || "", tenant_id: tenantId ?? "", sender_name: senderName, force }),
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
    const accountId = selectedAccount?.domain || selectedAccount?.account_id;
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
  }, [selectedAccount, tenantId]);

  const [batchModalOpen, setBatchModalOpen] = useState(false);
  const [batchLoading, setBatchLoading] = useState(false);
  const [batchResults, setBatchResults] = useState<null | { items: Array<{ label: string; success: boolean; account_name?: string; intent_score?: number; intent_stage?: string; error?: string }> }>(null);

  const handleBatchAnalyze = async (lines: string[]) => {
    setBatchLoading(true);
    setBatchResults(null);
    try {
      const companies = lines.map(l => {
        const [company_name, partial_domain] = l.split(",").map(s => s.trim());
        return { company_name, partial_domain: partial_domain || undefined };
      });
      const res = await apiFetch("/batch/analyze", tenantId, {
        method: "POST",
        body: JSON.stringify({ companies }),
      });
      const data = await res.json();
      setBatchResults(data);
      loadAccounts();
    } catch {
      setBatchResults({ items: [{ label: "Error", success: false, error: "Batch request failed" }] });
    } finally {
      setBatchLoading(false);
    }
  };

  return (
    <div className="flex flex-col flex-1 min-w-0">
      {/* Tabs bar - HubSpot style */}
      <div className="flex items-center border-b border-[#DDDDDD] bg-white px-4 py-0 min-h-[48px] mb-0">
        <button className="flex items-center gap-1.5 px-3 py-3 text-[14px] text-[#484848] font-medium border-b-2 border-[#FF5A5F] -mb-px">
          <span>All companies</span>
          <span className="bg-[#FF5A5F] text-white text-[11px] font-bold rounded-[3px] px-[6px] py-[1px] min-w-[18px] text-center">
            {filteredAccounts.length}
          </span>
        </button>
        <div className="flex-1" />
        <div className="flex items-center gap-2">
          <button
            onClick={() => setBatchModalOpen(true)}
            className="flex items-center gap-1.5 border border-[#DDDDDD] text-[#484848] text-[14px] font-medium px-4 py-[7px] rounded-[4px] hover:bg-[#F7F7F7] transition-colors"
          >
            Batch analyze
          </button>
          <button
            onClick={() => setAddModalOpen(true)}
            className="flex items-center gap-1.5 bg-[#FF5A5F] hover:bg-[#e0504a] text-white text-[14px] font-medium px-4 py-[7px] rounded-[4px] transition-colors"
          >
            <Plus className="w-[14px] h-[14px]" />
            Add company
          </button>
        </div>
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
                const rows = [["Name","Domain","Industry","Intent Score","Intent Stage","Runs"]];
                filteredAccounts.forEach(a => rows.push([
                  a.account_name||"", a.domain||"", a.industry||"",
                  String(a.latest_intent_score??""), a.latest_intent_stage||"", String(a.run_count)
                ]));
                const csv = rows.map(r => r.map(v => `"${v.replace(/"/g,'""')}"`).join(",")).join("\n");
                const el = document.createElement("a");
                el.href = URL.createObjectURL(new Blob([csv], {type:"text/csv"}));
                el.download = "companies.csv"; el.click();
              }}
              className="flex items-center gap-1.5 px-3 py-[6px] border border-[#DDDDDD] rounded-[4px] text-[13px] text-[#484848] hover:bg-[#F7F7F7] transition-colors"
            >
              Export CSV
            </button>
            <button
              onClick={async () => {
                const targets = selected.size > 0
                  ? filteredAccounts.filter(a => selected.has(a.account_id))
                  : filteredAccounts;
                if (!confirm(`Push ${targets.length} ${selected.size > 0 ? "selected" : ""} companies to HubSpot?`)) return;
                let ok = 0, fail = 0;
                for (const acc of targets) {
                  try {
                    const d = await pushToHubspot(acc.domain || acc.account_id);
                    d.success ? ok++ : fail++;
                  } catch { fail++; }
                }
                alert(`HubSpot push complete: ${ok} succeeded, ${fail} failed`);
              }}
              className="flex items-center gap-1.5 px-3 py-[6px] bg-[#FF5A5F] hover:bg-[#e0504a] text-white rounded-[4px] text-[13px] font-medium transition-colors"
            >
              Push all to HubSpot
            </button>
          </div>
        </div>
      </div>

      {/* Table - HubSpot style */}
      <div className="flex-1 flex flex-col bg-white overflow-hidden">
        {loading ? (
          <TableSkeleton rows={10} cols={6} />
        ) : filteredAccounts.length === 0 ? (
          <div className="text-center py-16">
            <Building2 className="w-14 h-14 text-[#767676] mx-auto mb-4" />
            <p className="text-[#767676] mb-4">No companies yet</p>
            <button
              onClick={() => setAddModalOpen(true)}
              className="inline-block px-5 py-2.5 bg-[#FF5A5F] text-white text-sm font-medium rounded-[4px] hover:bg-[#e0504a]"
            >
              Add your first company
            </button>
          </div>
        ) : (
          <>
            <div className="flex-1 overflow-x-auto">
              <table className="w-full min-w-[900px]">
                <thead>
                  <tr className="bg-[#F7F7F7] border-y border-[#DDDDDD]">
                    <th className="w-[44px] px-3 py-2.5">
                      <input type="checkbox" checked={allPageSelected} onChange={toggleSelectAll} className="w-[16px] h-[16px] rounded border-[#DDDDDD] accent-[#FF5A5F]" />
                    </th>
                    <th className="text-left px-3 py-2.5 text-[12px] font-semibold text-[#484848] tracking-wide">Company name</th>
                    <th className="text-left px-3 py-2.5 text-[12px] font-semibold text-[#484848] tracking-wide">Domain</th>
                    <th className="text-left px-3 py-2.5 text-[12px] font-semibold text-[#484848] tracking-wide">Industry</th>
                    <th className="text-left px-3 py-2.5 text-[12px] font-semibold text-[#484848] tracking-wide">Intent Score</th>
                    <th className="text-left px-3 py-2.5 text-[12px] font-semibold text-[#484848] tracking-wide">Stage</th>
                    <th className="text-left px-3 py-2.5 text-[12px] font-semibold text-[#484848] tracking-wide">Trend</th>
                    <th className="text-left px-3 py-2.5 text-[12px] font-semibold text-[#484848] tracking-wide">Visits</th>
                    <th className="text-left px-3 py-2.5 text-[12px] font-semibold text-[#484848] tracking-wide">Runs</th>
                    <th className="w-[44px]" />
                  </tr>
                </thead>
                <tbody>
                  {pagedAccounts.map((account) => (
                    <tr
                      key={account.account_id}
                      onClick={() => handleRowClick(account)}
                      className="border-b border-[#DDDDDD] hover:bg-[#F7F7F7] transition-colors cursor-pointer"
                    >
                      <td className="px-3 py-2.5" onClick={(e) => e.stopPropagation()}>
                        <input type="checkbox" checked={selected.has(account.account_id)} onChange={() => toggleSelect(account.account_id)} className="w-[16px] h-[16px] rounded border-[#DDDDDD] accent-[#FF5A5F]" />
                      </td>
                      <td className="px-3 py-2.5">
                        <a href="#" onClick={(e) => { e.preventDefault(); handleRowClick(account); }} className="text-[14px] text-[#0091ae] hover:underline">
                          {account.account_name || account.account_id}
                        </a>
                      </td>
                      <td className="px-3 py-2.5 text-[14px] text-[#484848]">{account.domain || "—"}</td>
                      <td className="px-3 py-2.5 text-[14px] text-[#484848]">{account.industry || "—"}</td>
                      <td className="px-3 py-2.5">
                        <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${
                          (account.latest_intent_score || 0) >= 7
                            ? "bg-emerald-100 text-emerald-700"
                            : (account.latest_intent_score || 0) >= 4
                            ? "bg-amber-100 text-amber-700"
                            : "bg-gray-100 text-[#767676]"
                        }`}>
                          {account.latest_intent_score?.toFixed(1) || "—"}
                        </span>
                      </td>
                      <td className="px-3 py-2.5 text-[14px] text-[#484848]">{account.latest_intent_stage || "—"}</td>
                      <td className="px-3 py-2.5">
                        <span className={`text-sm ${
                          account.intent_direction === "rising" ? "text-emerald-600" :
                          account.intent_direction === "falling" ? "text-red-600" :
                          "text-[#767676]"
                        }`}>
                          {account.intent_direction === "rising" ? "↑" : account.intent_direction === "falling" ? "↓" : "→"}
                        </span>
                      </td>
                      <td className="px-3 py-2.5 text-[14px] text-[#484848]">{account.visit_count_total}</td>
                      <td className="px-3 py-2.5 text-[14px] text-[#484848]">{account.run_count}</td>
                      <td className="px-3 py-2.5" onClick={(e) => e.stopPropagation()}>
                        <button
                          onClick={async () => {
                            const d = await pushToHubspot(account.domain || account.account_id);
                            alert(d.success ? `✓ ${d.action} in HubSpot` : `Failed: ${d.error}`);
                          }}
                          disabled={pushingHs.has(account.domain || account.account_id)}
                          title="Push to HubSpot"
                          className="text-xs text-[#767676] hover:text-[#FF5A5F] px-1.5 py-0.5 rounded border border-transparent hover:border-[#DDDDDD] transition-colors disabled:opacity-40"
                        >
                          {pushingHs.has(account.domain || account.account_id) ? "..." : "HS"}
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            {/* Pagination */}
            <div className="flex items-center justify-center gap-2 py-4 border-t border-[#DDDDDD]">
              <button onClick={() => setPage(p => Math.max(1, p - 1))} disabled={page === 1} className="flex items-center gap-1 text-[14px] text-[#767676] hover:text-[#484848] disabled:opacity-40 transition-colors">Prev</button>
              {Array.from({length: totalPages}, (_, i) => i + 1).map(p => (
                <button key={p} onClick={() => setPage(p)} className={`w-[28px] h-[28px] flex items-center justify-center border rounded-[4px] text-[14px] font-medium transition-colors ${p === page ? "border-[#FF5A5F] text-[#FF5A5F] bg-white" : "border-[#DDDDDD] text-[#484848] bg-white hover:bg-[#F7F7F7]"}`}>{p}</button>
              ))}
              <button onClick={() => setPage(p => Math.min(totalPages, p + 1))} disabled={page === totalPages} className="flex items-center gap-1 text-[14px] text-[#767676] hover:text-[#484848] disabled:opacity-40 transition-colors">Next</button>
              <span className="ml-4 text-[13px] text-[#767676]">{filteredAccounts.length} total · {PAGE_SIZE} per page</span>
            </div>
          </>
        )}
      </div>

      {addModalOpen && (
        <AddCompanyModal
          onClose={() => setAddModalOpen(false)}
          onAdd={handleAdd}
          loading={addLoading}
        />
      )}

      {batchModalOpen && (
        <BatchModal
          onClose={() => { setBatchModalOpen(false); setBatchResults(null); }}
          onSubmit={handleBatchAnalyze}
          loading={batchLoading}
          results={batchResults}
        />
      )}

      <AnalysisPanel
        isOpen={panelOpen}
        onClose={() => { setPanelOpen(false); setSelectedAccount(null); }}
        loading={analysisLoading}
        result={result && !(result as { error?: string }).error ? (result as unknown as Parameters<typeof AnalysisPanel>[0]["result"]) : null}
        error={(result as { error?: string })?.error}
        deepResearch={deepResearch}
        deepLoading={deepLoading}
        onDeepResearch={result && (result as { account_name?: string }).account_name ? handleDeepResearch : undefined}
        onPushHubspot={result && !(result as { error?: string }).error ? handlePushHubspot : undefined}
        tenantId={tenantId}
        apiFetch={apiFetch}
      />
    </div>
  );
}

function AddCompanyModal({ onClose, onAdd, loading }: { onClose: () => void; onAdd: (name: string, domain: string) => void; loading: boolean }) {
  const [name, setName] = useState("");
  const [domain, setDomain] = useState("");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) return;
    onAdd(name.trim(), domain.trim());
  };

  return (
    <>
      <div className="fixed inset-0 bg-black/20 z-40" onClick={onClose} />
      <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
        <div className="bg-white rounded-lg shadow-xl max-w-md w-full p-6" onClick={(e) => e.stopPropagation()}>
          <h2 className="text-lg font-semibold text-[#484848] mb-4">Add Company</h2>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-[#484848] mb-1.5">Company Name *</label>
              <input
                type="text"
                required
                className="w-full border border-[#DDDDDD] rounded-[4px] px-3 py-2 text-[#484848] focus:border-[#FF5A5F] focus:ring-1 focus:ring-[#FF5A5F]/30"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="e.g., Stripe, Notion, Figma"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-[#484848] mb-1.5">Domain (optional)</label>
              <input
                type="text"
                className="w-full border border-[#DDDDDD] rounded-[4px] px-3 py-2 text-[#484848] focus:border-[#FF5A5F] focus:ring-1 focus:ring-[#FF5A5F]/30"
                value={domain}
                onChange={(e) => setDomain(e.target.value)}
                placeholder="stripe.com"
              />
            </div>
            <div className="flex gap-2 pt-4">
              <button
                type="button"
                onClick={onClose}
                disabled={loading}
                className="flex-1 px-4 py-2 border border-[#DDDDDD] text-[#484848] rounded-[4px] hover:bg-[#F7F7F7] disabled:opacity-50"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={loading}
                className="flex-1 px-4 py-2 bg-[#FF5A5F] text-white rounded-[4px] hover:bg-[#e0504a] disabled:opacity-50 flex items-center justify-center gap-2"
              >
                {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : null}
                Add & Analyze
              </button>
            </div>
          </form>
        </div>
      </div>
    </>
  );
}

function BatchModal({ onClose, onSubmit, loading, results }: {
  onClose: () => void;
  onSubmit: (lines: string[]) => void;
  loading: boolean;
  results: null | { items: Array<{ label: string; success: boolean; account_name?: string; intent_score?: number; intent_stage?: string; error?: string }> };
}) {
  const [text, setText] = useState("");
  const lines = text.split("\n").map(l => l.trim()).filter(Boolean);

  return (
    <>
      <div className="fixed inset-0 bg-black/30 z-50" onClick={onClose} />
      <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
        <div className="bg-white rounded-[6px] border border-[#DDDDDD] w-full max-w-lg shadow-xl">
          <div className="px-6 py-4 border-b border-[#DDDDDD]">
            <h2 className="text-base font-semibold text-[#484848]">Batch Analyze Companies</h2>
            <p className="text-xs text-[#767676] mt-0.5">One company per line. Optionally add domain: <span className="font-mono">Acme Corp, acme.com</span></p>
          </div>
          <div className="p-6 space-y-4">
            {!results ? (
              <>
                <textarea
                  value={text}
                  onChange={e => setText(e.target.value)}
                  placeholder={"Apple Inc\nMicrosoft Corporation, microsoft.com\nStripe, stripe.com"}
                  rows={8}
                  className="w-full px-3 py-2 border border-[#DDDDDD] rounded-[4px] text-sm text-[#484848] font-mono resize-none focus:outline-none focus:border-[#FF5A5F]"
                />
                <p className="text-xs text-[#767676]">{lines.length} / 10 companies</p>
                <div className="flex gap-3">
                  <button onClick={onClose} className="flex-1 px-4 py-2 border border-[#DDDDDD] text-[#484848] rounded-[4px] hover:bg-[#F7F7F7]">Cancel</button>
                  <button
                    onClick={() => onSubmit(lines)}
                    disabled={loading || lines.length === 0 || lines.length > 10}
                    className="flex-1 px-4 py-2 bg-[#FF5A5F] text-white rounded-[4px] hover:bg-[#e0504a] disabled:opacity-50 flex items-center justify-center gap-2"
                  >
                    {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : null}
                    {loading ? `Analyzing ${lines.length} companies...` : "Run Batch"}
                  </button>
                </div>
              </>
            ) : (
              <>
                <div className="space-y-2 max-h-80 overflow-y-auto">
                  {results.items.map((item, i) => (
                    <div key={i} className={`flex items-center justify-between p-3 rounded-[4px] border ${item.success ? "border-emerald-200 bg-emerald-50" : "border-red-200 bg-red-50"}`}>
                      <div>
                        <p className="text-sm font-medium text-[#484848]">{item.account_name || item.label}</p>
                        {item.success ? (
                          <p className="text-xs text-[#767676]">Intent: {item.intent_score?.toFixed(1)} · {item.intent_stage}</p>
                        ) : (
                          <p className="text-xs text-red-600">{item.error}</p>
                        )}
                      </div>
                      <span className={`text-xs font-bold px-2 py-0.5 rounded ${item.success ? "bg-emerald-600 text-white" : "bg-red-600 text-white"}`}>
                        {item.success ? "✓" : "✗"}
                      </span>
                    </div>
                  ))}
                </div>
                <button onClick={onClose} className="w-full px-4 py-2 bg-[#FF5A5F] text-white rounded-[4px] hover:bg-[#e0504a]">Done</button>
              </>
            )}
          </div>
        </div>
      </div>
    </>
  );
}
