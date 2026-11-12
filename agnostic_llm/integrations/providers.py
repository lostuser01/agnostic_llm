"""Mockable employee integration contracts.

These contracts intentionally contain no SDK dependencies.  Production adapters
can be supplied by an application, while the employee defaults remain offline.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol, Sequence


class IntegrationNotConfigured(RuntimeError):
    pass


@dataclass(frozen=True)
class ResearchResult:
    title: str
    url: str
    snippet: str = ""


@dataclass(frozen=True)
class LeadEnrichment:
    company: str
    summary: str
    sources: tuple[str, ...] = ()


class BrowserResearchProvider(Protocol):
    """Read-only web research; implementations must not mutate remote systems."""

    def search(self, query: str, max_results: int = 5) -> Sequence[ResearchResult]: ...
    def enrich_lead(self, company: str, context: str = "") -> LeadEnrichment: ...


class DisabledBrowserResearchProvider:
    def search(self, query: str, max_results: int = 5) -> Sequence[ResearchResult]:
        raise IntegrationNotConfigured("Morgan browser research is not configured")

    def enrich_lead(self, company: str, context: str = "") -> LeadEnrichment:
        raise IntegrationNotConfigured("Morgan lead enrichment is not configured")


class ReadOnlyWebResearchProvider:
    """Opt-in adapter driven by injected GET/search callables.

    Keeping transport injection here prevents accidental network access in the
    default application and lets deployments use the constrained HTTP client.
    """

    def __init__(self, search_fn: Any, enrich_fn: Any | None = None):
        self.search_fn = search_fn
        self.enrich_fn = enrich_fn

    def search(self, query: str, max_results: int = 5) -> Sequence[ResearchResult]:
        return tuple(self.search_fn(query, max_results))

    def enrich_lead(self, company: str, context: str = "") -> LeadEnrichment:
        if self.enrich_fn is None:
            results = self.search(company, 3)
            return LeadEnrichment(company, "\n".join(result.snippet for result in results),
                                  tuple(result.url for result in results))
        return self.enrich_fn(company, context)


@dataclass(frozen=True)
class CalendarEvent:
    title: str
    start_time: str
    duration_minutes: int = 60
    location: str = ""
    notes: str = ""
    attendees: str = ""
    provider_id: str | None = None


@dataclass(frozen=True)
class TaskItem:
    title: str
    priority: str = "medium"
    due_date: str = ""
    category: str = "General"
    status: str = "pending"
    provider_id: str | None = None


class CalendarTaskProvider(Protocol):
    def list_events(self, date: str = "") -> Sequence[CalendarEvent]: ...
    def create_event(self, event: CalendarEvent) -> CalendarEvent: ...
    def list_tasks(self, status: str = "pending", category: str = "") -> Sequence[TaskItem]: ...
    def create_task(self, task: TaskItem) -> TaskItem: ...
    def complete_task(self, task_id_or_title: str) -> bool: ...


class LocalCalendarTaskProvider:
    """Adapter preserving the existing local SQLite calendar/task behavior."""

    def __init__(self, store: Any):
        self.store = store

    def list_events(self, date: str = "") -> Sequence[CalendarEvent]:
        return [
            CalendarEvent(
                title=row["title"], start_time=row["start_time"],
                duration_minutes=row["duration_minutes"], location=row["location"],
                notes=row["notes"], attendees=row["attendees"], provider_id=str(row["id"]),
            )
            for row in self.store.list_events(date_prefix=date or None)
        ]

    def create_event(self, event: CalendarEvent) -> CalendarEvent:
        row = self.store.add_event(event.title, event.start_time, event.duration_minutes,
                                   event.location, event.notes, event.attendees)
        return CalendarEvent(**{key: row[key] for key in (
            "title", "start_time", "duration_minutes", "location", "notes", "attendees"
        )}, provider_id=str(row["id"]))

    def list_tasks(self, status: str = "pending", category: str = "") -> Sequence[TaskItem]:
        return [
            TaskItem(title=row["title"], priority=row["priority"], due_date=row["due_date"],
                     category=row["category"], status=row["status"], provider_id=str(row["id"]))
            for row in self.store.list_tasks(status=status, category=category or None)
        ]

    def create_task(self, task: TaskItem) -> TaskItem:
        row = self.store.create_task(task.title, task.priority, task.due_date, task.category)
        return TaskItem(title=row["title"], priority=row["priority"], due_date=row["due_date"],
                        category=row["category"], status=row["status"], provider_id=str(row["id"]))

    def complete_task(self, task_id_or_title: str) -> bool:
        return self.store.complete_task(task_id_or_title)


@dataclass(frozen=True)
class SocialPost:
    platform: str
    content: str
    scheduled_for: str = ""
    provider_id: str | None = None


@dataclass(frozen=True)
class SocialAnalytics:
    platform: str
    impressions: int = 0
    engagements: int = 0
    clicks: int = 0
    raw: dict[str, Any] = field(default_factory=dict)


class SocialPublishingProvider(Protocol):
    def publish(self, post: SocialPost) -> SocialPost: ...
    def analytics(self, platform: str, post_id: str = "") -> SocialAnalytics: ...


class DisabledSocialPublishingProvider:
    def publish(self, post: SocialPost) -> SocialPost:
        raise IntegrationNotConfigured("Taylor social publishing is not configured")

    def analytics(self, platform: str, post_id: str = "") -> SocialAnalytics:
        raise IntegrationNotConfigured("Taylor social analytics is not configured")


@dataclass(frozen=True)
class EmailDraft:
    recipient: str
    subject: str
    body: str
    provider_id: str | None = None


class EmailProvider(Protocol):
    def draft(self, email: EmailDraft) -> EmailDraft: ...
    def send(self, email: EmailDraft) -> str: ...


class DocumentStorage(Protocol):
    def save(self, name: str, content: str, metadata: dict[str, Any] | None = None) -> str: ...


class DisabledEmailProvider:
    def draft(self, email: EmailDraft) -> EmailDraft:
        raise IntegrationNotConfigured("Elena email provider is not configured")

    def send(self, email: EmailDraft) -> str:
        raise IntegrationNotConfigured("Elena email provider is not configured")


class LocalDocumentStorage:
    def __init__(self, root: Path):
        self.root = Path(root).expanduser().resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def save(self, name: str, content: str, metadata: dict[str, Any] | None = None) -> str:
        path = (self.root / Path(name).name).resolve()
        if path.parent != self.root:
            raise ValueError("document must remain inside configured storage")
        path.write_text(content, encoding="utf-8")
        return str(path)


class GitHubProvider(Protocol):
    def repository(self, owner: str, name: str) -> dict[str, Any]: ...
    def create_pull_request(self, owner: str, name: str, title: str, head: str, base: str, body: str = "") -> dict[str, Any]: ...
    def run_ci(self, owner: str, name: str, ref: str = "") -> dict[str, Any]: ...
    def ci_status(self, owner: str, name: str, ref: str = "") -> dict[str, Any]: ...


class DisabledGitHubProvider:
    def _missing(self):
        raise IntegrationNotConfigured("Jack GitHub integration is not configured")

    def repository(self, owner: str, name: str) -> dict[str, Any]:
        self._missing()

    def create_pull_request(self, owner: str, name: str, title: str, head: str, base: str, body: str = "") -> dict[str, Any]:
        self._missing()

    def run_ci(self, owner: str, name: str, ref: str = "") -> dict[str, Any]:
        self._missing()

    def ci_status(self, owner: str, name: str, ref: str = "") -> dict[str, Any]:
        self._missing()


class InMemorySocialProvider:
    def __init__(self):
        self.posts: list[SocialPost] = []

    def publish(self, post: SocialPost) -> SocialPost:
        saved = SocialPost(post.platform, post.content, post.scheduled_for, str(len(self.posts) + 1))
        self.posts.append(saved)
        return saved

    def analytics(self, platform: str, post_id: str = "") -> SocialAnalytics:
        count = sum(post.platform == platform for post in self.posts)
        return SocialAnalytics(platform, impressions=count, engagements=count)


class InMemoryEmailProvider:
    def __init__(self):
        self.drafts: list[EmailDraft] = []
        self.sent: list[EmailDraft] = []

    def draft(self, email: EmailDraft) -> EmailDraft:
        saved = EmailDraft(email.recipient, email.subject, email.body, str(len(self.drafts) + 1))
        self.drafts.append(saved)
        return saved

    def send(self, email: EmailDraft) -> str:
        self.sent.append(email)
        return f"sent:{len(self.sent)}"
