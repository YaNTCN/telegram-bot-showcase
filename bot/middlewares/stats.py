"""Учёт событий: метрики по обработчикам и время последней активности пользователя."""

from __future__ import annotations

import time
from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.dispatcher.event.bases import UNHANDLED
from aiogram.types import TelegramObject, Update

from ..metrics import DURATION, LAST_UPDATE, UPDATES, Activity


class UpdateTimer(BaseMiddleware):
    """Внешний слой на всё событие: длительность и отметка «бот жив»."""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: Update,
        data: dict[str, Any],
    ) -> Any:
        Activity.last_update = time.time()
        LAST_UPDATE.set(Activity.last_update)
        started = time.perf_counter()
        try:
            result = await handler(event, data)
        finally:
            DURATION.labels(event.event_type).observe(time.perf_counter() - started)
        if result is UNHANDLED:
            UPDATES.labels(event.event_type, "-", "unhandled").inc()
        return result


class HandlerStats(BaseMiddleware):
    """Внутренний слой: знает, какой обработчик выбран, и обновляет last_seen."""

    def __init__(self, kind: str):
        self.kind = kind

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        name = data["handler"].callback.__name__
        try:
            result = await handler(event, data)
        except Exception:
            UPDATES.labels(self.kind, name, "error").inc()
            raise
        UPDATES.labels(self.kind, name, "ok").inc()
        user = data.get("event_from_user")
        if user is not None and "users" in data:
            await data["users"].touch(user.id)
        return result
