"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { LayoutDashboard, Settings, Building2, Users, Contact, Code2 } from "lucide-react";
import { useUser } from "@clerk/nextjs";

const navigation = [
  { name: "Dashboard", href: "/", icon: LayoutDashboard },
  { name: "Visitors", href: "/visitors", icon: Users },
  { name: "Companies", href: "/companies", icon: Building2 },
  { name: "Contacts", href: "/contacts", icon: Contact },
  { name: "Tracking", href: "/tracking", icon: Code2 },
  { name: "Settings", href: "/settings", icon: Settings },
];

export default function Sidebar() {
  const pathname = usePathname();
  const { user } = useUser();

  return (
    <aside className="w-[190px] min-w-[190px] h-screen bg-[#2d3e50] flex flex-col shrink-0 overflow-y-auto">
      {/* Logo */}
      <div className="px-5 py-4">
        <h1 className="text-base font-semibold text-white tracking-tight">LEPA</h1>
        <p className="text-[11px] text-[#7c98b6] mt-0.5">Account Intelligence</p>
      </div>

      <div className="border-t border-[#3a4f63] mx-3 mb-1" />

      {/* Navigation - HubSpot-style */}
      <nav className="flex-1 py-1">
        {navigation.map((item) => {
          const isActive = pathname === item.href;
          return (
            <Link
              key={item.name}
              href={item.href}
              className={`w-full flex items-center gap-3 px-5 py-[9px] text-[14px] font-medium transition-colors ${
                isActive ? "bg-[#3a4f63] text-white" : "text-[#b6c7d6] hover:bg-[#354b5e] hover:text-white"
              }`}
            >
              <item.icon className="w-[18px] h-[18px] flex-shrink-0" />
              <span className="truncate flex-1 text-left">{item.name}</span>
            </Link>
          );
        })}
      </nav>

      {/* Bottom - Logged-in user */}
      <div className="p-3 border-t border-[#3a4f63]">
        <div className="flex items-center gap-2.5 px-2 py-2">
          {user?.imageUrl ? (
            <img
              src={user.imageUrl}
              alt=""
              className="w-8 h-8 rounded-full object-cover shrink-0"
            />
          ) : (
            <div className="w-8 h-8 rounded-full bg-[#3a4f63] flex items-center justify-center text-white text-xs font-semibold shrink-0">
              {(user?.firstName?.[0] || user?.primaryEmailAddress?.emailAddress?.[0] || "?").toUpperCase()}
            </div>
          )}
          <div className="flex-1 min-w-0">
            <p className="text-[13px] font-medium text-white truncate">
              {user ? `${user.firstName || ""} ${user.lastName || ""}`.trim() || "User" : "Loading..."}
            </p>
            <p className="text-[11px] text-[#7c98b6] truncate">
              {user?.primaryEmailAddress?.emailAddress || "—"}
            </p>
          </div>
        </div>
      </div>
    </aside>
  );
}
