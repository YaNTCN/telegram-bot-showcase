"""Ограничение частоты сообщений от одного пользователя.

Слишком частое сообщение не обрабатывается. Предупреждение отправляется
один раз на серию, чтобы бот сам не начал спамить в ответ.
"""

from __future__ import annotations

import time
from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import Message

from .. import texts
from ..metrics import THROTTLED


class Throttling(BaseMiddleware):
    def __init__(self, interval: float, clock: Callable[[], float] = time.monotonic):
        self.interval = interval
        self.clock = clock
        self._last: dict[int, float] = {}
        self._warned: set[int] = set()

    async def __call__(
        self,
        handler: Callable[[Message, dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: dict[str, Any],
    ) -> Any:
        user = event.from_user
        if user is None or self.interval <= 0:
            return await handler(event, data)

        now = self.clock()
        last = self._last.get(user.id)
        self._last[user.id] = now
        if last is not None and now - last < self.interval:
            THROTTLED.inc()
            if user.id not in self._warned:
                self._warned.add(user.id)
                await event.answer(texts.TOO_FAST)
            return None

        self._warned.discard(user.id)
        if len(self._last) > 10_000:
            self._forget_old(now)
        return await handler(event, data)

    def _forget_old(self, now: float) -> None:
        self._last = {user: moment for user, moment in self._last.items() if now - moment < self.interval}
        self._warned &= self._last.keys()
