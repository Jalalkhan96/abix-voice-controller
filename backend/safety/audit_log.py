from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from dataclasses import dataclass


@dataclass
class AuditEntry:
    id: int | None
    timestamp: str
    transcript: str
    intent: str
    tier: int
    outcome: str
    details: str


class AuditLog:
    def __init__(self, db_path: str = "data/audit.db") -> None:
        self._db_path = Path(db_path)
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self._db_path))
        self._conn.row_factory = sqlite3.Row
        self._create_table()

    def _create_table(self) -> None:
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS audit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                transcript TEXT NOT NULL,
                intent TEXT NOT NULL,
                tier INTEGER NOT NULL,
                outcome TEXT NOT NULL,
                details TEXT DEFAULT ''
            )
            """
        )
        self._conn.commit()

    def log(
        self,
        transcript: str,
        intent: str,
        tier: int,
        outcome: str,
        details: str = "",
    ) -> AuditEntry:
        now = datetime.now(timezone.utc).isoformat()
        cursor = self._conn.execute(
            "INSERT INTO audit_log (timestamp, transcript, intent, tier, outcome, details) VALUES (?, ?, ?, ?, ?, ?)",
            (now, transcript, intent, tier, outcome, details),
        )
        self._conn.commit()
        return AuditEntry(
            id=cursor.lastrowid,
            timestamp=now,
            transcript=transcript,
            intent=intent,
            tier=tier,
            outcome=outcome,
            details=details,
        )

    def get_recent(self, limit: int = 50) -> list[dict[str, str | int]]:
        cursor = self._conn.execute(
            "SELECT * FROM audit_log ORDER BY id DESC LIMIT ?", (limit,)
        )
        return [dict(row) for row in cursor.fetchall()]

    def search(self, query: str, limit: int = 50) -> list[dict[str, str | int]]:
        cursor = self._conn.execute(
            "SELECT * FROM audit_log WHERE transcript LIKE ? OR intent LIKE ? ORDER BY id DESC LIMIT ?",
            (f"%{query}%", f"%{query}%", limit),
        )
        return [dict(row) for row in cursor.fetchall()]

    def close(self) -> None:
        self._conn.close()
