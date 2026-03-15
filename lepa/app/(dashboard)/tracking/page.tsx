"use client";

import { useEffect, useState, useCallback } from "react";
import { Copy, Plus, RefreshCw, Loader2 } from "lucide-react";
import { useTenantId } from "@/hooks/useTenantId";
import { apiFetch } from "@/lib/api";

const BACKEND = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000";

interface TrackerKey { api_key: string; label: string; active: boolean; created_at: string; }
interface TrackedVisitor {
  vid: string; ip_address: string; user_agent: string;
  visit_count: number; last_seen_at: string;
  event_count: number; total_active_ms: number; pages: string[];
}

export default function TrackingPage() {
  const tenantId = useTenantId();
  const [keys, setKeys] = useState<TrackerKey[]>([]);
  const [visitors, setVisitors] = useState<TrackedVisitor[]>([]);
  const [loadingKey, setLoadingKey] = useState(false);
  const [loadingVisitors, setLoadingVisitors] = useState(true);
  const [copied, setCopied] = useState(false);

  const activeKey = keys[0]?.api_key;

  const loadKeys = useCallback(async () => {
    if (!tenantId) return;
    const res = await apiFetch("/tracker-keys", tenantId);
    const data = await res.json();
    setKeys(data.keys || []);
  }, [tenantId]);

  const loadVisitors = useCallback(async () => {
    if (!tenantId) return;
    setLoadingVisitors(true);
    try {
      const res = await apiFetch("/track/visitors", tenantId);
      const data = await res.json();
      setVisitors(data.visitors || []);
    } finally {
      setLoadingVisitors(false);
    }
  }, [tenantId]);

  useEffect(() => {
    loadKeys();
    loadVisitors();
  }, [loadKeys, loadVisitors]);

  const handleCreateKey = async () => {
    setLoadingKey(true);
    try {
      await apiFetch("/tracker-keys", tenantId, { method: "POST" });
      await loadKeys();
    } finally {
      setLoadingKey(false);
    }
  };

  const TRACKER_ORIGIN = typeof window !== "undefined" ? window.location.origin : "http://localhost:3000";
  const snippet = activeKey
    ? `<script async src="${TRACKER_ORIGIN}/tracker.js?key=${activeKey}&endpoint=${BACKEND}"></script>`
    : "";

  const copySnippet = () => {
    navigator.clipboard.writeText(snippet);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const [saved, setSaved] = useState<Set<string>>(new Set());

  const saveToVisitors = async (v: TrackedVisitor) => {
    await apiFetch("/analyze/visitors", tenantId, {
      method: "POST",
      body: JSON.stringify({
        visitor_id: v.vid,
        ip_address: v.ip_address,
        pages_visited: v.pages.join(", "),
        time_on_site_seconds: Math.round(v.total_active_ms / 1000),
        visits_this_week: v.visit_count,
        referral_source: "",
      }),
    });
    setSaved(prev => new Set(prev).add(v.vid));
  };

  return (
    <div className="flex flex-col flex-1 min-w-0 bg-[#f5f8fa]">
      {/* Header */}
      <div className="flex items-center border-b border-[#cbd6e2] bg-white px-6 py-0 min-h-[48px]">
        <span className="text-[14px] font-medium text-[#33475b] border-b-2 border-[#ff7a59] py-3 -mb-px">
          Tracking Setup
        </span>
      </div>

      <div className="p-6 space-y-6 max-w-3xl">
        {/* API Key section */}
        <div className="bg-white border border-[#cbd6e2] rounded-[6px] p-5">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h2 className="text-[15px] font-semibold text-[#33475b]">Your Tracking Key</h2>
              <p className="text-xs text-[#516f90] mt-0.5">Embed this key in your client's website to start capturing visitors automatically.</p>
            </div>
            {!activeKey && (
              <button
                onClick={handleCreateKey}
                disabled={loadingKey}
                className="flex items-center gap-1.5 bg-[#ff7a59] hover:bg-[#ff5c35] text-white text-[13px] font-medium px-4 py-[7px] rounded-[4px] disabled:opacity-50"
              >
                {loadingKey ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Plus className="w-3.5 h-3.5" />}
                Generate Key
              </button>
            )}
          </div>

          {activeKey ? (
            <div className="flex items-center gap-2 bg-[#f5f8fa] border border-[#cbd6e2] rounded-[4px] px-3 py-2">
              <code className="flex-1 text-[13px] font-mono text-[#33475b] break-all">{activeKey}</code>
              <button
                onClick={() => { navigator.clipboard.writeText(activeKey); }}
                className="text-[#516f90] hover:text-[#33475b] shrink-0"
                title="Copy key"
              >
                <Copy className="w-4 h-4" />
              </button>
            </div>
          ) : (
            <p className="text-sm text-[#516f90]">No key yet — generate one above.</p>
          )}
        </div>

        {/* Embed snippet */}
        {activeKey && (
          <div className="bg-white border border-[#cbd6e2] rounded-[6px] p-5">
            <div className="flex items-center justify-between mb-3">
              <h2 className="text-[15px] font-semibold text-[#33475b]">Embed Snippet</h2>
              <button
                onClick={copySnippet}
                className="flex items-center gap-1.5 text-[13px] text-[#516f90] hover:text-[#33475b] border border-[#cbd6e2] px-3 py-1.5 rounded-[4px] hover:bg-[#f5f8fa]"
              >
                <Copy className="w-3.5 h-3.5" />
                {copied ? "Copied!" : "Copy"}
              </button>
            </div>
            <p className="text-xs text-[#516f90] mb-3">
              Paste this inside the <code className="bg-[#f5f8fa] px-1 rounded">&lt;head&gt;</code> of your client's website. Works on any site — React, Next.js, plain HTML.
            </p>
            <pre className="bg-[#1c1d20] text-[#e8e9ea] text-[12px] font-mono rounded-[4px] p-4 overflow-x-auto whitespace-pre-wrap break-all">
              {snippet}
            </pre>
            <p className="text-xs text-[#516f90] mt-3">
              The script is <strong>async</strong> — it won't block page rendering. Tracks page views, time on page, and SPA navigation automatically.
            </p>
          </div>
        )}

        {/* Live visitors table */}
        <div className="bg-white border border-[#cbd6e2] rounded-[6px]">
          <div className="flex items-center justify-between px-5 py-4 border-b border-[#cbd6e2]">
            <h2 className="text-[15px] font-semibold text-[#33475b]">
              Live Visitors
              <span className="ml-2 bg-[#ff7a59] text-white text-[11px] font-bold rounded-[3px] px-[6px] py-[1px]">
                {visitors.length}
              </span>
            </h2>
            <button onClick={loadVisitors} className="text-[#516f90] hover:text-[#33475b]" title="Refresh">
              <RefreshCw className={`w-4 h-4 ${loadingVisitors ? "animate-spin" : ""}`} />
            </button>
          </div>

          {loadingVisitors ? (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="w-5 h-5 animate-spin text-[#516f90]" />
            </div>
          ) : visitors.length === 0 ? (
            <div className="py-12 text-center text-sm text-[#516f90]">
              No visitors yet. Embed the snippet on a website to start tracking.
            </div>
          ) : (
            <table className="w-full text-[13px]">
              <thead>
                <tr className="border-b border-[#cbd6e2] bg-[#f5f8fa]">
                  {["IP Address", "Pages", "Time on Site", "Visits", "Last Seen", ""].map(h => (
                    <th key={h} className="text-left px-4 py-2.5 text-[11px] font-semibold text-[#516f90] uppercase tracking-wide">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {visitors.map((v) => (
                  <tr key={v.vid} className="border-b border-[#eaf0f6] hover:bg-[#f5f8fa]">
                    <td className="px-4 py-3 font-mono text-[#33475b]">{v.ip_address || "—"}</td>
                    <td className="px-4 py-3 text-[#516f90] max-w-[200px]">
                      <div className="truncate" title={v.pages.join(", ")}>
                        {v.pages.length > 0 ? v.pages[0] : "—"}
                        {v.pages.length > 1 && <span className="ml-1 text-[11px] text-[#7c98b6]">+{v.pages.length - 1}</span>}
                      </div>
                    </td>
                    <td className="px-4 py-3 text-[#33475b]">
                      {v.total_active_ms > 0 ? `${Math.round(v.total_active_ms / 1000)}s` : "—"}
                    </td>
                    <td className="px-4 py-3 text-[#33475b]">{v.visit_count}</td>
                    <td className="px-4 py-3 text-[#516f90]">
                      {new Date(v.last_seen_at).toLocaleString()}
                    </td>
                    <td className="px-4 py-3">
                      <button
                        onClick={() => saveToVisitors(v)}
                        disabled={saved.has(v.vid)}
                        className="text-[12px] px-2.5 py-1 rounded-[3px] border border-[#cbd6e2] text-[#33475b] hover:bg-[#f5f8fa] disabled:opacity-40 disabled:cursor-default whitespace-nowrap"
                      >
                        {saved.has(v.vid) ? "✓ Saved" : "Save to Visitors"}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </div>
  );
}
