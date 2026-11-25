"""Профили пользователей в SQLite."""

from __future__ import annotations

import datetime as dt
from pathlib import Path

import aiosqlite

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY,
    group_name TEXT,
    created_at TEXT NOT NULL,
    last_seen TEXT NOT NULL
)
"""


class Users:
    def __init__(self, path: str | Path = ":memory:"):
        self._path = str(path)
        self._db: aiosqlite.Connection | None = None

    async def open(self) -> None:
        if self._path != ":memory:":
            Path(self._path).parent.mkdir(parents=True, exist_ok=True)
        self._db = await aiosqlite.connect(self._path)
        await self._db.execute(SCHEMA)
        await self._db.commit()

    async def close(self) -> None:
        if self._db is not None:
            await self._db.close()
            self._db = None

    @property
    def db(self) -> aiosqlite.Connection:
        if self._db is None:
            raise RuntimeError("Users.open() не вызван")
        return self._db

    async def group(self, user_id: int) -> str | None:
        async with self.db.execute("SELECT group_name FROM users WHERE id = ?", (user_id,)) as cursor:
            row = await cursor.fetchone()
        return row[0] if row else None

    async def set_group(self, user_id: int, group: str) -> None:
        now = _now()
        await self.db.execute(
            "INSERT INTO users (id, group_name, created_at, last_seen) VALUES (?, ?, ?, ?) "
            "ON CONFLICT(id) DO UPDATE SET group_name = excluded.group_name, last_seen = excluded.last_seen",
            (user_id, group, now, now),
        )
        await self.db.commit()

    async def touch(self, user_id: int) -> None:
        await self.db.execute("UPDATE users SET last_seen = ? WHERE id = ?", (_now(), user_id))
        await self.db.commit()

    async def stats(self, since: dt.datetime) -> dict:
        async with self.db.execute(
            "SELECT COUNT(*), SUM(last_seen >= ?) FROM users WHERE group_name IS NOT NULL",
            (since.isoformat(),),
        ) as cursor:
            total, active = await cursor.fetchone()
        async with self.db.execute(
            "SELECT group_name, COUNT(*) FROM users WHERE group_name IS NOT NULL "
            "GROUP BY group_name ORDER BY COUNT(*) DESC, group_name LIMIT 10"
        ) as cursor:
            top = await cursor.fetchall()
        return {"total": total, "active": active or 0, "groups": top}


def _now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()
