import { Code2, BarChart3, Users, Send } from "lucide-react"

const steps = [
  {
    number: "01",
    icon: Code2,
    title: "Embed a script tag",
    description: "Paste one line of JavaScript on your site. Visitors are identified by IP — no cookies required.",
  },
  {
    number: "02",
    icon: BarChart3,
    title: "Click Analyze",
    description: "Instant ICP score, intent signals, tech stack, and firmographics for every company that visits.",
  },
  {
    number: "03",
    icon: Users,
    title: "Click Deep Research",
    description: "LEPA's agent discovers the full buying committee via Apollo, Exa, BuiltWith & LinkedIn.",
  },
  {
    number: "04",
    icon: Send,
    title: "Send the draft",
    description: "A personalized cold email and LinkedIn message, tailored to each stakeholder. No placeholders.",
  },
]

export function HowItWorks() {
  return (
    <section id="how-it-works" className="py-24 px-6">
      <div className="max-w-6xl mx-auto">
        <div className="text-center mb-14">
          <p className="text-xs font-semibold uppercase tracking-widest text-primary mb-3">How it works</p>
          <h2 className="text-3xl md:text-4xl font-bold text-foreground tracking-tight text-balance">
            From anonymous visit to sent email in minutes
          </h2>
        </div>

        {/* Desktop: horizontal flow */}
        <div className="hidden md:grid grid-cols-4 gap-0 relative">
          {/* Connecting line */}
          <div className="absolute top-[2.25rem] left-[12.5%] right-[12.5%] h-px bg-border z-0" />

          {steps.map(({ number, icon: Icon, title, description }) => (
            <div key={number} className="flex flex-col items-center text-center px-4 relative z-10">
              <div className="w-[3.25rem] h-[3.25rem] rounded-full bg-card border-2 border-border flex items-center justify-center mb-5 shadow-sm">
                <Icon className="w-5 h-5 text-primary" strokeWidth={1.75} />
              </div>
              <p className="text-xs font-bold text-primary tracking-widest mb-1">{number}</p>
              <p className="font-semibold text-foreground text-sm mb-2">{title}</p>
              <p className="text-xs text-muted-foreground leading-relaxed">{description}</p>
            </div>
          ))}
        </div>

        {/* Mobile: vertical stack */}
        <div className="md:hidden flex flex-col gap-0 relative">
          <div className="absolute left-6 top-6 bottom-6 w-px bg-border z-0" />
          {steps.map(({ number, icon: Icon, title, description }) => (
            <div key={number} className="flex gap-5 items-start mb-8 relative z-10">
              <div className="w-12 h-12 rounded-full bg-card border-2 border-border flex items-center justify-center flex-shrink-0 shadow-sm">
                <Icon className="w-4.5 h-4.5 text-primary" strokeWidth={1.75} />
              </div>
              <div className="pt-2">
                <p className="text-xs font-bold text-primary tracking-widest mb-0.5">{number}</p>
                <p className="font-semibold text-foreground text-sm mb-1">{title}</p>
                <p className="text-xs text-muted-foreground leading-relaxed">{description}</p>
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}
