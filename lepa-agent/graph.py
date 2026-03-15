"""
LEPA Research Agent — Agents as Tools pattern.

One orchestrator (Claude Sonnet) with 4 async tool-agents.
The orchestrator decides what to call and in what order based on what it finds.

Fixes from audit:
1. Agents as Tools instead of Graph — adaptive, not pre-wired
2. Native async @tool functions — no _run() thread hack
3. BedrockModel with cache_tools + CacheConfig(strategy="auto")
4. ICP scoring and committee classification in deterministic Python (no LLM)
5. Sonnet for orchestrator, Haiku for sub-agents
"""

import sys
import os
import asyncio
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lepa-backend"))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), "..", "lepa-backend", ".env"))

from strands import Agent, tool
from strands.models import BedrockModel, CacheConfig

HAIKU  = "us.anthropic.claude-3-5-haiku-20241022-v1:0"
SONNET = "us.anthropic.claude-sonnet-4-20250514-v1:0"

# ── Deterministic helpers (no LLM needed) ──────────────────────────────────

_COMMITTEE_RULES = [
    (["ceo","chief executive","president","founder","co-founder","owner"], "Economic Buyer"),
    (["cro","chief revenue","vp sales","head of sales","director of sales"],  "Champion"),
    (["cmo","chief marketing","vp marketing","head of marketing"],            "Champion"),
    (["cto","chief technology","vp engineering","head of engineering","architect","devops","it director"], "Technical Evaluator"),
    (["revops","revenue operations","sales ops","marketing ops"],             "Technical Evaluator"),
    (["cfo","chief financial","finance","procurement","legal","compliance"],  "Blocker"),
]

def classify_role(title: str) -> str:
    t = title.lower()
    for keywords, role in _COMMITTEE_RULES:
        if any(k in t for k in keywords):
            return role
    return "Influencer"


_ICP_INDUSTRIES = ["software","saas","technology","fintech","healthtech","edtech",
                   "ecommerce","b2b","cloud","cybersecurity","data","analytics","ai"]
_ICP_SIZES      = ["11-50","51-200","201-500","501-1000","1001-5000"]

def score_icp(industry: str, size: str, tech_count: int, signal_count: int) -> dict:
    ind  = 100 if any(k in (industry or "").lower() for k in _ICP_INDUSTRIES) else 25
    sz   = 90  if any(s in (size or "") for s in _ICP_SIZES) else 35
    tech = min(100, 30 + tech_count * 14)
    sig  = min(100, 30 + signal_count * 20)
    score = round(ind * 0.30 + sz * 0.25 + tech * 0.25 + sig * 0.20)
    tier  = "Strong Fit" if score >= 80 else "Good Fit" if score >= 60 else "Partial Fit" if score >= 40 else "Poor Fit"
    return {"score": score, "tier": tier,
            "dimensions": {"industry": ind, "size": sz, "tech": tech, "signals": sig}}


# ── Async tool-agents ──────────────────────────────────────────────────────

@tool
async def research_company_website(company_name: str, domain: str) -> str:
    """
    Gather company firmographics, tech stack, and recent business signals.
    Always call this first. Returns industry, size, HQ, LinkedIn URL, tech stack, signals.
    """
    from clients.scraper import scrape_company_website
    from clients.apollo_client import enrich_organization
    from clients.exa_client import search_business_signals
    from clients.builtwith_client import get_tech_stack

    async def _noop():
        return None

    results = await asyncio.gather(
        enrich_organization(domain) if domain else _noop(),
        scrape_company_website(domain) if domain else _noop(),
        search_business_signals(company_name),
        get_tech_stack(domain) if domain else _noop(),
        return_exceptions=True,
    )
    apollo, website, signals, tech = results

    lines = [f"=== {company_name} ==="]
    industry = ""
    size_str = ""
    tech_count = 0
    sig_count = 0

    try:
        if not isinstance(apollo, (Exception, type(None))) and apollo and getattr(apollo, 'name', None):
            industry = apollo.industry or ""
            size_str = apollo.employee_range or ""
            lines += [
                f"Industry: {industry or 'unknown'}",
                f"Size: {size_str or 'unknown'}",
                f"HQ: {apollo.headquarters or 'unknown'}",
                f"Founded: {apollo.founded_year or 'unknown'}",
                f"LinkedIn: {apollo.linkedin_url or 'not found'}",
                f"Description: {(apollo.description or 'N/A')[:300]}",
            ]
    except Exception:
        lines.append("Apollo: data unavailable")

    try:
        if not isinstance(website, (Exception, type(None))) and getattr(website, 'success', False):
            lines.append(f"Website tech: {', '.join(website.technologies[:10]) or 'none detected'}")
            li = (website.social_links or {}).get("linkedin")
            if li:
                lines.append(f"LinkedIn (from website): {li}")
    except Exception:
        pass

    try:
        if not isinstance(signals, (Exception, type(None))) and getattr(signals, 'success', False):
            sig_count = len(signals.results)
            for r in signals.results[:5]:
                lines.append(f"Signal [{r.published_date or 'recent'}]: {r.title}")
    except Exception:
        pass

    try:
        if not isinstance(tech, (Exception, type(None))) and tech:
            tech_count = len(tech) if isinstance(tech, list) else 0
            if tech_count:
                stack = ", ".join(f"{t.get('name','')}({t.get('category','')})" for t in (tech if isinstance(tech, list) else [])[:12])
                lines.append(f"BuiltWith: {stack}")
    except Exception:
        pass

    icp = score_icp(industry, size_str, tech_count, sig_count)
    lines.append(f"ICP Score: {icp['score']}/100 ({icp['tier']}) | dimensions={icp['dimensions']}")

    return "\n".join(lines)


