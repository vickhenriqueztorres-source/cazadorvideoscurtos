from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import aiosqlite

from render_inspector.events import InspectorEvent
from render_inspector.models import AnalysisResult, SessionInfo

SCHEMA = """
CREATE TABLE IF NOT EXISTS sessions (session_id TEXT PRIMARY KEY, status TEXT NOT NULL, started_at TEXT NOT NULL, ended_at TEXT, metadata_json TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS events (id INTEGER PRIMARY KEY AUTOINCREMENT, event_type TEXT NOT NULL, target_id TEXT, cdp_session_id TEXT, context_id INTEGER, received_at TEXT NOT NULL, payload_json TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS events_type_time ON events(event_type, received_at);
CREATE TABLE IF NOT EXISTS analyses (analysis_id TEXT PRIMARY KEY, status TEXT NOT NULL, created_at TEXT NOT NULL, result_json TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS artifacts (id INTEGER PRIMARY KEY AUTOINCREMENT, analysis_id TEXT, path TEXT NOT NULL, sha256 TEXT NOT NULL, size INTEGER NOT NULL, media_type TEXT);
CREATE TABLE IF NOT EXISTS errors (id INTEGER PRIMARY KEY AUTOINCREMENT, component TEXT NOT NULL, timestamp TEXT NOT NULL, error TEXT NOT NULL, stack TEXT);
"""


class SessionStore:
    def __init__(self, session_dir: Path) -> None:
        self.session_dir = session_dir
        self.db_path = session_dir / "session.db"
        self.db: aiosqlite.Connection | None = None

    async def open(self, session: SessionInfo) -> None:
        self.session_dir.mkdir(parents=True, exist_ok=True)
        self.db = await aiosqlite.connect(self.db_path)
        await self.db.executescript(SCHEMA)
        await self.db.execute(
            "UPDATE sessions SET status='ABORTED', ended_at=? WHERE status='RUNNING'",
            (datetime.now(UTC).isoformat(),),
        )
        await self.db.execute(
            "INSERT OR REPLACE INTO sessions(session_id,status,started_at,metadata_json) VALUES(?,?,?,?)",
            (
                session.session_id,
                "RUNNING",
                session.started_at.isoformat(),
                session.model_dump_json(),
            ),
        )
        await self.db.commit()

    async def save_event(self, event: InspectorEvent) -> None:
        if self.db is None:
            return
        await self.db.execute(
            "INSERT INTO events(event_type,target_id,cdp_session_id,context_id,received_at,payload_json) VALUES(?,?,?,?,?,?)",
            (
                event.type,
                event.target_id,
                event.session_id,
                event.context_id,
                event.received_at,
                json.dumps(event.payload, ensure_ascii=False),
            ),
        )
        if event.type in {
            "TARGET_SELECTED",
            "ANALYSIS_COMPLETED",
            "HOOK_FAILED",
            "BRIDGE_DECODE_FAILED",
        }:
            await self.db.commit()

    async def close(self, status: str = "STOPPED") -> None:
        if self.db is None:
            return
        await self.db.execute(
            "UPDATE sessions SET status=?, ended_at=? WHERE status='RUNNING'",
            (status, datetime.now(UTC).isoformat()),
        )
        await self.db.commit()
        await self.db.close()
        self.db = None

    async def save_analysis(self, result: AnalysisResult) -> None:
        if self.db is None:
            return
        await self.db.execute(
            "INSERT OR REPLACE INTO analyses(analysis_id,status,created_at,result_json) VALUES(?,?,?,?)",
            (
                result.analysis_id,
                result.status,
                result.created_at.isoformat(),
                result.model_dump_json(),
            ),
        )
        await self.db.executemany(
            "INSERT INTO artifacts(analysis_id,path,sha256,size,media_type) VALUES(?,?,?,?,?)",
            [
                (result.analysis_id, item.path, item.sha256, item.size, item.media_type)
                for item in result.artifacts
            ],
        )
        await self.db.commit()

    async def event_counts(self) -> dict[str, int]:
        if self.db is None:
            return {}
        cursor = await self.db.execute(
            "SELECT event_type, COUNT(*) FROM events GROUP BY event_type"
        )
        return {str(row[0]): int(row[1]) for row in await cursor.fetchall()}
