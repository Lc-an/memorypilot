"""Persist source messages and append-only fact versions in SQLite."""

import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from uuid import uuid4

from memorypilot.schemas import CandidateFact, Evidence, Fact, Scope, normalize_time, now_iso


class Repository:
    def __init__(self, path: Path):
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        with self.connection() as db:
            db.execute("PRAGMA journal_mode=WAL")
            db.executescript("""
                CREATE TABLE IF NOT EXISTS source_events (
                    source_id TEXT PRIMARY KEY,
                    namespace TEXT NOT NULL, user_id TEXT NOT NULL, trip_id TEXT NOT NULL,
                    session_id TEXT NOT NULL, role TEXT NOT NULL, content TEXT NOT NULL,
                    timestamp TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS source_scope ON source_events
                    (namespace, user_id, trip_id, timestamp);
                CREATE TABLE IF NOT EXISTS fact_versions (
                    seq INTEGER PRIMARY KEY AUTOINCREMENT, fact_id TEXT UNIQUE NOT NULL,
                    namespace TEXT NOT NULL, user_id TEXT NOT NULL, trip_id TEXT NOT NULL,
                    attribute TEXT NOT NULL, value TEXT NOT NULL, known_at TEXT NOT NULL,
                    source_id TEXT NOT NULL REFERENCES source_events(source_id),
                    supersedes TEXT REFERENCES fact_versions(fact_id)
                );
                CREATE INDEX IF NOT EXISTS fact_scope ON fact_versions
                    (namespace, user_id, trip_id, attribute, known_at);
                CREATE TABLE IF NOT EXISTS runs (
                    run_id TEXT PRIMARY KEY, created_at TEXT NOT NULL, payload TEXT NOT NULL
                );
            """)

    @contextmanager
    def connection(self):
        db = sqlite3.connect(self.path, timeout=10)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys=ON")
        try:
            with db:
                yield db
        finally:
            db.close()

    @staticmethod
    def _scope(scope: Scope) -> tuple[str, str, str]:
        return scope.namespace, scope.user_id, scope.trip_id

    def add_event(
        self,
        scope: Scope,
        session_id: str,
        content: str,
        *,
        role: str = "user",
        timestamp: str | None = None,
        source_id: str | None = None,
    ) -> str:
        source_id = source_id or f"src_{uuid4().hex}"
        timestamp = normalize_time(timestamp or now_iso())
        with self.connection() as db:
            existing = db.execute(
                "SELECT * FROM source_events WHERE source_id=?", (source_id,)
            ).fetchone()
            if existing:
                expected = (*self._scope(scope), session_id, role, content, timestamp)
                actual = tuple(
                    existing[k]
                    for k in [
                        "namespace",
                        "user_id",
                        "trip_id",
                        "session_id",
                        "role",
                        "content",
                        "timestamp",
                    ]
                )
                if expected != actual:
                    raise ValueError("来源编号已经被不同的消息使用。")
                return source_id
            db.execute(
                "INSERT INTO source_events VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (source_id, *self._scope(scope), session_id, role, content, timestamp),
            )
        return source_id

    def read_evidence(self, scope: Scope, source_id: str) -> Evidence | None:
        with self.connection() as db:
            row = db.execute(
                """SELECT source_id, content AS text, timestamp FROM source_events
                   WHERE namespace=? AND user_id=? AND trip_id=? AND source_id=?""",
                (*self._scope(scope), source_id),
            ).fetchone()
        return Evidence(**dict(row)) if row else None

    def write_facts(
        self, scope: Scope, source_id: str, candidates: list[CandidateFact]
    ) -> list[Fact]:
        with self.connection() as db:
            # Serialize competing updates so that each version has a clear predecessor.
            db.execute("BEGIN IMMEDIATE")
            source = db.execute(
                """SELECT * FROM source_events
                   WHERE namespace=? AND user_id=? AND trip_id=? AND source_id=?""",
                (*self._scope(scope), source_id),
            ).fetchone()
            if not source or source["role"] != "user":
                raise ValueError("事实必须来自当前用户在当前范围内的消息。")
            attributes = [candidate.attribute for candidate in candidates]
            if len(attributes) != len(set(attributes)):
                raise ValueError("同一消息中发现重复属性；请先确认最终要求。")
            for candidate in candidates:
                if candidate.quote not in source["content"]:
                    raise ValueError("记忆引用不在原文中，已拒绝写入。")
                if candidate.value not in candidate.quote:
                    raise ValueError("第一版只接收原文中直接出现的事实值，不接受推断值。")
            results = []
            for candidate in candidates:
                previous = db.execute(
                    """SELECT * FROM fact_versions WHERE namespace=? AND user_id=? AND trip_id=?
                       AND attribute=? AND known_at<=? ORDER BY known_at DESC, seq DESC LIMIT 1""",
                    (*self._scope(scope), candidate.attribute, source["timestamp"]),
                ).fetchone()
                if previous and previous["value"] == candidate.value:
                    results.append(self._fact(previous))
                    continue
                fact = Fact(
                    fact_id=f"fact_{uuid4().hex}",
                    attribute=candidate.attribute,
                    value=candidate.value,
                    known_at=source["timestamp"],
                    source_id=source_id,
                    supersedes=previous["fact_id"] if previous else None,
                )
                db.execute(
                    """INSERT INTO fact_versions
                       (fact_id, namespace, user_id, trip_id, attribute, value,
                        known_at, source_id, supersedes) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        fact.fact_id,
                        *self._scope(scope),
                        fact.attribute,
                        fact.value,
                        fact.known_at,
                        fact.source_id,
                        fact.supersedes,
                    ),
                )
                results.append(fact)
        return results

    @staticmethod
    def _fact(row) -> Fact:
        return Fact(**{key: row[key] for key in Fact.model_fields})

    def facts(self, scope: Scope, *, history: bool = False, as_of: str | None = None) -> list[Fact]:
        cutoff = normalize_time(as_of or now_iso())
        with self.connection() as db:
            rows = db.execute(
                """SELECT * FROM fact_versions WHERE namespace=? AND user_id=? AND trip_id=?
                   AND known_at<=? ORDER BY known_at DESC, seq DESC""",
                (*self._scope(scope), cutoff),
            ).fetchall()
        if history:
            return [self._fact(row) for row in reversed(rows)]
        latest = {}
        for row in rows:
            latest.setdefault(row["attribute"], self._fact(row))
        return list(latest.values())

    def recent_events(self, scope: Scope, limit: int = 20) -> list[Evidence]:
        with self.connection() as db:
            rows = db.execute(
                """SELECT source_id, content AS text, timestamp FROM source_events
                   WHERE namespace=? AND user_id=? AND trip_id=? AND role='user'
                   ORDER BY timestamp DESC, rowid DESC LIMIT ?""",
                (*self._scope(scope), limit),
            ).fetchall()
        return [Evidence(**dict(row)) for row in rows]

    def save_run(self, run_id: str, payload: dict) -> None:
        with self.connection() as db:
            db.execute(
                "INSERT INTO runs VALUES (?, ?, ?)",
                (run_id, now_iso(), json.dumps(payload, ensure_ascii=False)),
            )
