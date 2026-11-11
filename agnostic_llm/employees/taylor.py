"""Taylor: Growth & Marketing Strategist.
Specializes in content marketing, viral social hooks, LinkedIn/X thought leadership,
audience acquisition, email newsletters, and content calendars.
"""
from __future__ import annotations
import datetime
from typing import Optional
from .base import Employee
from ..types import ToolSpec
from ..macos import MacOSStore, copy_to_clipboard, send_macos_notification


def create_taylor(store: Optional[MacOSStore] = None) -> Employee:
    store = store or MacOSStore()

    def generate_social_campaign(topic: str, target_audience: str, platform: str = "linkedin") -> str:
        """Create a multi-post social media campaign tailored to the target audience and platform."""
        campaign = f"""
📢 Social Campaign on '{topic}' for {target_audience} ({platform.upper()}):

[Post 1: The Counter-Intuitive Truth]
Most people think {topic} is about brute force or endless hours.
They're wrong.
Here is the exact playbook that changed how I approach it (and why the conventional advice fails):
1. Focus on signal over noise.
2. Build systems instead of relying on motivation.
3. Test fast, iterate in public.
What’s your biggest friction point with {topic}?

[Post 2: The Tactical Step-by-Step Breakdown]
If you want to master {topic} in 2026, here are the 3 non-negotiable levers:
• Lever A: Ruthless simplification.
• Lever B: Rapid customer feedback loops.
• Lever C: Modern AI leverage.
Bookmark this for your next project review.

[Post 3: The Case Study / Proof]
A quick breakdown of how applying {topic} saved 15+ hours a week and unlocked higher client retention.
Key lesson: When in doubt, eliminate friction for the user.
"""
        store.save_campaign(title=f"Campaign: {topic}", content=campaign.strip(), platform=platform)
        copy_to_clipboard(campaign.strip())
        return f"Campaign generated and saved to marketing store:\n\n{campaign.strip()}"

    def draft_newsletter(topic: str, key_takeaways: str, call_to_action: str = "") -> str:
        """Draft a high-engagement email newsletter edition with narrative hook, body, and CTA."""
        newsletter = f"""Subject: The real reason why {topic} matters right now

Hey friend,

Earlier this week, I was reflecting on {topic}.

We often get trapped in busywork, mistaking movement for progress. But if you strip away the complexity, it comes down to a few fundamental insights:

{key_takeaways}

My takeaway: Stop waiting for the 'ideal moment'. Build the prototype today.

{f'👉 Next Step: {call_to_action}' if call_to_action else 'Drop a reply and let me know your thoughts.'}

Until next week,
"""
        store.save_campaign(title=f"Newsletter: {topic}", content=newsletter.strip(), platform="newsletter")
        copy_to_clipboard(newsletter.strip())
        return f"Newsletter drafted and copied to clipboard:\n\n{newsletter.strip()}"

    def analyze_hook(hook_text: str) -> str:
        """Analyze a headline or hook for psychological impact, curiosity gap, and generate 3 viral alternatives."""
        words = len(hook_text.split())
        score = 8.5 if ("how" in hook_text.lower() or "why" in hook_text.lower() or any(c.isdigit() for c in hook_text)) else 7.0
        analysis = f"""
🪝 Hook Analysis for: "{hook_text}"
• Length: {words} words (Optimal: 6-12 words)
• Estimated Engagement Score: {score}/10
• Strengths: Clear topic clarity.
• Opportunities: Increase urgency or emotional contrast.

3 High-Converting Variations:
1. Curiosity Gap: "Why 90% of people fail at {hook_text} (and the 1 tweak that fixes it)"
2. Contrarian Truth: "Stop doing {hook_text} the hard way. Here’s the 2026 framework."
3. Proof & Story: "How we transformed {hook_text} in 7 days — without extra budget."
"""
        return analysis.strip()

    def build_content_calendar(niche: str, days_ahead: int = 7) -> str:
        """Generate a structured content calendar with post topics, formats, and optimal publishing cadence."""
        schedule = [f"📅 {days_ahead}-Day Content Cadence for '{niche}':"]
        days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        types = [
            ("Industry Insight / Contrarian Opinion", "LinkedIn"),
            ("Quick Tactical Tip / Framework", "X / Twitter"),
            ("Case Study / Client Win Breakdown", "LinkedIn"),
            ("Deep-Dive Essay / Weekly Newsletter", "Substack / Email"),
            ("Behind-the-scenes / Lesson Learned", "All Channels"),
            ("Ask Me Anything / Community Discussion", "X / Threads"),
            ("Weekly Review & Next Week Horizon", "Newsletter"),
        ]
        for i in range(min(days_ahead, 7)):
            d = days[i % 7]
            theme, channel = types[i % len(types)]
            schedule.append(f"• {d}: [{channel}] {theme} in {niche}")
        return "\n".join(schedule)

    tools = [
        ToolSpec("generate_social_campaign", "Generate multi-post social media campaigns for LinkedIn/X.",
                 {"type": "object",
                  "properties": {
                      "topic": {"type": "string"},
                      "target_audience": {"type": "string"},
                      "platform": {"type": "string", "enum": ["linkedin", "x", "all"]}
                  },
                  "required": ["topic", "target_audience"]},
                 fn=generate_social_campaign, approval_key="marketing.campaign.save",
                 approval_description="Save a marketing campaign to the local workspace"),
        ToolSpec("draft_newsletter", "Draft a narrative newsletter edition with hook and CTA.",
                 {"type": "object",
                  "properties": {
                      "topic": {"type": "string"},
                      "key_takeaways": {"type": "string"},
                      "call_to_action": {"type": "string"}
                  },
                  "required": ["topic", "key_takeaways"]},
                 fn=draft_newsletter, approval_key="marketing.newsletter.save",
                 approval_description="Save a newsletter draft to the local workspace"),
        ToolSpec("analyze_hook", "Analyze hook strength and provide 3 higher-converting alternatives.",
                 {"type": "object",
                  "properties": {"hook_text": {"type": "string"}},
                  "required": ["hook_text"]},
                 fn=analyze_hook),
        ToolSpec("build_content_calendar", "Build a structured content schedule across channels.",
                 {"type": "object",
                  "properties": {
                      "niche": {"type": "string"},
                      "days_ahead": {"type": "integer"}
                  },
                  "required": ["niche"]},
                 fn=build_content_calendar),
    ]

    prompt = """You are Taylor, Growth & Marketing Strategist.
Your mission is to expand the user's audience, attract inbound opportunities, and craft captivating narratives.
You understand modern organic distribution algorithms, curiosity psychology, and conversion-focused storytelling.
Avoid generic corporate fluff; write crisp, human, high-retention content.
"""

    return Employee(
        name="Taylor",
        title="Marketing & Growth Lead",
        role="Content Marketing, Social Media Strategy, Newsletters & Hook Optimization",
        route="default",
        voice="Karen",
        avatar="🚀",
        system_prompt=prompt,
        tools=tools,
        store=store,
    )