@tool
async def research_linkedin_company(linkedin_url: str) -> str:
    """
    Scrape a LinkedIn company page for employees and their profile URLs.
    Only call this when you have a LinkedIn company URL from research_company_website.
    Returns employee names, titles, and LinkedIn profile URLs for decision-makers.
    """
    from clients.apify_linkedin_client import scrape_linkedin_company
    result = await scrape_linkedin_company(linkedin_url)
    if not result.success:
        return f"LinkedIn scrape failed: {result.error}"

    employees = []
    for e in (result.employees or [])[:15]:
        role = classify_role(e.get("position") or "")
        employees.append(f"  {e.get('name')} | {e.get('position')} | {role} | {e.get('profile_url','no url')}")

    return (
        f"LinkedIn: {result.company_name} | {result.company_size} | {result.industry}\n"
        f"About: {(result.about or '')[:300]}\n"
        "Employees (Name | Title | BuyingRole | ProfileURL):\n" + "\n".join(employees)
    )


@tool
async def enrich_person_profiles(linkedin_urls_csv: str) -> str:
    """
    Scrape individual LinkedIn profiles for decision-makers in bulk.
    Pass comma-separated LinkedIn profile URLs (max 8).
    Only call this after getting profile URLs from research_linkedin_company.
    Returns: name, title, headline, skills, buying committee role.
    """
    from clients.apify_linkedin_person_client import scrape_linkedin_persons
    urls = [u.strip() for u in linkedin_urls_csv.split(",") if u.strip()][:8]
    if not urls:
        return "No URLs provided"

    profiles = await scrape_linkedin_persons(urls)
    lines = []
    for p in profiles:
        if p.success:
            role = classify_role(p.current_title or "")
            lines.append(
                f"Name: {p.full_name} | {p.current_title} @ {p.current_company}\n"
                f"  BuyingRole: {role}\n"
                f"  Headline: {p.headline}\n"
                f"  Skills: {p.top_skills}\n"
                f"  Location: {p.location}"
            )
    return "\n\n".join(lines) or "No profiles returned"


@tool
async def find_contacts(company_name: str, domain: str) -> str:
    """
    Find decision-maker contacts via Apollo.io and Exa people search.
    Returns names, titles, seniority, LinkedIn URLs, and buying committee roles.
    Call this in parallel with research_linkedin_company when possible.
    """
    from clients.apollo_client import search_people_at_company
    from clients.exa_client import search_leadership

    apollo_people, exa_people = await asyncio.gather(
        search_people_at_company(company_name=company_name, domain=domain, max_results=8),
        search_leadership(company_name=company_name),
        return_exceptions=True,
    )

    lines = ["=== Contacts ==="]
    try:
        if not isinstance(apollo_people, (Exception, type(None))) and apollo_people:
            for p in apollo_people:
                role = classify_role(p.get("title") or "")
                lines.append(f"[Apollo] {p.get('name','?')} | {p.get('title','?')} | {role} | {p.get('linkedin_url','')}")
    except Exception:
        lines.append("Apollo contacts: unavailable")

    try:
        if not isinstance(exa_people, (Exception, type(None))) and exa_people and getattr(exa_people, 'success', False):
            for r in exa_people.results[:3]:
                lines.append(f"[Exa] {r.title}\n  {(r.text or '')[:300]}")
    except Exception:
        lines.append("Exa people: unavailable")

    return "\n".join(lines)


