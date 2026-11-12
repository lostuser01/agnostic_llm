import io
import socket

import pytest

from agnostic_llm.integrations.credentials import EnvironmentCredentialStore
from agnostic_llm.integrations.http import ControlledOutboundHTTPClient, OutboundHTTPError
from agnostic_llm.integrations.metadata import ConnectionMetadata, OAuthMetadata
from agnostic_llm.integrations import (
    InMemoryEmailProvider,
    InMemorySocialProvider,
    ResearchResult,
    LeadEnrichment,
    CalendarEvent,
    TaskItem,
)
from agnostic_llm.employees import create_alex, create_morgan, create_taylor, create_elena, create_jack
from agnostic_llm.macos import MacOSStore


class FakeCredentials:
    def __init__(self, value=None):
        self.value = value

    def get(self, name, *, env_var=None):
        return self.value


def test_credentials_prefer_environment(monkeypatch):
    monkeypatch.setenv("EXAMPLE_TOKEN", "from-env")
    assert EnvironmentCredentialStore(FakeCredentials("from-keychain")).get(
        "provider.token", env_var="EXAMPLE_TOKEN"
    ) == "from-env"


def test_connection_metadata_contains_references_not_secrets():
    metadata = ConnectionMetadata(
        "github",
        credential_ref="GITHUB_TOKEN",
        auth_type="oauth",
        oauth=OAuthMetadata("https://github.com/login", "https://github.com/token", ("repo",)),
    )
    serialized = metadata.to_dict()
    assert serialized["credential_ref"] == "GITHUB_TOKEN"
    assert "secret" not in repr(serialized).lower()


def test_http_client_allowlist_and_private_ip_protection(monkeypatch):
    client = ControlledOutboundHTTPClient({"api.example.com"})
    monkeypatch.setattr(socket, "getaddrinfo", lambda *args, **kwargs: [(None, None, None, None, ("127.0.0.1", 443))])
    with pytest.raises(OutboundHTTPError, match="private or local"):
        client.get("https://api.example.com/data")
    with pytest.raises(OutboundHTTPError, match="allowlisted"):
        client.get("https://evil.example/data")


def test_http_client_limits_response_and_redacts_audit(monkeypatch):
    events = []

    class Response:
        status = 200
        headers = {"Content-Length": "20"}

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return None

    monkeypatch.setattr(socket, "getaddrinfo", lambda *args, **kwargs: [(None, None, None, None, ("93.184.216.34", 443))])
    client = ControlledOutboundHTTPClient(
        {"api.example.com"}, max_response_bytes=10, audit_hook=events.append, secret_values=("secret-token",)
    )
    monkeypatch.setattr(client._opener, "open", lambda *args, **kwargs: Response())
    with pytest.raises(OutboundHTTPError, match="size limit"):
        client.get("https://api.example.com/data", headers={"Authorization": "secret-token"})
    assert events[0]["headers"]["Authorization"] == "[REDACTED]"


class MockResearch:
    def search(self, query, max_results=5):
        return [ResearchResult("Acme", "https://example.test/acme", "Public company profile")]

    def enrich_lead(self, company, context=""):
        return LeadEnrichment(company, "Growing developer tools company", ("https://example.test/acme",))


class MockCalendar:
    def __init__(self):
        self.events = []
        self.tasks = []

    def list_events(self, date=""):
        return self.events

    def create_event(self, event):
        self.events.append(CalendarEvent(**{**event.__dict__, "provider_id": "event-1"}))
        return self.events[-1]

    def list_tasks(self, status="pending", category=""):
        return self.tasks

    def create_task(self, task):
        saved = TaskItem(**{**task.__dict__, "provider_id": "task-1"})
        self.tasks.append(saved)
        return saved

    def complete_task(self, task_id_or_title):
        return True


def test_employee_provider_contracts_are_mockable(tmp_path):
    store = MacOSStore(tmp_path / "employees.db")
    alex = create_alex(store, calendar_provider=MockCalendar())
    assert "event-1" in next(t for t in alex.tools if t.name == "schedule_meeting").fn(
        "Planning", "2026-11-12 10:00"
    )

    morgan = create_morgan(store, research_provider=MockResearch())
    research = next(t for t in morgan.tools if t.name == "research_web").fn("Acme")
    assert "https://example.test/acme" in research
    assert "Growing developer tools" in next(t for t in morgan.tools if t.name == "enrich_lead_from_web").fn("Acme")

    social = InMemorySocialProvider()
    taylor = create_taylor(store, social_provider=social)
    publish = next(t for t in taylor.tools if t.name == "publish_social_post")
    assert publish.approval_key == "social.publish"
    assert "provider ID" in publish.fn("linkedin", "Hello")

    email = InMemoryEmailProvider()
    elena = create_elena(store, email_provider=email)
    send = next(t for t in elena.tools if t.name == "send_email_provider")
    assert send.approval_key == "email.send"
    assert "sent:1" in send.fn("a@example.test", "Hi", "Hello")

    jack = create_jack(store)
    assert next(t for t in jack.tools if t.name == "create_github_pull_request").approval_key == "github.pull_request.create"


def test_external_defaults_are_disabled_without_network(tmp_path):
    store = MacOSStore(tmp_path / "offline.db")
    morgan = create_morgan(store)
    result = next(t for t in morgan.tools if t.name == "research_web").fn("anything")
    assert "not configured" in result
