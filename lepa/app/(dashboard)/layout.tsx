"use client";

import { useState } from "react";
import Sidebar from "@/components/Sidebar";
import Header from "@/components/Header";
import AssistantSidebar from "@/components/AssistantSidebar";

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const [assistantOpen, setAssistantOpen] = useState(false);

  return (
    <div className="flex h-screen bg-[#F7F7F7] text-[#484848] overflow-hidden">
      <Sidebar />
      <div className="flex flex-col flex-1 min-w-0">
        <Header onToggleAssistant={() => setAssistantOpen(o => !o)} assistantOpen={assistantOpen} />
        <main className="flex-1 overflow-y-auto w-full bg-[#F7F7F7]">
          {children}
        </main>
      </div>
      <AssistantSidebar open={assistantOpen} onClose={() => setAssistantOpen(false)} />
    </div>
  );
}
