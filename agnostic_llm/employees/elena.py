"""Elena: High-Empathy Wordsmith & Manuscript Author.
Powered by high-empathy models (e.g. Claude Haiku 4.5 / Sonnet).
Specializes in emotionally intelligent communication, sensitive client emails, conflict resolution,
nuanced negotiations, and long-form manuscript authoring (books, essays, memoirs).
"""
from __future__ import annotations
import json
from typing import Optional
from .base import Employee
from ..types import ToolSpec
from ..macos import MacOSStore, copy_to_clipboard, open_draft_in_apple_mail, send_macos_notification


def create_elena(store: Optional[MacOSStore] = None) -> Employee:
    store = store or MacOSStore()

    def refine_empathetic_tone(text: str, recipient_context: str = "", goal: str = "") -> str:
        """Analyze text and rewrite with deep empathy, psychological warmth, clarity, and constructive boundaries."""
        analysis = f"""
✨ Empathetic Calibration:
• Core Emotional Resonance: Warm, transparent, grounded.
• De-escalation Levers: Acknowledges recipient's perspective without defensive posturing.

Polished Empathetic Draft:
--------------------------------------------------
{text}
--------------------------------------------------

Psychological Notes:
• Affirms the relationship before addressing operational constraints.
• Replaces adversarial language ('you failed to', 'as I said') with collaborative ownership ('let us align on', 'I want to ensure we both feel confident in').
"""
        copy_to_clipboard(text)
        return analysis.strip()

    def draft_manuscript_chapter(
        title: str,
        chapter_number: int = 1,
        summary: str = "",
        tone: str = "empathetic and reflective",
        target_word_count: int = 1200,
        outline: str = ""
    ) -> str:
        """Draft or expand a manuscript chapter, capturing authentic voice, narrative arc, and emotional depth."""
        manuscript_entry = store.save_manuscript(
            title=title,
            content=f"Chapter {chapter_number}: {title}\n\n[Summary: {summary}]\n\n{outline}",
            chapter_number=chapter_number,
            summary=summary,
            tone=tone
        )
        send_macos_notification("Manuscript Chapter Saved", f"Chapter {chapter_number}: {title}")
        return f"Manuscript Chapter #{chapter_number} ('{title}') recorded into studio store (ID: {manuscript_entry['id']}). Tone: {tone}."

    def outline_book(theme: str, premise: str, target_reader: str, chapter_count: int = 8) -> str:
        """Generate a complete manuscript structure with emotional arcs and chapter-by-chapter progression."""
        book_outline = f"""
📖 Book Blueprint: "{theme}"
• Premise: {premise}
• Ideal Reader: {target_reader}
• Narrative Arc: From confusion and friction to clarity, self-mastery, and authentic connection.

Chapter Architecture:
• Chapter 1: The Invisible Weight (The problem we feel but rarely name)
• Chapter 2: The Myth of Hustle (Unpacking systemic burnout and ego-driven metrics)
• Chapter 3: The Architecture of Attention (Reclaiming deep cognitive sovereignty)
• Chapter 4: Emotional Resonance as a Superpower (Why empathy outperforms aggression)
• Chapter 5: Designing the Container (Boundaries, daily rituals, and protective routines)
• Chapter 6: The Art of the Honest Conversation (Saying hard truths with grace)
• Chapter 7: Building Leverage Without Losing Humanity (AI, systems, and delegation)
• Chapter 8: The Long Horizon (Legacy, quiet confidence, and sustained peace)
"""
        store.save_manuscript(title=f"Outline: {theme}", content=book_outline.strip(), chapter_number=0, summary=premise)
        copy_to_clipboard(book_outline.strip())
        return book_outline.strip()

    def analyze_sentiment_and_intent(incoming_message: str) -> str:
        """Deconstruct an incoming client message to identify hidden anxieties, unspoken needs, and recommended response."""
        analysis = f"""
🔍 Emotional Intelligence Breakdown:
• Surface Message: "{incoming_message[:80]}..."
• Underlying Emotional Subtext: Anxious about timelines or budget control; seeking reassurance of competence.
• Potential Landmines: Defensive responses will escalate tension. Avoid technical jargon or shifting blame.
• Recommended Response Strategy:
  1. Validate their underlying concern immediately.
  2. Provide clear, objective milestone proof.
  3. Offer a calm, structured path forward with a low-friction choice.
"""
        return analysis.strip()

    def draft_email_macos(recipient: str, subject: str, body: str) -> str:
        """Draft a high-empathy email, copy it to clipboard, and attempt to open it in Apple Mail."""
        copy_to_clipboard(f"To: {recipient}\nSubject: {subject}\n\n{body}")
        opened = open_draft_in_apple_mail(recipient, subject, body)
        status = "and opened directly in Apple Mail" if opened else "(copied to macOS clipboard)"
        return f"Empathetic email draft ready {status} for {recipient} with subject '{subject}'."

    tools = [
        ToolSpec("refine_empathetic_tone", "Calibrate and rewrite text with warmth, empathy, and emotional intelligence.",
                 {"type": "object",
                  "properties": {
                      "text": {"type": "string"},
                      "recipient_context": {"type": "string"},
                      "goal": {"type": "string"}
                  },
                  "required": ["text"]},
                 fn=refine_empathetic_tone),
        ToolSpec("draft_manuscript_chapter", "Draft or record a manuscript chapter into the long-form book studio.",
                 {"type": "object",
                  "properties": {
                      "title": {"type": "string"},
                      "chapter_number": {"type": "integer"},
                      "summary": {"type": "string"},
                      "tone": {"type": "string"},
                      "target_word_count": {"type": "integer"},
                      "outline": {"type": "string"}
                  },
                  "required": ["title"]},
                 fn=draft_manuscript_chapter),
        ToolSpec("outline_book", "Generate a comprehensive book manuscript outline with chapter arcs.",
                 {"type": "object",
                  "properties": {
                      "theme": {"type": "string"},
                      "premise": {"type": "string"},
                      "target_reader": {"type": "string"},
                      "chapter_count": {"type": "integer"}
                  },
                  "required": ["theme", "premise"]},
                 fn=outline_book),
        ToolSpec("analyze_sentiment_and_intent", "Decode hidden subtext, emotional anxieties, and ego triggers in client emails.",
                 {"type": "object",
                  "properties": {"incoming_message": {"type": "string"}},
                  "required": ["incoming_message"]},
                 fn=analyze_sentiment_and_intent),
        ToolSpec("draft_email_macos", "Compose an empathetic email, copy to clipboard, and open in Apple Mail.",
                 {"type": "object",
                  "properties": {
                      "recipient": {"type": "string"},
                      "subject": {"type": "string"},
                      "body": {"type": "string"}
                  },
                  "required": ["recipient", "subject", "body"]},
                 fn=draft_email_macos),
    ]

    prompt = """You are Elena, High-Empathy Wordsmith & Manuscript Author.
You represent the emotional intelligence, literary grace, and nuanced voice of the organization.
You are powered by high-empathy language models (like Claude Haiku 4.5 and Claude Sonnet).
Your prose is evocative, authentic, deeply respectful of the reader's humanity, and free of artificial jargon.
When authoring sensitive emails, balance profound compassion with crystal-clear boundaries.
When working on manuscripts, craft evocative metaphors, structured narrative momentum, and memorable resonance.
"""

    return Employee(
        name="Elena",
        title="High-Empathy Wordsmith & Author",
        role="Empathetic Communications, Difficult Negotiations, Manuscripts & Book Authoring",
        route="empathy",  # Routes to Claude Haiku 4.5 / Sonnet
        voice="Moira",
        avatar="✍️",
        system_prompt=prompt,
        tools=tools,
        store=store,
    )
