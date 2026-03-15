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
    <aside className="w-[190px] min-w-[190px] h-screen bg-[#F7F7F7] flex flex-col shrink-0 overflow-y-auto border-r border-[#DDDDDD]">
      {/* Logo */}
      <div className="px-5 py-4">
        <h1 className="text-base font-semibold text-[#484848] tracking-tight">LEPA</h1>
        <p className="text-[11px] text-[#767676] mt-0.5">Account Intelligence</p>
      </div>

      <div className="border-t border-[#DDDDDD] mx-3 mb-1" />

      {/* Navigation */}
      <nav className="flex-1 py-1">
        {navigation.map((item) => {
          const isActive = pathname === item.href;
          return (
            <Link
              key={item.name}
              href={item.href}
              className={`w-full flex items-center gap-3 px-5 py-[9px] text-[14px] font-medium transition-colors ${
                isActive ? "bg-[#FF5A5F] text-white" : "text-[#484848] hover:bg-[#DDDDDD] hover:text-[#484848]"
              }`}
            >
              <item.icon className="w-[18px] h-[18px] flex-shrink-0" />
              <span className="truncate flex-1 text-left">{item.name}</span>
            </Link>
          );
        })}
      </nav>

      {/* Bottom - Logged-in user */}
      <div className="p-3 border-t border-[#DDDDDD]">
        <div className="flex items-center gap-2.5 px-2 py-2">
          {user?.imageUrl ? (
            <img src={user.imageUrl} alt="" className="w-8 h-8 rounded-full object-cover shrink-0" />
          ) : (
            <div className="w-8 h-8 rounded-full bg-[#FF5A5F] flex items-center justify-center text-white text-xs font-semibold shrink-0">
              {(user?.firstName?.[0] || user?.primaryEmailAddress?.emailAddress?.[0] || "?").toUpperCase()}
            </div>
          )}
          <div className="flex-1 min-w-0">
            <p className="text-[13px] font-medium text-[#484848] truncate">
              {user ? `${user.firstName || ""} ${user.lastName || ""}`.trim() || "User" : "Loading..."}
            </p>
            <p className="text-[11px] text-[#767676] truncate">
              {user?.primaryEmailAddress?.emailAddress || "—"}
            </p>
          </div>
        </div>
      </div>
    </aside>
  );
}
