"use client";

import { useEffect, useState } from "react";
import { Building2, Users, TrendingUp, CheckSquare, ArrowRight } from "lucide-react";
import Link from "next/link";
import { useTenantId } from "@/hooks/useTenantId";
import { apiFetch } from "@/lib/api";

export default function DashboardPage() {
  const tenantId = useTenantId();
  const [stats, setStats] = useState({ companies: 0, visitors: 0, runs: 0 });
  const [recentRuns, setRecentRuns] = useState<Array<{ job_id: string; account_name?: string; input_type: string; started_at: string | null }>>([]);

  useEffect(() => {
    apiFetch("/analyze/stats", tenantId)
      .then((r) => r.json())
      .then((data) => {
        console.log("Dashboard stats:", data); // Debug log
        const stats = data.stats || { total: 0, visitors: 0, companies: 0 };
        const recentResults = data.recent_results || [];
        
        setStats({
          companies: stats.companies,
          visitors: stats.visitors,
          runs: stats.total,
        });
        
        // Convert to recent runs format
        const recentRuns = recentResults.map((r: any) => ({
          job_id: r.cache_key,
          account_name: r.company_name,
          input_type: r.input_type,
          started_at: r.cached_at,
        }));
        setRecentRuns(recentRuns);
      })
      .catch((error) => {
        console.error("Dashboard fetch error:", error);
        setStats({ companies: 0, visitors: 0, runs: 0 });
        setRecentRuns([]);
      });
  }, [tenantId]);

  return (
    <div className="p-0 max-w-6xl">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-[#33475b] mb-1">Dashboard</h1>
        <p className="text-sm text-[#516f90]">Overview of your account intelligence</p>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-8">
        <div className="bg-white border border-[#cbd6e2] rounded-[4px] p-6">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-[#ff7a59]/10 rounded-[4px] flex items-center justify-center">
              <Building2 className="w-5 h-5 text-[#ff7a59]" />
            </div>
            <div>
              <p className="text-2xl font-bold text-[#33475b]">{stats.companies}</p>
              <p className="text-sm text-[#516f90]">Companies</p>
            </div>
          </div>
        </div>
        <div className="bg-white border border-[#cbd6e2] rounded-[4px] p-6">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-emerald-500/10 rounded-[4px] flex items-center justify-center">
              <Users className="w-5 h-5 text-emerald-600" />
            </div>
            <div>
              <p className="text-2xl font-bold text-[#33475b]">{stats.visitors}</p>
              <p className="text-sm text-[#516f90]">Visitors</p>
            </div>
          </div>
        </div>
        <div className="bg-white border border-[#cbd6e2] rounded-[4px] p-6">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-amber-500/10 rounded-[4px] flex items-center justify-center">
              <TrendingUp className="w-5 h-5 text-amber-600" />
            </div>
            <div>
              <p className="text-2xl font-bold text-[#33475b]">{stats.runs}</p>
              <p className="text-sm text-[#516f90]">Pipeline Runs</p>
            </div>
          </div>
        </div>
      </div>

      {/* Quick actions & Recent activity */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-white border border-[#cbd6e2] rounded-[4px] p-6">
          <h2 className="text-base font-semibold text-[#33475b] mb-4">Quick Actions</h2>
          <div className="space-y-3">
            <Link
              href="/visitors"
              className="flex items-center justify-between p-3 bg-[#f5f8fa] border border-[#cbd6e2] rounded-[4px] hover:bg-[#e8eef2] transition-colors group"
            >
              <div className="flex items-center gap-3">
                <Users className="w-5 h-5 text-[#ff7a59]" />
                <span className="font-medium text-[#33475b]">Add Visitor</span>
              </div>
              <ArrowRight className="w-4 h-4 text-[#516f90] group-hover:text-[#0091ae]" />
            </Link>
            <Link
              href="/companies"
              className="flex items-center justify-between p-3 bg-[#f5f8fa] border border-[#cbd6e2] rounded-[4px] hover:bg-[#e8eef2] transition-colors group"
            >
              <div className="flex items-center gap-3">
                <Building2 className="w-5 h-5 text-[#ff7a59]" />
                <span className="font-medium text-[#33475b]">Add Company</span>
              </div>
              <ArrowRight className="w-4 h-4 text-[#516f90] group-hover:text-[#0091ae]" />
            </Link>
          </div>
        </div>

        <div className="bg-white border border-[#cbd6e2] rounded-[4px] p-6">
          <h2 className="text-base font-semibold text-[#33475b] mb-4">Recent Activity</h2>
          {recentRuns.length === 0 ? (
            <p className="text-sm text-[#516f90]">No pipeline runs yet. Add a visitor or company to get started.</p>
          ) : (
            <div className="space-y-3">
              {recentRuns.map((run, i) => (
                <div
                  key={`${run.job_id}-${i}`}
                  className="flex items-center justify-between py-2 border-b border-[#cbd6e2] last:border-0"
                >
                  <div>
                    <p className="text-sm font-medium text-[#33475b]">{run.account_name || run.job_id}</p>
                    <p className="text-xs text-[#516f90]">
                      {run.input_type === "visitor_signal" ? "Visitor" : "Company"} • {run.started_at ? new Date(run.started_at).toLocaleString() : "—"}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
