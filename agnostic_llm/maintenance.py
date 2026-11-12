"""Local database backup and restore helpers."""
from __future__ import annotations

import sqlite3
from pathlib import Path


def backup_database(source: Path, destination: Path) -> Path:
    """Create a consistent SQLite backup without copying a live file directly."""
    source = Path(source)
    destination = Path(destination)
    if not source.exists():
        raise FileNotFoundError(source)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(str(source)) as source_db, sqlite3.connect(str(destination)) as backup_db:
        source_db.backup(backup_db)
    return destination


def restore_database(source: Path, destination: Path) -> Path:
    """Restore a SQLite backup into the application database."""
    source = Path(source)
    destination = Path(destination)
    if not source.exists():
        raise FileNotFoundError(source)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(str(source)) as backup_db, sqlite3.connect(str(destination)) as destination_db:
        backup_db.backup(destination_db)
    return destination
