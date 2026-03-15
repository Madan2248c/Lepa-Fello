"use client";

import { useState, useEffect } from "react";
import { Save, Settings as SettingsIcon, User, Plus, X, Briefcase } from "lucide-react";
import { useUser } from "@clerk/nextjs";
import { useTenantId } from "@/hooks/useTenantId";
import { apiFetch } from "@/lib/api";

interface ICPProfile {
  target_industries: string[];
  target_locations: string[];
  target_company_sizes: string[];
  target_roles: string[];
}

interface BusinessProfile {
  business_name: string;
  business_description: string;
  product_service: string;
  value_proposition: string;
}

export default function SettingsPage() {
  const { user } = useUser();
  const tenantId = useTenantId();
  const [icp, setIcp] = useState<ICPProfile>({
    target_industries: [],
    target_locations: [],
    target_company_sizes: [],
    target_roles: []
  });
  const [business, setBusiness] = useState<BusinessProfile>({
    business_name: "",
    business_description: "",
    product_service: "",
    value_proposition: "",
  });
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [savingBusiness, setSavingBusiness] = useState(false);
  const [savedBusiness, setSavedBusiness] = useState(false);

  useEffect(() => {
    apiFetch("/icp", tenantId)
      .then((res) => res.ok ? res.json() : null)
      .then((data) => { if (data?.profile) setIcp(data.profile); })
      .catch(() => {});

    apiFetch("/business-profile", tenantId)
      .then((res) => res.ok ? res.json() : null)
      .then((data) => { if (data?.profile) setBusiness(data.profile); })
      .catch(() => {});
  }, [tenantId]);

  const addItem = (field: keyof ICPProfile, value: string) => {
    if (value.trim() && !icp[field].includes(value.trim())) {
      setIcp(prev => ({ ...prev, [field]: [...prev[field], value.trim()] }));
    }
  };

  const removeItem = (field: keyof ICPProfile, index: number) => {
    setIcp(prev => ({ ...prev, [field]: prev[field].filter((_, i) => i !== index) }));
  };

  const handleSaveICP = async () => {
    setSaving(true);
    try {
      await apiFetch("/icp", tenantId, { method: "POST", body: JSON.stringify(icp) });
      setSaved(true);
      setTimeout(() => setSaved(false), 3000);
    } catch (e) {
      console.error(e);
    } finally {
      setSaving(false);
    }
  };

  const handleSaveBusiness = async () => {
    setSavingBusiness(true);
    try {
      await apiFetch("/business-profile", tenantId, { method: "POST", body: JSON.stringify(business) });
      setSavedBusiness(true);
      setTimeout(() => setSavedBusiness(false), 3000);
    } catch (e) {
      console.error(e);
    } finally {
      setSavingBusiness(false);
    }
  };

  return (
    <div className="p-0 max-w-2xl mx-auto">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-[#33475b] mb-1">Settings</h1>
        <p className="text-sm text-[#516f90]">Configure your profile and ICP preferences</p>
      </div>

      <div className="space-y-6">
        {/* Profile */}
        <div className="bg-white border border-[#cbd6e2] rounded-[4px] p-6">
          <div className="flex items-center gap-3 mb-6">
            <User className="w-6 h-6 text-[#ff7a59]" />
            <h2 className="text-lg font-bold text-[#33475b]">Profile</h2>
          </div>
          <div className="flex items-center gap-4 p-4 bg-[#f5f8fa] border border-[#cbd6e2] rounded-[4px]">
            {user?.imageUrl ? (
              <img src={user.imageUrl} alt="" className="w-14 h-14 rounded-full object-cover" />
            ) : (
              <div className="w-14 h-14 rounded-full bg-[#cbd6e2] flex items-center justify-center text-[#516f90] text-lg font-medium">
                {(user?.firstName?.[0] || user?.primaryEmailAddress?.emailAddress?.[0] || "?").toUpperCase()}
              </div>
            )}
            <div className="flex-1 min-w-0">
              <p className="text-base font-semibold text-[#33475b] truncate">
                {user ? `${user.firstName || ""} ${user.lastName || ""}`.trim() || "Loading..." : "Loading..."}
              </p>
              <p className="text-sm text-[#516f90] truncate">{user?.primaryEmailAddress?.emailAddress || "—"}</p>
            </div>
          </div>
          <p className="text-xs text-[#516f90] mt-3">Profile details are managed by Clerk.</p>
        </div>

        {/* Your Business */}
        <div className="bg-white border border-[#cbd6e2] rounded-[4px] p-6">
          <div className="flex items-center gap-3 mb-6">
            <Briefcase className="w-6 h-6 text-[#ff7a59]" />
            <div>
              <h2 className="text-lg font-bold text-[#33475b]">Your Business</h2>
              <p className="text-xs text-[#516f90] mt-0.5">Used to personalize outreach angles and recommended actions</p>
            </div>
          </div>
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-[#33475b] mb-1.5">Business Name</label>
              <input
                type="text"
                value={business.business_name}
                onChange={(e) => setBusiness(p => ({ ...p, business_name: e.target.value }))}
                placeholder="e.g., Acme Corp"
                className="w-full border border-[#cbd6e2] rounded-[4px] px-3 py-2 text-sm focus:outline-none focus:border-[#ff7a59]"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-[#33475b] mb-1.5">What do you sell?</label>
              <input
                type="text"
                value={business.product_service}
                onChange={(e) => setBusiness(p => ({ ...p, product_service: e.target.value }))}
                placeholder="e.g., B2B sales intelligence platform"
                className="w-full border border-[#cbd6e2] rounded-[4px] px-3 py-2 text-sm focus:outline-none focus:border-[#ff7a59]"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-[#33475b] mb-1.5">Value Proposition</label>
              <input
                type="text"
                value={business.value_proposition}
                onChange={(e) => setBusiness(p => ({ ...p, value_proposition: e.target.value }))}
                placeholder="e.g., Helps sales teams close 3x more deals with AI-powered insights"
                className="w-full border border-[#cbd6e2] rounded-[4px] px-3 py-2 text-sm focus:outline-none focus:border-[#ff7a59]"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-[#33475b] mb-1.5">Business Description</label>
              <textarea
                value={business.business_description}
                onChange={(e) => setBusiness(p => ({ ...p, business_description: e.target.value }))}
                placeholder="Brief description of your business, target market, and how you help customers..."
                rows={3}
                className="w-full border border-[#cbd6e2] rounded-[4px] px-3 py-2 text-sm focus:outline-none focus:border-[#ff7a59] resize-none"
              />
            </div>
            <div className="pt-2">
              <button
                onClick={handleSaveBusiness}
                disabled={savingBusiness}
                className="flex items-center gap-2 px-5 py-2.5 bg-[#ff7a59] text-white font-medium rounded-[4px] hover:bg-[#ff5c35] disabled:opacity-50"
              >
                <Save className="w-4 h-4" />
                {savingBusiness ? "Saving..." : "Save Business Profile"}
              </button>
              {savedBusiness && <p className="text-sm text-emerald-500 mt-2">✓ Business profile saved</p>}
            </div>
          </div>
        </div>

        {/* ICP */}
        <div className="bg-white border border-[#cbd6e2] rounded-[4px] p-6">
          <div className="flex items-center gap-3 mb-6">
            <SettingsIcon className="w-6 h-6 text-[#ff7a59]" />
            <h2 className="text-lg font-bold text-[#33475b]">Ideal Customer Profile (ICP)</h2>
          </div>

          <div className="space-y-6">
            <ICPSection title="Target Industries" items={icp.target_industries} onAdd={(v) => addItem("target_industries", v)} onRemove={(i) => removeItem("target_industries", i)} placeholder="e.g., SaaS, Healthcare, Financial Services" />
            <ICPSection title="Target Locations" items={icp.target_locations} onAdd={(v) => addItem("target_locations", v)} onRemove={(i) => removeItem("target_locations", i)} placeholder="e.g., United States, Europe, San Francisco" />
            <ICPSection title="Target Company Sizes" items={icp.target_company_sizes} onAdd={(v) => addItem("target_company_sizes", v)} onRemove={(i) => removeItem("target_company_sizes", i)} placeholder="e.g., 50-200 employees, Enterprise (1000+)" />
            <ICPSection title="Target Roles / Titles" items={icp.target_roles} onAdd={(v) => addItem("target_roles", v)} onRemove={(i) => removeItem("target_roles", i)} placeholder="e.g., CTO, VP Engineering, Head of Sales" />

            <div className="pt-4 border-t border-[#cbd6e2]">
              <button
                onClick={handleSaveICP}
                disabled={saving}
                className="flex items-center gap-2 px-5 py-2.5 bg-[#ff7a59] text-white font-medium rounded-[4px] hover:bg-[#ff5c35] disabled:opacity-50"
              >
                <Save className="w-4 h-4" />
                {saving ? "Saving..." : "Save ICP Settings"}
              </button>
              {saved && <p className="text-sm text-emerald-500 mt-2">✓ ICP settings saved</p>}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

interface ICPSectionProps {
  title: string;
  items: string[];
  onAdd: (value: string) => void;
  onRemove: (index: number) => void;
  placeholder: string;
}

function ICPSection({ title, items, onAdd, onRemove, placeholder }: ICPSectionProps) {
  const [inputValue, setInputValue] = useState("");

  const handleAdd = () => {
    onAdd(inputValue);
    setInputValue("");
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === "Enter") {
      handleAdd();
    }
  };

  return (
    <div className="border border-[#cbd6e2] rounded-[4px] p-4">
      <h4 className="text-sm font-semibold text-[#33475b] mb-3">{title}</h4>
      
      {/* Add new item */}
      <div className="flex gap-2 mb-3">
        <input
          type="text"
          value={inputValue}
          onChange={(e) => setInputValue(e.target.value)}
          onKeyPress={handleKeyPress}
          placeholder={placeholder}
          className="flex-1 px-3 py-2 border border-[#cbd6e2] rounded-[4px] text-sm focus:outline-none focus:border-[#ff7a59]"
        />
        <button
          onClick={handleAdd}
          className="bg-[#ff7a59] hover:bg-[#ff5c35] text-white px-3 py-2 rounded-[4px] text-sm flex items-center gap-1"
        >
          <Plus className="w-4 h-4" />
          Add
        </button>
      </div>

      {/* Items list */}
      <div className="flex flex-wrap gap-2">
        {items.map((item, index) => (
          <div
            key={index}
            className="bg-[#f5f8fa] border border-[#cbd6e2] rounded-[4px] px-3 py-1 text-sm flex items-center gap-2"
          >
            <span>{item}</span>
            <button
              onClick={() => onRemove(index)}
              className="text-[#516f90] hover:text-[#ff7a59] transition-colors"
            >
              <X className="w-3 h-3" />
            </button>
          </div>
        ))}
        {items.length === 0 && (
          <p className="text-[#7c98b6] text-sm italic">No items added yet</p>
        )}
      </div>
    </div>
  );
}
