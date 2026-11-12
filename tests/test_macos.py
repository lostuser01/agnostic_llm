import pytest
from agnostic_llm.macos import MacOSStore, copy_to_clipboard, get_clipboard, send_macos_notification


@pytest.fixture
def store(tmp_path):
    return MacOSStore(db_path=tmp_path / "test_macos.db")


def test_calendar_store(store):
    ev = store.add_event(title="Quarterly Review", start_time="2026-11-20 14:00", duration_minutes=45, location="Cupertino")
    assert ev["id"] is not None
    events = store.list_events(date_prefix="2026-11-20")
    assert len(events) == 1
    assert events[0]["title"] == "Quarterly Review"


def test_task_store(store):
    t = store.create_task(title="Prepare pitch deck", priority="high", due_date="2026-11-15")
    assert t["status"] == "pending"

    tasks = store.list_tasks(status="pending")
    assert len(tasks) == 1
    assert tasks[0]["title"] == "Prepare pitch deck"

    ok = store.complete_task(t["id"])
    assert ok is True
    pending_after = store.list_tasks(status="pending")
    assert len(pending_after) == 0


def test_crm_leads_store(store):
    lead = store.add_lead(client_name="Acme Corp", estimated_value="$25,000", status="lead")
    assert lead["id"] is not None

    leads = store.list_leads()
    assert len(leads) == 1
    assert leads[0]["client_name"] == "Acme Corp"

    updated = store.update_lead(lead["id"], status="won", notes="Contract signed")
    assert updated is True
    won_leads = store.list_leads(status="won")
    assert len(won_leads) == 1


def test_clipboard_fallback():
    msg = "Agnostic AI Clipboard Test 123"
    copy_to_clipboard(msg)
    retrieved = get_clipboard()
    assert retrieved == msg


def test_notification_fallback():
    res = send_macos_notification("Test Title", "Test Message")
    assert isinstance(res, bool)


def test_database_backup_is_consistent(store, tmp_path):
    store.create_task(title="Backup me")
    destination = store.backup_database(tmp_path / "backups" / "snapshot.db")
    backup = MacOSStore(destination)
    assert backup.list_tasks()[0]["title"] == "Backup me"
    assert destination.exists()

