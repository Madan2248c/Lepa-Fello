"use client";

import { useEffect, useState } from "react";
import { Building2, Users, TrendingUp, Contact, ArrowRight, Zap } from "lucide-react";
import Link from "next/link";
import { useTenantId } from "@/hooks/useTenantId";
import { apiFetch } from "@/lib/api";
import { useApiFetch } from "@/hooks/useApiFetch";
import { StatCardSkeleton, Skeleton } from "@/components/Skeleton";
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell,
  PieChart, Pie, Legend,
  RadialBarChart, RadialBar,
} from "recharts";

interface TopAccount { account_id: string; account_name: string; intent_score: number; intent_stage: string; }
interface RecentRun { job_id: string; account_name?: string; input_type: string; started_at: string | null; }

const STAGE_COLORS: Record<string, string> = {
  "Awareness":     "#767676",
  "Consideration": "#f5a623",
  "Decision":      "#FF5A5F",
  "Champion":      "#00bda5",
  "Research":      "#7c4dff",
  "Qualified":     "#0091ae",
  "Engaged":       "#f2547d",
  "Opportunity":   "#00bda5",
};

const INTENT_COLOR = (score: number) =>
  score >= 8 ? "#FF5A5F" : score >= 6 ? "#f5a623" : score >= 4 ? "#0091ae" : "#767676";

const CustomTooltip = ({ active, payload, label }: any) => {
  if (!active || !payload?.length) return null;
  return (
    <div className="bg-[#484848] text-white text-[12px] px-3 py-2 rounded-[4px] shadow-lg">
      <p className="font-semibold mb-0.5">{label}</p>
      {payload.map((p: any) => (
        <p key={p.name}>{p.name}: <span className="font-bold">{typeof p.value === "number" ? p.value.toFixed(1) : p.value}</span></p>
      ))}
    </div>
  );
};

