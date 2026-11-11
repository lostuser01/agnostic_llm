"""Morgan: Freelance & Business Development Hunter.
Specializes in finding freelance clients, lead generation, pitching, closing proposals,
rate calculations, client objection handling, and pipeline CRM tracking.
"""
from __future__ import annotations
import json
from typing import Optional
from .base import Employee
from ..types import ToolSpec
from ..macos import MacOSStore, copy_to_clipboard, send_macos_notification


def create_morgan(store: Optional[MacOSStore] = None) -> Employee:
    store = store or MacOSStore()

    def add_lead(
        client_name: str,
        company: str = "",
        project_scope: str = "",
        estimated_value: str = "$0",
        status: str = "lead",
        notes: str = ""
    ) -> str:
        """Add a prospective freelance client to the CRM pipeline (status: lead, pitched, negotiating, won, lost)."""
        lead = store.add_lead(
            client_name=client_name,
            company=company,
            project_scope=project_scope,
            estimated_value=estimated_value,
            status=status,
            notes=notes
        )
        send_macos_notification("New Lead Added", f"{client_name} ({company}) - {estimated_value}")
        return f"Lead #{lead['id']} recorded: {client_name} ({company}) | Scope: {project_scope} | Value: {estimated_value} | Status: {status.upper()}"

    def list_leads(status: str = "all") -> str:
        """List active prospective clients and their deal stage in the CRM."""
        leads = store.list_leads(status=status)
        if not leads:
            return f"No leads found with status '{status}'."
        lines = [f"💼 Active Pipeline ({len(leads)} leads):"]
        for d in leads:
            lines.append(f"  • #{d['id']} [{d['status'].upper()}] {d['client_name']} ({d['company']}) - {d['estimated_value']} | {d['project_scope']}")
            if d.get("notes"):
                lines.append(f"    Notes: {d['notes']}")
        return "\n".join(lines)

    def update_lead(lead_id: int, status: str = "", notes: str = "") -> str:
        """Update a deal's status or notes in the CRM."""
        ok = store.update_lead(lead_id=lead_id, status=status if status else None, notes=notes if notes else None)
        if ok:
            return f"Lead #{lead_id} updated successfully."
        return f"Could not find lead #{lead_id} to update."

    def calculate_rate_quote(hourly_rate: float, estimated_hours: float, value_markup_percentage: float = 25.0) -> str:
        """Calculate structured freelance project pricing tiers (Base, Recommended Value, Premium Retainer)."""
        base_cost = hourly_rate * estimated_hours
        value_price = base_cost * (1.0 + (value_markup_percentage / 100.0))
        premium_price = value_price * 1.5

        quote = f"""
💰 Freelance Pricing Tiers:
• Tier 1 (Cost-Plus Base): ${base_cost:,.2f}
  - Scope: Core deliverables only, standard turnaround.
• Tier 2 (Value-Aligned - RECOMMENDED): ${value_price:,.2f}
  - Scope: Complete project, revisions, priority communication, 30 days post-launch support.
• Tier 3 (Premium Turnkey + Advisory): ${premium_price:,.2f}
  - Scope: Everything in Tier 2 + strategic advisory + fast-track turnaround + ongoing maintenance.
"""
        return quote.strip()

    def draft_pitch_proposal(
        client_name: str,
        client_pain_point: str,
        proposed_solution: str,
        pricing: str,
        timeline: str = "2-3 weeks"
    ) -> str:
        """Draft a high-converting, value-driven cold pitch or freelance project proposal."""
        pitch = f"""Subject: Quick question regarding {client_pain_point} at your business

Hi {client_name},

I’ve been following your work and noticed that {client_pain_point} might be creating friction or holding back your growth.

I specialize in solving exactly this. Recently, I built a solution focused on {proposed_solution}, which delivered measurable ROI without dragging out development cycles.

Here is how we could approach this:
1. Quick Audit & Architecture: Identify high-impact bottlenecks.
2. Direct Implementation ({timeline}): Deliver tested, production-ready solution.
3. Launch & Handoff: Seamless onboarding and documentation.

Investment: {pricing}
Timeline: {timeline}

Would you be open to a brief 10-minute chat this Thursday at 2 PM to explore if this is a fit?

Best regards,
"""
        copy_to_clipboard(pitch.strip())
        return f"Pitch drafted and copied to macOS clipboard:\n\n{pitch.strip()}"

    def find_client_targets(niche: str, skills: str, platform: str = "all") -> str:
        """Generate targeted freelance outreach strategy, search queries, and high-probability client niches."""
        strategy = f"""
🎯 Freelance Acquisition Blueprint for '{niche}' ({skills}):
1. High-Intent Platforms to Target:
   • {platform.capitalize() if platform != 'all' else 'LinkedIn Sales Navigator, Upwork Enterprise, Indie Hackers, Wellfound'}
2. Search Operators & Boolean Queries:
   • `"{niche}" AND ("looking for" OR "hiring" OR "contractor" OR "freelancer") AND "{skills}"`
   • `site:linkedin.com/jobs "{niche}" contract`
3. Ideal Client Profile (ICP):
   • Bootstrapped Founders & Seed-to-Series-A Startups who need senior execution without full-time overhead.
   • Agencies experiencing capacity overflow looking for reliable white-label contractors.
4. Pitch Angle:
   • Don't sell "hours" — sell "reduced cycle time", "faster time to market", or "revenue unlocks".
"""
        return strategy.strip()

    tools = [
        ToolSpec("add_lead", "Record a new prospective client in the CRM pipeline.",
                 {"type": "object",
                  "properties": {
                      "client_name": {"type": "string"},
                      "company": {"type": "string"},
                      "project_scope": {"type": "string"},
                      "estimated_value": {"type": "string"},
                      "status": {"type": "string", "enum": ["lead", "pitched", "negotiating", "won", "lost"]},
                      "notes": {"type": "string"}
                  },
                  "required": ["client_name"]},
                 fn=add_lead, approval_key="crm.lead.create",
                 approval_description="Create a lead in the CRM pipeline"),
        ToolSpec("list_leads", "List active leads and opportunities from the CRM.",
                 {"type": "object",
                  "properties": {"status": {"type": "string", "enum": ["lead", "pitched", "negotiating", "won", "lost", "all"]}}},
                 fn=list_leads),
        ToolSpec("update_lead", "Update stage or notes for a lead in the CRM.",
                 {"type": "object",
                  "properties": {
                      "lead_id": {"type": "integer"},
                      "status": {"type": "string"},
                      "notes": {"type": "string"}
                  },
                  "required": ["lead_id"]},
                 fn=update_lead, approval_key="crm.lead.update",
                 approval_description="Update a CRM lead status or notes"),
        ToolSpec("draft_pitch_proposal", "Draft a high-converting cold pitch or client proposal and copy to clipboard.",
                 {"type": "object",
                  "properties": {
                      "client_name": {"type": "string"},
                      "client_pain_point": {"type": "string"},
                      "proposed_solution": {"type": "string"},
                      "pricing": {"type": "string"},
                      "timeline": {"type": "string"}
                  },
                  "required": ["client_name", "client_pain_point", "proposed_solution", "pricing"]},
                 fn=draft_pitch_proposal),
        ToolSpec("calculate_rate_quote", "Calculate tiered project pricing based on hours and value markup.",
                 {"type": "object",
                  "properties": {
                      "hourly_rate": {"type": "number"},
                      "estimated_hours": {"type": "number"},
                      "value_markup_percentage": {"type": "number"}
                  },
                  "required": ["hourly_rate", "estimated_hours"]},
                 fn=calculate_rate_quote),
        ToolSpec("find_client_targets", "Generate lead search strategies and boolean search queries for freelance niches.",
                 {"type": "object",
                  "properties": {
                      "niche": {"type": "string"},
                      "skills": {"type": "string"},
                      "platform": {"type": "string"}
                  },
                  "required": ["niche", "skills"]},
                 fn=find_client_targets),
    ]

    prompt = """You are Morgan, Business Development & Freelance Hunter.
Your mission is to win lucrative freelance clients, position the user as an indispensable expert, draft irresistible pitches, and close high-ticket deals.
You never sell low-margin commodities; you emphasize value pricing, client pain resolution, and clear ROI.
When drafting pitches, keep them punchy, tailored, and action-oriented.
"""

    return Employee(
        name="Morgan",
        title="Freelance & BizDev Hunter",
        role="Client Acquisition, Cold Pitching, Deal Negotiation & CRM Management",
        route="default",
        voice="Daniel",
        avatar="💼",
        system_prompt=prompt,
        tools=tools,
        store=store,
    )

