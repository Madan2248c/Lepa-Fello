"use client";

import { useState, useEffect, useRef } from "react";
import { Search, Bell, MessageSquare, Building2, Contact } from "lucide-react";
import { UserButton } from "@clerk/nextjs";
import { useRouter } from "next/navigation";
import { useTenantId } from "@/hooks/useTenantId";
import { apiFetch } from "@/lib/api";

interface Result {
  type: "account" | "contact";
  id: string;
  label: string;
  sub: string;
}

function GlobalSearch() {
  const tenantId = useTenantId();
  const router = useRouter();
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<Result[]>([]);
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (!ref.current?.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  useEffect(() => {
    if (!query.trim() || !tenantId) { setResults([]); return; }
    const t = setTimeout(async () => {
      try {
        const [accRes, conRes] = await Promise.all([
          apiFetch(`/accounts?search=${encodeURIComponent(query)}&limit=5`, tenantId),
          apiFetch(`/contacts?search=${encodeURIComponent(query)}&limit=5`, tenantId),
        ]);
        const accounts = (await accRes.json()).accounts || [];
        const contacts = (await conRes.json()).contacts || [];
        setResults([
          ...accounts.map((a: { account_id: string; account_name: string; domain: string }) => ({
            type: "account" as const,
            id: a.account_id,
            label: a.account_name || a.domain,
            sub: a.domain || "",
          })),
          ...contacts.map((c: { id: string; name: string; title: string; company_name: string }) => ({
            type: "contact" as const,
            id: c.id,
            label: c.name,
            sub: `${c.title || ""} · ${c.company_name || ""}`.replace(/^·\s*/, ""),
          })),
        ]);
        setOpen(true);
      } catch {}
    }, 250);
    return () => clearTimeout(t);
  }, [query, tenantId]);

  const go = (r: Result) => {
    setQuery(""); setOpen(false);
    router.push(r.type === "account" ? "/companies" : "/contacts");
  };

  return (
    <div ref={ref} className="relative w-[340px]">
      <div className="flex items-center bg-[#F7F7F7] rounded-[4px] border border-[#DDDDDD] px-3 py-[6px] focus-within:border-[#767676]">
        <Search className="w-[14px] h-[14px] text-[#767676] mr-2 flex-shrink-0" />
        <input
          value={query}
          onChange={e => setQuery(e.target.value)}
          onFocus={() => results.length && setOpen(true)}
          placeholder="Search companies, contacts..."
          className="bg-transparent text-[14px] text-[#484848] placeholder-[#767676] outline-none w-full"
        />
      </div>
      {open && results.length > 0 && (
        <div className="absolute top-full mt-1 left-0 w-full bg-white border border-[#DDDDDD] rounded-[4px] shadow-lg z-50 overflow-hidden">
          {results.map(r => (
            <button
              key={`${r.type}-${r.id}`}
              onClick={() => go(r)}
              className="w-full flex items-center gap-3 px-3 py-2.5 hover:bg-[#F7F7F7] text-left"
            >
              {r.type === "account"
                ? <Building2 className="w-3.5 h-3.5 text-[#767676] shrink-0" />
                : <Contact className="w-3.5 h-3.5 text-[#767676] shrink-0" />}
              <div className="min-w-0">
                <p className="text-[13px] font-medium text-[#484848] truncate">{r.label}</p>
                <p className="text-[11px] text-[#767676] truncate">{r.sub}</p>
              </div>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

export default function Header({
  onToggleAssistant,
  assistantOpen,
}: {
  onToggleAssistant?: () => void;
  assistantOpen?: boolean;
}) {
  return (
    <header className="h-[52px] min-h-[52px] bg-white border-b border-[#DDDDDD] flex items-center px-4 gap-3 shrink-0">
      <GlobalSearch />
      <div className="flex-1" />
      <div className="flex items-center gap-1">
        {onToggleAssistant && (
          <button
            onClick={onToggleAssistant}
            className={`flex items-center gap-1.5 px-3 h-[32px] rounded-[4px] text-[13px] font-medium transition-colors ${
              assistantOpen
                ? "bg-[#484848] text-white"
                : "text-[#767676] hover:bg-[#F7F7F7] border border-[#DDDDDD]"
            }`}
          >
            <MessageSquare className="w-[14px] h-[14px]" />
            Ask LEPA
          </button>
        )}
        <div className="w-px h-[24px] bg-[#DDDDDD] mx-1" />
        <UserButton appearance={{ elements: { avatarBox: "w-8 h-8" } }} />
      </div>
    </header>
  );
}
