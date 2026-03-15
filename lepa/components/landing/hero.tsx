import Link from "next/link"
import { ArrowRight } from "lucide-react"

export function Hero() {
  return (
    <section className="pt-32 pb-24 px-6">
      <div className="max-w-4xl mx-auto text-center">
        <div className="inline-flex items-center gap-2 bg-card border border-border rounded-full px-3.5 py-1.5 text-xs text-muted-foreground mb-8 font-medium">
          <span className="w-1.5 h-1.5 rounded-full bg-primary" />
          AI-powered account intelligence
        </div>

        <h1 className="text-4xl sm:text-5xl md:text-6xl font-bold text-foreground leading-tight tracking-tight text-balance mb-6">
          Your website visitors are your best leads.{" "}
          <span className="text-primary">You just don&apos;t know who they are.</span>
        </h1>

        <p className="text-lg text-muted-foreground leading-relaxed max-w-2xl mx-auto mb-10 text-pretty">
          LEPA identifies anonymous visitors, researches the buying committee, and writes the first personalized email — in one click. No forms. No guesswork.
        </p>

        <div className="flex flex-col sm:flex-row items-center justify-center gap-3">
          <Link
            href="/sign-up"
            className="w-full sm:w-auto inline-flex items-center justify-center gap-2 bg-primary text-primary-foreground px-6 py-3 rounded font-semibold text-sm hover:opacity-90 transition-opacity"
          >
            Try LEPA Free
            <ArrowRight className="w-4 h-4" />
          </Link>
          <Link
            href="#how-it-works"
            className="w-full sm:w-auto inline-flex items-center justify-center gap-2 text-sm text-muted-foreground hover:text-foreground transition-colors px-6 py-3"
          >
            See how it works
          </Link>
        </div>

        {/* Code snippet teaser */}
        <div className="mt-16 bg-card border border-border rounded-lg p-5 max-w-lg mx-auto text-left shadow-sm">
          <div className="flex items-center gap-2 mb-3">
            <span className="w-2.5 h-2.5 rounded-full bg-[#FF5A5F]" />
            <span className="w-2.5 h-2.5 rounded-full bg-[#DDDDDD]" />
            <span className="w-2.5 h-2.5 rounded-full bg-[#DDDDDD]" />
            <span className="text-xs text-muted-foreground ml-2 font-mono">index.html</span>
          </div>
          <pre className="text-xs font-mono leading-relaxed text-foreground overflow-x-auto">
            <code>
              <span className="text-muted-foreground">{`<!-- Paste once. Identify forever. -->`}</span>{"\n"}
              <span>{`<script src="https://cdn.lepa.ai/v1/track.js"`}</span>{"\n"}
              <span>{`  data-key="`}</span><span className="text-primary">pk_live_xxxxx</span><span>{`">`}</span>{"\n"}
              <span>{`</script>`}</span>
            </code>
          </pre>
        </div>
      </div>
    </section>
  )
}
