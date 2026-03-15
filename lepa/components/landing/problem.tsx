import { TrendingDown, Clock, MailX } from "lucide-react"

const problems = [
  {
    icon: TrendingDown,
    stat: "98%",
    label: "of visitors leave without filling a form",
    description: "Your highest-intent prospects browse in silence. You never know they were there.",
  },
  {
    icon: Clock,
    stat: "4+ hrs",
    label: "of manual research per account",
    description: "Reps burn their best hours on LinkedIn instead of conversations that close.",
  },
  {
    icon: MailX,
    stat: "~2%",
    label: "average reply rate on generic cold emails",
    description: 'Templates with "[First Name]" and zero context get deleted on sight.',
  },
]

export function Problem() {
  return (
    <section className="py-24 px-6 bg-card border-y border-border">
      <div className="max-w-6xl mx-auto">
        <div className="text-center mb-14">
          <p className="text-xs font-semibold uppercase tracking-widest text-primary mb-3">The problem</p>
          <h2 className="text-3xl md:text-4xl font-bold text-foreground tracking-tight text-balance">
            B2B sales teams are flying blind
          </h2>
        </div>

        <div className="grid md:grid-cols-3 gap-6">
          {problems.map(({ icon: Icon, stat, label, description }) => (
            <div
              key={stat}
              className="bg-background border border-border rounded-lg p-6 flex flex-col gap-4"
            >
              <div className="w-10 h-10 rounded-lg bg-primary/10 flex items-center justify-center">
                <Icon className="w-5 h-5 text-primary" strokeWidth={1.75} />
              </div>
              <div>
                <p className="text-3xl font-bold text-foreground leading-none mb-1">{stat}</p>
                <p className="text-sm font-semibold text-foreground leading-snug">{label}</p>
              </div>
              <p className="text-sm text-muted-foreground leading-relaxed">{description}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}
