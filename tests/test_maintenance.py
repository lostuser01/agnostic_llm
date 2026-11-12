from agnostic_llm.macos import MacOSStore
from agnostic_llm.maintenance import backup_database, restore_database


def test_database_backup_and_restore(tmp_path):
    source = tmp_path / "source.db"
    backup = tmp_path / "backups" / "snapshot.db"
    restored = tmp_path / "restored.db"
    store = MacOSStore(source)
    store.create_task("Back up this data")

    backup_database(source, backup)
    restored_store = MacOSStore(restored)
    restore_database(backup, restored)

    assert restored_store.list_tasks(status="all")[0]["title"] == "Back up this data"
