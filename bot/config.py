"""Настройки из переменных окружения (и файла .env, если он есть)."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from zoneinfo import ZoneInfo

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent


@dataclass(frozen=True)
class Config:
    token: str
    admin_ids: frozenset[int] = frozenset()
    timezone: ZoneInfo = field(default_factory=lambda: ZoneInfo("Europe/Moscow"))
    db_path: Path = ROOT / "data" / "bot.sqlite3"
    schedule_path: Path = ROOT / "data" / "schedule.json"
    http_host: str = "127.0.0.1"
    http_port: int = 8080
    message_interval: float = 0.5


def load_config() -> Config:
    load_dotenv()
    token = os.getenv("BOT_TOKEN", "").strip()
    if not token:
        raise SystemExit("Нет BOT_TOKEN: возьмите токен у @BotFather и положите в .env (см. .env.example)")
    admins = frozenset(int(part) for part in os.getenv("ADMIN_IDS", "").replace(",", " ").split())
    defaults = Config(token)
    return Config(
        token=token,
        admin_ids=admins,
        timezone=ZoneInfo(os.getenv("TIMEZONE") or "Europe/Moscow"),
        db_path=Path(os.getenv("DB_PATH") or defaults.db_path),
        schedule_path=Path(os.getenv("SCHEDULE_PATH") or defaults.schedule_path),
        http_host=os.getenv("HTTP_HOST") or defaults.http_host,
        http_port=int(os.getenv("HTTP_PORT") or defaults.http_port),
        message_interval=float(os.getenv("MESSAGE_INTERVAL") or defaults.message_interval),
    )