# ── Orchestrator ───────────────────────────────────────────────────────────

def build_orchestrator(sender_context: str = "") -> Agent:
    model = BedrockModel(
        model_id=SONNET,
        cache_tools="default",
        cache_config=CacheConfig(strategy="auto"),
        temperature=0.2,
    )
    system = """You are a B2B sales intelligence researcher.

RESEARCH ORDER:
1. Call research_company_website first — firmographics, signals, LinkedIn URL, ICP score
2. Call research_linkedin_company if a LinkedIn URL was found
3. Call find_contacts — always (Apollo data)
4. Call enrich_person_profiles with top 5 decision-maker URLs from step 2

After research, return ONLY a valid JSON object — no markdown, no explanation, no code fences:
{
  "account_overview": "2-3 sentence company summary",
  "icp_score": 0,
  "icp_tier": "Strong Fit|Good Fit|Partial Fit|Poor Fit",
  "icp_dimensions": {"industry": 0, "size": 0, "tech": 0, "signals": 0},
  "buying_committee": [{"name": "", "title": "", "role": "", "priority": "High|Medium|Low", "engagement_angle": "", "linkedin_url": ""}],
  "signal_velocity": "surging|stable|declining",
  "signals": ["signal 1", "signal 2"],
  "outreach_angles": ["angle 1", "angle 2", "angle 3"],
  "cold_email": {"subject": "", "body": ""},
  "linkedin_message": "",
  "competitive_context": "",
  "next_action": ""
}

Use the sender's real name and company in cold_email and linkedin_message — never use placeholders like [Your name]."""

    if sender_context:
        system += f"\n\n{sender_context}"

    return Agent(
        name="lepa_orchestrator",
        model=model,
        tools=[research_company_website, research_linkedin_company,
               enrich_person_profiles, find_contacts],
        system_prompt=system,
    )


# ── Public API ─────────────────────────────────────────────────────────────

async def research_company(company_name: str, domain: str = "", tenant_id: str = "default", sender_name: str = "", force: bool = False) -> dict:
    account_id = domain or company_name.lower().replace(" ", "_")

    # Return cached result unless force=True
    if not force:
        try:
            from clients.db_client import _connect
            conn = await _connect()
            try:
                row = await conn.fetchrow("""
                    SELECT result_json FROM pipeline_runs
                    WHERE tenant_id = $1 AND account_id = $2 AND input_type = 'deep_research'
                    ORDER BY created_at DESC LIMIT 1
                """, tenant_id, account_id)
            finally:
                await conn.close()
            if row:
                val = row["result_json"]
                cached = json.loads(val) if isinstance(val, str) else dict(val)
                cached["_cached"] = True
                return cached
        except Exception:
            pass

    sender_context = ""
    try:
        from clients.db_client import get_business_profile, get_icp_profile
        bp = await get_business_profile(tenant_id)
        icp = await get_icp_profile(tenant_id)
        if bp:
            name = sender_name or bp.get("sender_name", "")
            sender_context += "SENDER CONTEXT (use in all outreach — never use placeholders):\n"
            sender_context += f"  Your name: {name}\n"
            sender_context += f"  Your company: {bp.get('business_name', '')}\n"
            sender_context += f"  Your product/service: {bp.get('product_service', '')}\n"
            sender_context += f"  Value proposition: {bp.get('value_proposition', '')}\n"
        if icp:
            sender_context += f"ICP: industries={icp.get('industries', [])}, size={icp.get('size_min', 0)}-{icp.get('size_max', 0)} employees\n"
    except Exception:
        pass

    orchestrator = build_orchestrator(sender_context)
    task = f"Research company: {company_name}" + (f"\nDomain: {domain}" if domain else "")
    result = await orchestrator.invoke_async(task)

    raw = str(result).strip()
    try:
        start = raw.find("{")
        end = raw.rfind("}") + 1
        data = json.loads(raw[start:end])
    except Exception:
        data = {"account_overview": raw, "error": "Could not parse structured response"}

    try:
        from clients.db_client import save_pipeline_run
        await save_pipeline_run(
            tenant_id=tenant_id,
            account_id=account_id,
            input_type="deep_research",
            result_json=data,
            confidence=0.9,
        )
    except Exception:
        pass

    return data


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="LEPA Research Agent")
    parser.add_argument("company")
    parser.add_argument("--domain", default="")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    result = asyncio.run(research_company(args.company, args.domain))
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(result.get("account_overview", result))
