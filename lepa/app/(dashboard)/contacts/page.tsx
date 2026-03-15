"use client";

import { useState, useEffect, useCallback } from "react";
import { useUser } from "@clerk/nextjs";
import { Search, Users, ExternalLink, Building2, X, Loader2, Mail, Linkedin, Send, CheckSquare, Square } from "lucide-react";
import { useTenantId } from "@/hooks/useTenantId";
import { apiFetch } from "@/lib/api";
import { useApiFetch } from "@/hooks/useApiFetch";
import { Skeleton } from "@/components/Skeleton";

interface Contact {
  id: number;
  name: string;
  title: string;
  role: string;
  source_url: string | null;
  company_name: string;
  company_domain: string;
  source_type: "visitor" | "company";
  linkedin_headline: string | null;
  linkedin_about: string | null;
  linkedin_skills: string[];
  linkedin_location: string | null;
  linkedin_scraped_at: string | null;
  personalized_email: string | null;
  personalized_linkedin_msg: string | null;
  hubspot_contact_id: string | null;
  hubspot_synced_at: string | null;
  created_at: string;
}

const roleColors: Record<string, string> = {
  "Economic Buyer": "bg-[#F7F7F7] text-[#484848] border-[#DDDDDD]",
  "Champion": "bg-emerald-100 text-emerald-700 border-emerald-200",
  "Technical Evaluator": "bg-orange-100 text-orange-700 border-orange-200",
  "Blocker": "bg-red-100 text-red-700 border-red-200",
  "End User": "bg-amber-100 text-amber-700 border-amber-200",
};

