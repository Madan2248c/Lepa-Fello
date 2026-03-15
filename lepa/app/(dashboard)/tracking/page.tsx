"use client";

import { useEffect, useState, useCallback } from "react";
import { Copy, Plus, RefreshCw, Loader2 } from "lucide-react";
import { useTenantId } from "@/hooks/useTenantId";
import { apiFetch } from "@/lib/api";
import { useApiFetch } from "@/hooks/useApiFetch";

const BACKEND = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface TrackerKey { api_key: string; label: string; active: boolean; created_at: string; }
interface TrackedVisitor {
  vid: string; ip_address: string; user_agent: string;
  visit_count: number; last_seen_at: string;
  event_count: number; total_active_ms: number; pages: string[];
}

export default function TrackingPage() {
  const apiFetch = useApiFetch();
  const tenantId = useTenantId();
  const [keys, setKeys] = useState<TrackerKey[]>([]);
  const [visitors, setVisitors] = useState<TrackedVisitor[]>([]);
  const [loadingKey, setLoadingKey] = useState(false);
  const [loadingVisitors, setLoadingVisitors] = useState(true);
  const [copied, setCopied] = useState(false);
  const [copiedKey, setCopiedKey] = useState(false);
  const [saved, setSaved] = useState<Set<string>>(new Set());

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

  useEffect(() => { loadKeys(); loadVisitors(); }, [loadKeys, loadVisitors]);

  const handleCreateKey = async () => {
    setLoadingKey(true);
    try { await apiFetch("/tracker-keys", tenantId, { method: "POST" }); await loadKeys(); }
    finally { setLoadingKey(false); }
  };

  const TRACKER_ORIGIN = "https://d3a0jits88oyj6.cloudfront.net";
  const snippet = activeKey
    ? `<script async src="${TRACKER_ORIGIN}/tracker.js?key=${activeKey}&endpoint=${BACKEND}"></script>`
    : "";

  const copySnippet = () => { navigator.clipboard.writeText(snippet); setCopied(true); setTimeout(() => setCopied(false), 2000); };
  const copyKey = () => { navigator.clipboard.writeText(activeKey); setCopiedKey(true); setTimeout(() => setCopiedKey(false), 2000); };

  const saveToVisitors = async (v: TrackedVisitor) => {
    await apiFetch("/analyze/visitors", tenantId, {
      method: "POST",
      body: JSON.stringify({
        visitor_id: v.vid, ip_address: v.ip_address,
        pages_visited: v.pages.join(", "),
        time_on_site_seconds: Math.round(v.total_active_ms / 1000),
        visits_this_week: v.visit_count, referral_source: "",
      }),
    });
    setSaved(prev => new Set(prev).add(v.vid));
  };

  return (
    <div className="flex flex-col flex-1 min-w-0 h-full">
      {/* Page header */}
      <div className="flex items-center justify-between px-6 py-4 border-b border-[#DDDDDD] bg-white shrink-0">
        <div>
          <h1 className="text-[18px] font-semibold text-[#484848]">Tracking</h1>
          <p className="text-[13px] text-[#767676] mt-0.5">Embed the script on any website to capture visitor intelligence</p>
        </div>
        {!activeKey ? (
          <button
            onClick={handleCreateKey}
            disabled={loadingKey}
            className="flex items-center gap-1.5 bg-[#FF5A5F] hover:bg-[#e0504a] text-white text-[13px] font-medium px-4 py-2 rounded-[4px] disabled:opacity-50"
          >
            {loadingKey ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Plus className="w-3.5 h-3.5" />}
            Generate Key
          </button>
        ) : (
          <button onClick={loadVisitors} className="flex items-center gap-1.5 text-[13px] text-[#767676] hover:text-[#484848] border border-[#DDDDDD] px-3 py-2 rounded-[4px] hover:bg-[#F7F7F7]">
            <RefreshCw className={`w-3.5 h-3.5 ${loadingVisitors ? "animate-spin" : ""}`} />
            Refresh
          </button>
        )}
      </div>

      {/* Setup strip — only shown when key exists */}
      {activeKey && (
        <div className="flex gap-0 border-b border-[#DDDDDD] bg-white shrink-0">
          {/* API Key */}
          <div className="flex-1 px-6 py-4 border-r border-[#DDDDDD]">
            <p className="text-[11px] font-semibold text-[#767676] uppercase tracking-wide mb-2">API Key</p>
            <div className="flex items-center gap-2 bg-[#F7F7F7] border border-[#DDDDDD] rounded-[4px] px-3 py-2">
              <code className="flex-1 text-[12px] font-mono text-[#484848] truncate">{activeKey}</code>
              <button onClick={copyKey} className="text-[#767676] hover:text-[#484848] shrink-0" title="Copy key">
                {copiedKey ? <span className="text-[11px] text-green-600">✓</span> : <Copy className="w-3.5 h-3.5" />}
              </button>
            </div>
          </div>
          {/* Embed snippet */}
          <div className="flex-[2] px-6 py-4">
            <div className="flex items-center justify-between mb-2">
              <p className="text-[11px] font-semibold text-[#767676] uppercase tracking-wide">Embed Snippet</p>
              <button onClick={copySnippet} className="flex items-center gap-1 text-[12px] text-[#767676] hover:text-[#484848]">
                <Copy className="w-3 h-3" />
                {copied ? "Copied!" : "Copy"}
              </button>
            </div>
            <pre className="bg-[#1c1d20] text-[#e8e9ea] text-[11px] font-mono rounded-[4px] px-3 py-2 overflow-x-auto whitespace-pre-wrap break-all leading-relaxed">
              {snippet}
            </pre>
          </div>
        </div>
      )}

      {/* Visitors table — fills remaining space */}
      <div className="flex flex-col flex-1 overflow-hidden bg-white">
        <div className="flex items-center justify-between px-6 py-3 border-b border-[#DDDDDD] shrink-0">
          <span className="text-[13px] font-semibold text-[#484848]">
            Live Visitors
            <span className="ml-2 bg-[#FF5A5F] text-white text-[10px] font-bold rounded-[3px] px-[5px] py-[1px]">{visitors.length}</span>
          </span>
        </div>

        {loadingVisitors ? (
          <div className="flex items-center justify-center flex-1">
            <Loader2 className="w-5 h-5 animate-spin text-[#767676]" />
          </div>
        ) : visitors.length === 0 ? (
          <div className="flex flex-col items-center justify-center flex-1 text-center">
            <p className="text-[14px] text-[#484848] font-medium mb-1">No visitors yet</p>
            <p className="text-[13px] text-[#767676]">Embed the snippet on a website to start tracking.</p>
          </div>
        ) : (
          <div className="overflow-y-auto flex-1">
            <table className="w-full text-[13px]">
              <thead className="sticky top-0 bg-[#F7F7F7] z-10">
                <tr className="border-b border-[#DDDDDD]">
                  {["IP Address", "Pages", "Time on Site", "Visits", "Last Seen", ""].map(h => (
                    <th key={h} className="text-left px-4 py-2.5 text-[11px] font-semibold text-[#767676] uppercase tracking-wide">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {visitors.map((v) => (
                  <tr key={v.vid} className="border-b border-[#DDDDDD] hover:bg-[#F7F7F7]">
                    <td className="px-4 py-3 font-mono text-[#484848]">{v.ip_address || "—"}</td>
                    <td className="px-4 py-3 text-[#767676] max-w-[220px]">
                      <div className="truncate" title={v.pages.join(", ")}>
                        {v.pages.length > 0 ? v.pages[0] : "—"}
                        {v.pages.length > 1 && <span className="ml-1 text-[11px]">+{v.pages.length - 1}</span>}
                      </div>
                    </td>
                    <td className="px-4 py-3 text-[#484848]">{v.total_active_ms > 0 ? `${Math.round(v.total_active_ms / 1000)}s` : "—"}</td>
                    <td className="px-4 py-3 text-[#484848]">{v.visit_count}</td>
                    <td className="px-4 py-3 text-[#767676]">{new Date(v.last_seen_at).toLocaleString()}</td>
                    <td className="px-4 py-3">
                      <button
                        onClick={() => saveToVisitors(v)}
                        disabled={saved.has(v.vid)}
                        className="text-[12px] px-2.5 py-1 rounded-[3px] border border-[#DDDDDD] text-[#484848] hover:bg-[#F7F7F7] disabled:opacity-40 disabled:cursor-default whitespace-nowrap"
                      >
                        {saved.has(v.vid) ? "✓ Saved" : "Save to Visitors"}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
