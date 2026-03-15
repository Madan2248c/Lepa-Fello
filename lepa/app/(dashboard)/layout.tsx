import Sidebar from "@/components/Sidebar";
import Header from "@/components/Header";

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="flex h-screen bg-[#f5f8fa] text-[#33475b] overflow-hidden">
      <Sidebar />
      <div className="flex flex-col flex-1 relative min-w-0 bg-[#f5f8fa]">
        <Header />
        <main className="flex-1 overflow-y-auto p-4 sm:p-6 lg:p-8 relative z-10 w-full bg-[#f5f8fa]">
          <div className="mx-auto max-w-7xl h-full">
            {children}
          </div>
        </main>
      </div>
    </div>
  );
}