export default function ContactsPage() {
  const apiFetch = useApiFetch();
  const tenantId = useTenantId();
  const { user } = useUser();
  const senderName = user ? `${user.firstName ?? ""} ${user.lastName ?? ""}`.trim() : "";
  const [contacts, setContacts] = useState<Contact[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [selected, setSelected] = useState<Set<number>>(new Set());
  const [panelContact, setPanelContact] = useState<Contact | null>(null);
  const [enriching, setEnriching] = useState(false);
  const [pushingBulk, setPushingBulk] = useState(false);
  const [bulkResult, setBulkResult] = useState<string | null>(null);
  const [pushingHs, setPushingHs] = useState<Set<number>>(new Set());

  const loadContacts = useCallback(() => {
    apiFetch("/contacts", tenantId)
      .then((r) => r.json())
      .then((data) => setContacts(data.contacts || []))
      .catch(() => setContacts([]))
      .finally(() => setLoading(false));
  }, [tenantId]);

  useEffect(() => { loadContacts(); }, [loadContacts]);

  const filtered = contacts.filter((c) =>
    [c.name, c.title, c.role, c.company_name].some((f) =>
      f?.toLowerCase().includes(search.toLowerCase())
    )
  );

  const grouped = filtered.reduce<Record<string, Contact[]>>((acc, c) => {
    const key = c.company_name || c.company_domain || "Unknown";
    if (!acc[key]) acc[key] = [];
    acc[key].push(c);
    return acc;
  }, {});

  const toggleSelect = (id: number) => {
    setSelected(prev => {
      const next = new Set(prev);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });
  };

  const handleEnrich = async (contact: Contact) => {
    setEnriching(true);
    try {
      const res = await apiFetch(`/contacts/${contact.id}/enrich`, tenantId, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ sender_name: senderName }),
      });
      const updated = await res.json();
      setContacts(prev => prev.map(c => c.id === updated.id ? updated : c));
      setPanelContact(updated);
    } catch (e) {
      console.error(e);
    } finally {
      setEnriching(false);
    }
  };

  const handlePushHubspot = async (contact: Contact) => {
    setPushingHs(prev => new Set(prev).add(contact.id));
    try {
      const res = await apiFetch(`/contacts/${contact.id}/push-hubspot`, tenantId, { method: "POST" });
      const data = await res.json();
      if (data.success) {
        const updated = { ...contact, hubspot_contact_id: data.hubspot_id, hubspot_synced_at: new Date().toISOString() };
        setContacts(prev => prev.map(c => c.id === contact.id ? updated : c));
        setPanelContact(updated);
      }
    } catch (e) {
      console.error(e);
    } finally {
      setPushingHs(prev => { const s = new Set(prev); s.delete(contact.id); return s; });
    }
  };

  const handleBulkPush = async () => {
    if (selected.size === 0) return;
    setPushingBulk(true);
    setBulkResult(null);
    try {
      const res = await apiFetch("/contacts/bulk-push-hubspot", tenantId, {
        method: "POST",
        body: JSON.stringify({ contact_ids: Array.from(selected) }),
      });
      const data = await res.json();
      setBulkResult(`✓ Pushed ${data.pushed}/${selected.size} contacts to HubSpot`);
      loadContacts();
      setSelected(new Set());
    } catch (e) {
      setBulkResult("Failed to push contacts");
    } finally {
      setPushingBulk(false);
    }
  };

  return (
    <div className="flex flex-col flex-1 min-w-0">
      {/* Header bar */}
      <div className="flex items-center border-b border-[#DDDDDD] bg-white px-4 min-h-[48px]">
        <button className="flex items-center gap-1.5 px-3 py-3 text-[14px] text-[#484848] font-medium border-b-2 border-[#FF5A5F] -mb-px">
          <span>All Contacts</span>
          <span className="bg-[#FF5A5F] text-white text-[11px] font-bold rounded-[3px] px-[6px] py-[1px]">{filtered.length}</span>
        </button>
      </div>

      {/* Toolbar */}
      <div className="bg-white px-4 pt-3 pb-3 border-b border-[#DDDDDD] flex items-center gap-3">
        <div className="flex items-center border border-[#DDDDDD] rounded-[4px] px-3 py-[6px] w-[260px] bg-white">
          <input
            type="text"
            placeholder="Search contacts..."
            className="flex-1 text-[14px] text-[#484848] placeholder-[#767676] outline-none bg-transparent"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
          <Search className="w-[14px] h-[14px] text-[#767676]" />
        </div>

        {selected.size > 0 && (
          <div className="flex items-center gap-2 ml-2">
            <span className="text-sm text-[#767676]">{selected.size} selected</span>
            <button
              onClick={handleBulkPush}
              disabled={pushingBulk}
              className="flex items-center gap-1.5 px-3 py-[6px] bg-[#FF5A5F] hover:bg-[#e0504a] text-white text-sm font-medium rounded-[4px] disabled:opacity-50"
            >
              {pushingBulk ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Send className="w-3.5 h-3.5" />}
              Push to HubSpot
            </button>
            <button onClick={() => setSelected(new Set())} className="text-sm text-[#767676] hover:text-[#484848]">Clear</button>
          </div>
        )}
        {bulkResult && <span className="text-sm text-emerald-600 ml-2">{bulkResult}</span>}
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto bg-[#F7F7F7] p-4">
        {loading ? (
          <div className="space-y-4">
            {Array.from({ length: 3 }).map((_, g) => (
              <div key={g} className="bg-white border border-[#DDDDDD] rounded-[4px] overflow-hidden">
                {/* Group header */}
                <div className="flex items-center gap-3 px-4 py-3 border-b border-[#DDDDDD] bg-[#F7F7F7]">
                  <Skeleton className="h-3 w-32" />
                  <Skeleton className="h-3 w-20" />
                  <div className="flex-1" />
                  <Skeleton className="h-5 w-16 rounded-[3px]" />
                </div>
                {/* Table rows */}
                <table className="w-full">
                  <tbody>
                    {Array.from({ length: g === 0 ? 3 : 2 }).map((_, r) => (
                      <tr key={r} className="border-b border-[#eaf0f6] last:border-0">
                        <td className="px-4 py-3 w-10"><Skeleton className="h-4 w-4" /></td>
                        <td className="px-4 py-3">
                          <div className="flex items-center gap-2">
                            <Skeleton className="w-7 h-7 rounded-full" />
                            <Skeleton className="h-3 w-28" />
                          </div>
                        </td>
                        <td className="px-4 py-3"><Skeleton className="h-3 w-24" /></td>
                        <td className="px-4 py-3"><Skeleton className="h-5 w-16 rounded-[3px]" /></td>
                        <td className="px-4 py-3"><Skeleton className="h-3 w-12" /></td>
                        <td className="px-4 py-3"><Skeleton className="h-3 w-10" /></td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ))}
          </div>
        ) : filtered.length === 0 ? (
          <div className="text-center py-16">
            <Users className="w-14 h-14 text-[#767676] mx-auto mb-4" />
            <p className="text-[#767676] mb-2">No contacts yet</p>
            <p className="text-sm text-[#767676]">Run analysis on visitors or companies to discover buying committee members</p>
          </div>
        ) : (
          <div className="space-y-4">
            {Object.entries(grouped).map(([company, members]) => (
              <div key={company} className="bg-white border border-[#DDDDDD] rounded-[4px] overflow-hidden">
                <div className="flex items-center gap-3 px-4 py-3 border-b border-[#DDDDDD] bg-[#F7F7F7]">
                  <Building2 className="w-4 h-4 text-[#767676] shrink-0" />
                  <span className="text-sm font-semibold text-[#484848]">{company}</span>
                  {members[0]?.company_domain && <span className="text-xs text-[#767676]">{members[0].company_domain}</span>}
                  <div className="flex-1" />
                  <span className="text-xs text-[#767676]">{members[0]?.source_type === "visitor" ? "👤 Visitor" : "🏢 Company"} analysis</span>
                  <span className="text-xs bg-[#DDDDDD] text-[#484848] px-2 py-0.5 rounded-[3px]">{members.length} contact{members.length !== 1 ? "s" : ""}</span>
                </div>

                <table className="w-full">
                  <thead>
                    <tr className="border-b border-[#DDDDDD]">
                      <th className="w-10 px-4 py-2" />
                      <th className="text-left px-4 py-2 text-[11px] font-semibold text-[#767676] uppercase tracking-wide">Name</th>
                      <th className="text-left px-4 py-2 text-[11px] font-semibold text-[#767676] uppercase tracking-wide">Title</th>
                      <th className="text-left px-4 py-2 text-[11px] font-semibold text-[#767676] uppercase tracking-wide">Role</th>
                      <th className="text-left px-4 py-2 text-[11px] font-semibold text-[#767676] uppercase tracking-wide">HubSpot</th>
                      <th className="text-left px-4 py-2 text-[11px] font-semibold text-[#767676] uppercase tracking-wide">LinkedIn</th>
                    </tr>
                  </thead>
                  <tbody>
                    {members.map((contact) => (
                      <tr
                        key={contact.id}
                        onClick={() => setPanelContact(contact)}
                        className="border-b border-[#DDDDDD] last:border-0 hover:bg-[#F7F7F7] transition-colors cursor-pointer"
                      >
                        <td className="px-4 py-3" onClick={(e) => { e.stopPropagation(); toggleSelect(contact.id); }}>
                          {selected.has(contact.id)
                            ? <CheckSquare className="w-4 h-4 text-[#FF5A5F]" />
                            : <Square className="w-4 h-4 text-[#DDDDDD]" />}
                        </td>
                        <td className="px-4 py-3">
                          <div className="flex items-center gap-2">
                            <div className="w-7 h-7 rounded-full bg-[#DDDDDD] flex items-center justify-center text-[#484848] text-xs font-bold shrink-0">
                              {contact.name.charAt(0).toUpperCase()}
                            </div>
                            <span className="text-sm font-medium text-[#484848]">{contact.name}</span>
                          </div>
                        </td>
                        <td className="px-4 py-3 text-sm text-[#767676]">{contact.title || "—"}</td>
                        <td className="px-4 py-3">
                          <span className={`text-xs font-medium px-2 py-0.5 rounded-[3px] border ${roleColors[contact.role] || "bg-gray-100 text-gray-600 border-gray-200"}`}>
                            {contact.role || "—"}
                          </span>
                        </td>
                        <td className="px-4 py-3">
                          {contact.hubspot_contact_id
                            ? <span className="text-xs text-emerald-600 font-medium">✓ Synced</span>
                            : <span className="text-xs text-[#767676]">—</span>}
                        </td>
                        <td className="px-4 py-3" onClick={(e) => e.stopPropagation()}>
                          {contact.source_url
                            ? <a href={contact.source_url} target="_blank" rel="noopener noreferrer" className="flex items-center gap-1 text-xs text-[#0091ae] hover:underline"><ExternalLink className="w-3 h-3" />View</a>
                            : <span className="text-xs text-[#767676]">—</span>}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Right panel */}
      {panelContact && (
        <ContactPanel
          contact={panelContact}
          onClose={() => setPanelContact(null)}
          onEnrich={() => handleEnrich(panelContact)}
          onPushHubspot={() => handlePushHubspot(panelContact)}
          enriching={enriching}
          pushingHs={pushingHs.has(panelContact.id)}
        />
      )}
    </div>
  );
}

function ContactPanel({ contact, onClose, onEnrich, onPushHubspot, enriching, pushingHs }: {
  contact: Contact;
  onClose: () => void;
  onEnrich: () => void;
  onPushHubspot: () => void;
  enriching: boolean;
  pushingHs: boolean;
}) {
  const hasLinkedIn = !!contact.linkedin_scraped_at;

  return (
    <>
      <div className="fixed inset-0 bg-black/20 z-40" onClick={onClose} />
      <aside className="fixed top-0 right-0 h-full w-full max-w-lg bg-white border-l border-[#DDDDDD] shadow-xl z-50 flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-[#DDDDDD] shrink-0">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-full bg-[#DDDDDD] flex items-center justify-center text-[#484848] font-bold">
              {contact.name.charAt(0).toUpperCase()}
            </div>
            <div>
              <h2 className="text-base font-semibold text-[#484848]">{contact.name}</h2>
              <p className="text-sm text-[#767676]">{contact.title} · {contact.company_name}</p>
            </div>
          </div>
          <button onClick={onClose} className="p-2 text-[#767676] hover:bg-[#F7F7F7] rounded-[4px]">
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {/* Quick info */}
          <div className="grid grid-cols-2 gap-3">
            <div className="p-3 bg-[#F7F7F7] border border-[#DDDDDD] rounded-[4px]">
              <p className="text-xs text-[#767676] uppercase mb-1">Role</p>
              <span className={`text-xs font-medium px-2 py-0.5 rounded-[3px] border ${roleColors[contact.role] || "bg-gray-100 text-gray-600 border-gray-200"}`}>
                {contact.role || "—"}
              </span>
            </div>
            <div className="p-3 bg-[#F7F7F7] border border-[#DDDDDD] rounded-[4px]">
              <p className="text-xs text-[#767676] uppercase mb-1">Company</p>
              <p className="text-sm font-medium text-[#484848]">{contact.company_name}</p>
            </div>
            {contact.linkedin_location && (
              <div className="p-3 bg-[#F7F7F7] border border-[#DDDDDD] rounded-[4px]">
                <p className="text-xs text-[#767676] uppercase mb-1">Location</p>
                <p className="text-sm text-[#484848]">{contact.linkedin_location}</p>
              </div>
            )}
            {contact.source_url && (
              <div className="p-3 bg-[#F7F7F7] border border-[#DDDDDD] rounded-[4px]">
                <p className="text-xs text-[#767676] uppercase mb-1">LinkedIn</p>
                <a href={contact.source_url} target="_blank" rel="noopener noreferrer"
                  className="flex items-center gap-1 text-sm text-[#0091ae] hover:underline">
                  <Linkedin className="w-3.5 h-3.5" />View Profile
                </a>
              </div>
            )}
          </div>

          {/* LinkedIn insights */}
          {hasLinkedIn ? (
            <div className="space-y-3">
              {contact.linkedin_headline && (
                <div>
                  <p className="text-xs font-medium text-[#767676] uppercase mb-1">Headline</p>
                  <p className="text-sm text-[#484848]">{contact.linkedin_headline}</p>
                </div>
              )}
              {contact.linkedin_about && (
                <div>
                  <p className="text-xs font-medium text-[#767676] uppercase mb-1">About</p>
                  <p className="text-sm text-[#484848] leading-relaxed">{contact.linkedin_about.slice(0, 400)}{contact.linkedin_about.length > 400 ? "..." : ""}</p>
                </div>
              )}
              {contact.linkedin_skills && contact.linkedin_skills.length > 0 && (
                <div>
                  <p className="text-xs font-medium text-[#767676] uppercase mb-2">Skills</p>
                  <div className="flex flex-wrap gap-1.5">
                    {contact.linkedin_skills.map((s, i) => (
                      <span key={i} className="text-xs bg-[#F7F7F7] border border-[#DDDDDD] text-[#484848] px-2 py-0.5 rounded-[3px]">{s}</span>
                    ))}
                  </div>
                </div>
              )}
            </div>
          ) : (
            <div className="p-4 bg-[#F7F7F7] border border-[#DDDDDD] rounded-[4px] text-center">
              <p className="text-sm text-[#767676] mb-3">Generate personalized outreach for this contact</p>
              <button
                onClick={onEnrich}
                disabled={enriching}
                className="flex items-center gap-2 px-4 py-2 bg-[#FF5A5F] hover:bg-[#e0504a] text-white text-sm font-medium rounded-[4px] mx-auto disabled:opacity-50"
              >
                {enriching ? <Loader2 className="w-4 h-4 animate-spin" /> : <Mail className="w-4 h-4" />}
                {enriching ? "Generating..." : "Generate Outreach"}
              </button>
            </div>
          )}

          {/* Personalized outreach */}
          {(contact.personalized_email || contact.personalized_linkedin_msg) && (
            <div className="space-y-4">
              {contact.personalized_email && (
                <div>
                  <div className="flex items-center gap-2 mb-2">
                    <Mail className="w-4 h-4 text-[#767676]" />
                    <p className="text-xs font-medium text-[#767676] uppercase">Personalized Email</p>
                  </div>
                  <div className="p-3 bg-[#F7F7F7] border border-[#DDDDDD] rounded-[4px]">
                    <pre className="text-sm text-[#484848] whitespace-pre-wrap font-sans leading-relaxed">{contact.personalized_email}</pre>
                  </div>
                </div>
              )}
              {contact.personalized_linkedin_msg && (
                <div>
                  <div className="flex items-center gap-2 mb-2">
                    <Linkedin className="w-4 h-4 text-[#767676]" />
                    <p className="text-xs font-medium text-[#767676] uppercase">LinkedIn Message</p>
                  </div>
                  <div className="p-3 bg-[#F7F7F7] border border-[#DDDDDD] rounded-[4px]">
                    <p className="text-sm text-[#484848] leading-relaxed">{contact.personalized_linkedin_msg}</p>
                  </div>
                  {contact.source_url && (
                    <a
                      href={contact.source_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="mt-2 flex items-center gap-2 px-4 py-2 bg-[#0077b5] hover:bg-[#006097] text-white text-sm font-medium rounded-[4px] w-fit"
                    >
                      <Linkedin className="w-4 h-4" />
                      Open LinkedIn to Send
                    </a>
                  )}
                </div>
              )}
            </div>
          )}

          {/* Re-generate outreach */}
          {hasLinkedIn && (
            <button
              onClick={onEnrich}
              disabled={enriching}
              className="flex items-center gap-2 text-sm text-[#767676] hover:text-[#484848] disabled:opacity-50"
            >
              {enriching ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : null}
              {enriching ? "Generating..." : "↻ Regenerate Outreach"}
            </button>
          )}
        </div>

        {/* Footer actions */}
        <div className="px-6 py-4 border-t border-[#DDDDDD] flex items-center gap-3 shrink-0">
          <button
            onClick={onPushHubspot}
            disabled={pushingHs}
            className="flex items-center gap-2 px-4 py-2 bg-[#FF5A5F] hover:bg-[#e0504a] disabled:opacity-50 text-white text-sm font-medium rounded-[4px]"
          >
            {pushingHs ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
            {pushingHs ? "Syncing..." : contact.hubspot_contact_id ? "Re-sync to HubSpot" : "Push to HubSpot"}
          </button>
          {contact.hubspot_contact_id && (
            <span className="text-xs text-emerald-600">✓ Synced {contact.hubspot_synced_at ? new Date(contact.hubspot_synced_at).toLocaleDateString() : ""}</span>
          )}
        </div>
      </aside>
    </>
  );
}
