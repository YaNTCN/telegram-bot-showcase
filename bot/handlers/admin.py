"""Команды для администраторов (ADMIN_IDS)."""

from __future__ import annotations

import datetime as dt

from aiogram import Router
from aiogram.filters import Command, Filter
from aiogram.types import Message

from .. import texts
from ..config import Config
from ..storage import Users


class IsAdmin(Filter):
    async def __call__(self, message: Message, config: Config) -> bool:
        return message.from_user is not None and message.from_user.id in config.admin_ids


async def stats(message: Message, users: Users) -> None:
    since = dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=7)
    await message.answer(texts.stats(await users.stats(since)))


def router() -> Router:
    r = Router(name="admin")
    r.message.filter(IsAdmin())
    r.message.register(stats, Command("stats"))
    return r
