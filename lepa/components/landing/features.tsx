import {
  Globe,
  Brain,
  SearchCode,
  Network,
  Mail,
  RefreshCw,
} from "lucide-react"

const features = [
  {
    icon: Globe,
    title: "Visitor Identification",
    description:
      "Resolve anonymous IPs to real companies — with firmographics, industry, and size. No cookies or forms needed.",
    tag: "IP → Company",
  },
  {
    icon: Brain,
    title: "AI Account Analysis",
    description:
      "Instant ICP fit score, intent stage classification, and tech stack detection for every account that visits.",
    tag: "ICP + Intent",
  },
  {
    icon: SearchCode,
    title: "Deep Research Agent",
    description:
      "Automated account research powered by Apollo, Exa, BuiltWith, and LinkedIn scraping in a single agentic loop.",
    tag: "Apollo · Exa · BuiltWith",
  },
  {
    icon: Network,
    title: "Buying Committee Mapping",
    description:
      "Identifies the economic buyer, champion, and technical evaluator — with titles, LinkedIn profiles, and contact info.",
    tag: "Multi-stakeholder",
  },
  {
    icon: Mail,
    title: "Personalized Outreach Drafts",
    description:
      "Cold emails and LinkedIn messages tailored to each stakeholder. No placeholders. No generic templates.",
    tag: "Email + LinkedIn",
  },
  {
    icon: RefreshCw,
    title: "HubSpot Sync",
    description:
      "Push accounts, contacts, and outreach drafts to your CRM in one click. Keep your pipeline clean and current.",
    tag: "One-click CRM",
  },
]

export function Features() {
  return (
    <section id="features" className="py-24 px-6 bg-card border-y border-border">
      <div className="max-w-6xl mx-auto">
        <div className="text-center mb-14">
          <p className="text-xs font-semibold uppercase tracking-widest text-primary mb-3">Features</p>
          <h2 className="text-3xl md:text-4xl font-bold text-foreground tracking-tight text-balance">
            Everything you need to close the invisible pipeline
          </h2>
        </div>

        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-5">
          {features.map(({ icon: Icon, title, description, tag }) => (
            <div
              key={title}
              className="bg-background border border-border rounded-lg p-6 flex flex-col gap-4 hover:border-primary/40 transition-colors group"
            >
              <div className="flex items-start justify-between gap-3">
                <div className="w-9 h-9 rounded-lg bg-primary/10 flex items-center justify-center flex-shrink-0 group-hover:bg-primary/15 transition-colors">
                  <Icon className="w-4.5 h-4.5 text-primary" strokeWidth={1.75} />
                </div>
                <span className="text-[10px] font-semibold text-muted-foreground border border-border rounded-full px-2 py-0.5 mt-0.5 whitespace-nowrap">
                  {tag}
                </span>
              </div>
              <div>
                <h3 className="font-semibold text-foreground text-sm mb-1.5">{title}</h3>
                <p className="text-sm text-muted-foreground leading-relaxed">{description}</p>
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}
