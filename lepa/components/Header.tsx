"use client";

import { Search, Bell, ChevronDown } from "lucide-react";
import { UserButton } from "@clerk/nextjs";

export default function Header() {
  return (
    <header className="h-[52px] min-h-[52px] bg-white border-b border-[#cbd6e2] flex items-center px-4 gap-3 shrink-0">
      {/* Search - HubSpot style */}
      <div className="flex items-center bg-[#f5f8fa] rounded-[4px] border border-[#cbd6e2] px-3 py-[6px] w-[340px]">
        <Search className="w-[14px] h-[14px] text-[#516f90] mr-2 flex-shrink-0" />
        <span className="text-[14px] text-[#516f90]">Search LEPA</span>
      </div>

      <div className="flex-1" />

      {/* Right side */}
      <div className="flex items-center gap-1">
        <button className="w-[36px] h-[36px] flex items-center justify-center text-[#516f90] hover:bg-[#f5f8fa] rounded transition-colors">
          <Bell className="w-[16px] h-[16px]" />
        </button>

        <div className="w-px h-[24px] bg-[#cbd6e2] mx-1" />

        <UserButton
          appearance={{
            elements: {
              avatarBox: "w-8 h-8",
            },
          }}
        />
      </div>
    </header>
  );
}
