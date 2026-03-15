import Link from "next/link"
import { ArrowRight } from "lucide-react"

export function CtaBanner() {
  return (
    <section className="py-24 px-6">
      <div className="max-w-3xl mx-auto text-center">
        <p className="text-xs font-semibold uppercase tracking-widest text-primary mb-4">Get started</p>
        <h2 className="text-3xl md:text-4xl font-bold text-foreground tracking-tight text-balance mb-5">
          From anonymous visit to personalized outreach in one click.
        </h2>
        <p className="text-muted-foreground text-base mb-8 leading-relaxed">
          Stop leaving pipeline on the table. Join B2B sales teams using LEPA to convert invisible traffic into booked meetings.
        </p>
        <Link
          href="/sign-up"
          className="inline-flex items-center gap-2 bg-primary text-primary-foreground px-7 py-3.5 rounded font-semibold text-sm hover:opacity-90 transition-opacity"
        >
          Get Started Free
          <ArrowRight className="w-4 h-4" />
        </Link>
        <p className="text-xs text-muted-foreground mt-4">No credit card required. Setup in under 5 minutes.</p>
      </div>
    </section>
  )
}
