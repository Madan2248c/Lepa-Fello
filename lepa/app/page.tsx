import { LandingNavbar } from "@/components/landing/navbar";
import { Hero } from "@/components/landing/hero";
import { Problem } from "@/components/landing/problem";
import { HowItWorks } from "@/components/landing/how-it-works";
import { Features } from "@/components/landing/features";
import { CtaBanner } from "@/components/landing/cta-banner";
import { LandingFooter } from "@/components/landing/footer";

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-[#F7F7F7] text-[#484848] font-sans">
      <LandingNavbar />
      <main>
        <Hero />
        <Problem />
        <HowItWorks />
        <Features />
        <CtaBanner />
      </main>
      <LandingFooter />
    </div>
  );
}