export default function DashboardPage() {
  const apiFetch = useApiFetch();
  const tenantId = useTenantId();
  const [stats, setStats] = useState({ companies: 0, visitors: 0, runs: 0, contacts: 0 });
  const [recentRuns, setRecentRuns] = useState<RecentRun[]>([]);
  const [topAccounts, setTopAccounts] = useState<TopAccount[]>([]);
  const [intentDist, setIntentDist] = useState<Record<string, number>>({});
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!tenantId) return;
    apiFetch("/analyze/stats", tenantId)
      .then(r => r.json())
      .then(data => {
        const s = data.stats || {};
        setStats({ companies: s.companies || 0, visitors: s.visitors || 0, runs: s.total || 0, contacts: s.contacts || 0 });
        setRecentRuns((data.recent_results || []).map((r: any) => ({
          job_id: r.cache_key, account_name: r.company_name,
          input_type: r.input_type, started_at: r.cached_at,
        })));
        setTopAccounts(data.top_accounts || []);
        setIntentDist(data.intent_distribution || {});
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [tenantId]);

  const statCards = [
    { label: "Companies", value: stats.companies, icon: Building2, color: "#FF5A5F", bg: "linear-gradient(135deg,#FF5A5F,#e0504a)", href: "/companies" },
    { label: "Visitors", value: stats.visitors, icon: Users, color: "#00bda5", bg: "linear-gradient(135deg,#00bda5,#00a38d)", href: "/visitors" },
    { label: "Contacts", value: stats.contacts, icon: Contact, color: "#7c4dff", bg: "linear-gradient(135deg,#7c4dff,#651fff)", href: "/contacts" },
    { label: "Pipeline Runs", value: stats.runs, icon: TrendingUp, color: "#f5a623", bg: "linear-gradient(135deg,#f5a623,#e09400)", href: "/companies" },
  ];

  const barData = topAccounts.map(a => ({
    name: (a.account_name || a.account_id || "").split(" ").slice(0, 2).join(" "),
    score: a.intent_score,
    stage: a.intent_stage,
  }));

  const pieData = Object.entries(intentDist).map(([name, value]) => ({
    name, value: Number(value), fill: STAGE_COLORS[name] || "#DDDDDD",
  }));

  const radialData = topAccounts.slice(0, 5).map((a, i) => ({
    name: (a.account_name || "").split(" ")[0],
    score: a.intent_score,
    fill: ["#FF5A5F", "#f5a623", "#00bda5", "#7c4dff", "#0091ae"][i % 5],
  }));

  return (
    <div className="p-6 space-y-5">
      {/* Header */}
      <div>
        <h1 className="text-[22px] font-bold text-[#484848]">Dashboard</h1>
        <p className="text-[13px] text-[#767676] mt-0.5">Your account intelligence at a glance</p>
      </div>

      {/* Stat cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {loading ? Array.from({ length: 4 }).map((_, i) => <StatCardSkeleton key={i} />) :
          statCards.map(c => (
            <Link key={c.label} href={c.href}
              className="rounded-[8px] p-5 text-white hover:opacity-90 transition-opacity group relative overflow-hidden"
              style={{ background: c.bg }}
            >
              <div className="absolute right-3 top-3 opacity-20">
                <c.icon className="w-12 h-12" />
              </div>
              <p className="text-[32px] font-bold leading-none">{c.value}</p>
              <p className="text-[13px] mt-1 opacity-90">{c.label}</p>
              <div className="flex items-center gap-1 mt-3 text-[12px] opacity-75 group-hover:opacity-100">
                <span>View all</span><ArrowRight className="w-3 h-3" />
              </div>
            </Link>
          ))
        }
      </div>

      {/* Charts row */}
      <div className="grid grid-cols-1 lg:grid-cols-5 gap-4">

        {/* Intent bar chart — spans 3 cols */}
        <div className="lg:col-span-3 bg-white border border-[#DDDDDD] rounded-[8px] p-5">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h2 className="text-[14px] font-semibold text-[#484848]">Intent Scores</h2>
              <p className="text-[11px] text-[#767676]">Top accounts ranked by buying intent</p>
            </div>
            <Link href="/companies" className="text-[12px] text-[#FF5A5F] hover:underline">View all →</Link>
          </div>
          {loading ? <Skeleton className="h-48 w-full" /> :
           barData.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-48 text-center">
              <Zap className="w-8 h-8 text-[#DDDDDD] mb-2" />
              <p className="text-[13px] text-[#767676]">No accounts yet</p>
              <Link href="/companies" className="mt-1 text-[12px] text-[#FF5A5F] hover:underline">Add your first company →</Link>
            </div>
          ) : (
            <ResponsiveContainer width="100%" height={220}>
              <BarChart data={barData} layout="vertical" margin={{ left: 0, right: 20, top: 0, bottom: 0 }}>
                <XAxis type="number" domain={[0, 10]} tick={{ fontSize: 11, fill: "#767676" }} tickLine={false} axisLine={false} />
                <YAxis type="category" dataKey="name" width={90} tick={{ fontSize: 12, fill: "#484848" }} tickLine={false} axisLine={false} />
                <Tooltip content={<CustomTooltip />} cursor={{ fill: "#F7F7F7" }} />
                <Bar dataKey="score" radius={[0, 4, 4, 0]} maxBarSize={20}>
                  {barData.map((entry, i) => (
                    <Cell key={i} fill={INTENT_COLOR(entry.score)} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          )}
        </div>

        {/* Pie chart — spans 2 cols */}
        <div className="lg:col-span-2 bg-white border border-[#DDDDDD] rounded-[8px] p-5">
          <div className="mb-4">
            <h2 className="text-[14px] font-semibold text-[#484848]">Intent Stages</h2>
            <p className="text-[11px] text-[#767676]">Distribution across pipeline stages</p>
          </div>
          {loading ? <Skeleton className="h-48 w-full" /> :
           pieData.length === 0 ? (
            <div className="flex items-center justify-center h-48 text-[13px] text-[#767676]">No data yet</div>
          ) : (
            <ResponsiveContainer width="100%" height={220}>
              <PieChart>
                <Pie
                  data={pieData}
                  cx="50%" cy="45%"
                  innerRadius={50} outerRadius={75}
                  paddingAngle={3}
                  dataKey="value"
                >
                  {pieData.map((entry, i) => (
                    <Cell key={i} fill={entry.fill} />
                  ))}
                </Pie>
                <Tooltip content={<CustomTooltip />} />
                <Legend
                  iconType="circle" iconSize={8}
                  formatter={(v) => <span style={{ fontSize: 11, color: "#484848" }}>{v}</span>}
                />
              </PieChart>
            </ResponsiveContainer>
          )}
        </div>
      </div>

      {/* Radial + Recent row */}
      <div className="grid grid-cols-1 lg:grid-cols-5 gap-4">

        {/* Radial bar — top 5 */}
        <div className="lg:col-span-2 bg-white border border-[#DDDDDD] rounded-[8px] p-5">
          <div className="mb-4">
            <h2 className="text-[14px] font-semibold text-[#484848]">Top 5 Radar</h2>
            <p className="text-[11px] text-[#767676]">Intent score out of 10</p>
          </div>
          {loading ? <Skeleton className="h-44 w-full" /> :
           radialData.length === 0 ? (
            <div className="flex items-center justify-center h-44 text-[13px] text-[#767676]">No data yet</div>
          ) : (
            <ResponsiveContainer width="100%" height={180}>
              <RadialBarChart
                cx="50%" cy="50%"
                innerRadius="20%" outerRadius="90%"
                data={radialData}
                startAngle={180} endAngle={0}
              >
                <RadialBar dataKey="score" background={{ fill: "#F7F7F7" }} cornerRadius={4} label={false} />
                <Tooltip content={<CustomTooltip />} />
                <Legend
                  iconType="circle" iconSize={8}
                  formatter={(v) => <span style={{ fontSize: 11, color: "#484848" }}>{v}</span>}
                />
              </RadialBarChart>
            </ResponsiveContainer>
          )}
        </div>

        {/* Recent activity */}
        <div className="lg:col-span-3 bg-white border border-[#DDDDDD] rounded-[8px] overflow-hidden">
          <div className="flex items-center justify-between px-5 py-4 border-b border-[#eaf0f6]">
            <h2 className="text-[14px] font-semibold text-[#484848]">Recent Activity</h2>
            <Link href="/companies" className="text-[12px] text-[#FF5A5F] hover:underline">View all →</Link>
          </div>
          {loading ? (
            <div className="divide-y divide-[#eaf0f6]">
              {Array.from({ length: 4 }).map((_, i) => (
                <div key={i} className="flex items-center gap-4 px-5 py-3">
                  <Skeleton className="w-8 h-8 rounded-full" />
                  <div className="space-y-1.5 flex-1"><Skeleton className="h-3 w-36" /><Skeleton className="h-2.5 w-24" /></div>
                  <Skeleton className="h-5 w-16 rounded-full" />
                </div>
              ))}
            </div>
          ) : recentRuns.length === 0 ? (
            <div className="px-5 py-10 text-center text-[13px] text-[#767676]">
              No runs yet. <Link href="/companies" className="text-[#FF5A5F] hover:underline">Add a company</Link> to start.
            </div>
          ) : (
            <div className="divide-y divide-[#eaf0f6]">
              {recentRuns.map((run, i) => (
                <div key={`${run.job_id}-${i}`} className="flex items-center gap-3 px-5 py-3 hover:bg-[#F7F7F7]">
                  <div className={`w-8 h-8 rounded-full flex items-center justify-center shrink-0 ${
                    run.input_type === "visitor_signal" ? "bg-[#e6faf8]" : "bg-[#fff0ed]"
                  }`}>
                    {run.input_type === "visitor_signal"
                      ? <Users className="w-3.5 h-3.5 text-[#00bda5]" />
                      : <Building2 className="w-3.5 h-3.5 text-[#FF5A5F]" />}
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-[13px] font-medium text-[#484848] truncate">{run.account_name || run.job_id}</p>
                    <p className="text-[11px] text-[#767676]">{run.started_at ? new Date(run.started_at).toLocaleString() : "—"}</p>
                  </div>
                  <span className={`text-[11px] font-semibold px-2.5 py-1 rounded-full ${
                    run.input_type === "visitor_signal" ? "bg-[#e6faf8] text-[#00bda5]" : "bg-[#fff0ed] text-[#FF5A5F]"
                  }`}>
                    {run.input_type === "visitor_signal" ? "Visitor" : "Company"}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
