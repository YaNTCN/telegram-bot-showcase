"""Бот в тестах: настоящий Dispatcher, вместо Telegram сессия, которая записывает вызовы API."""

from __future__ import annotations

import asyncio
import datetime as dt
import itertools
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest
from aiogram.client.session.base import BaseSession
from aiogram.methods import GetMe, SendMessage, TelegramMethod
from aiogram.types import CallbackQuery, Chat, InlineQuery, Message, Update, User

from bot.app import build_dispatcher, create_bot
from bot.config import Config
from bot.schedule import Schedule
from bot.storage import Users

DATA = Path(__file__).resolve().parent.parent / "data" / "schedule.json"
TZ = ZoneInfo("Europe/Moscow")
# Среда 2 декабря 2026, нечётная ISO-неделя (49).
NOW = dt.datetime(2026, 12, 2, 10, 0, tzinfo=TZ)
BOT_USER = User(id=42, is_bot=True, first_name="Demo", username="demo_bot")
ADMIN_ID = 7


class FakeSession(BaseSession):
    def __init__(self) -> None:
        super().__init__()
        self.calls: list[TelegramMethod] = []
        self._ids = itertools.count(1000)

    async def make_request(self, bot, method, timeout=None):
        self.calls.append(method)
        if isinstance(method, GetMe):
            return BOT_USER
        if isinstance(method, SendMessage):
            return Message(message_id=next(self._ids), date=NOW, text=method.text,
                           chat=Chat(id=method.chat_id, type="private"), from_user=BOT_USER)
        return True

    async def stream_content(self, *args, **kwargs):
        raise NotImplementedError
        yield b""  # pragma: no cover

    async def close(self) -> None:
        pass


class Harness:
    """Отправляет боту события от имени пользователя и возвращает вызовы API, которые он сделал в ответ."""

    def __init__(self) -> None:
        self.loop = asyncio.new_event_loop()
        self.now = NOW
        self.schedule = Schedule.from_json(DATA)
        self.users = Users(":memory:")
        self.run(self.users.open())
        self.session = FakeSession()
        self.bot = create_bot("42:TEST", session=self.session)
        config = Config("42:TEST", admin_ids=frozenset({ADMIN_ID}), timezone=TZ, message_interval=0)
        self.dp = build_dispatcher(config, self.schedule, self.users, clock=lambda: self.now)
        self._ids = itertools.count(1)

    def run(self, coro):
        return self.loop.run_until_complete(coro)

    def close(self) -> None:
        self.run(self.users.close())
        self.loop.close()

    def _feed(self, **event) -> list[TelegramMethod]:
        before = len(self.session.calls)
        update = Update(update_id=next(self._ids), **event)
        self.run(self.dp.feed_update(self.bot, update))
        return self.session.calls[before:]

    @staticmethod
    def user(user_id: int) -> User:
        return User(id=user_id, is_bot=False, first_name="Студент")

    def send(self, text: str, user_id: int = 1) -> list[TelegramMethod]:
        message = Message(message_id=next(self._ids), date=self.now, text=text,
                          chat=Chat(id=user_id, type="private"), from_user=self.user(user_id))
        return self._feed(message=message)

    def press(self, data: str, user_id: int = 1, text: str = "…") -> list[TelegramMethod]:
        message = Message(message_id=500, date=self.now, text=text,
                          chat=Chat(id=user_id, type="private"), from_user=BOT_USER)
        callback = CallbackQuery(id=str(next(self._ids)), from_user=self.user(user_id),
                                 chat_instance="test", data=data, message=message)
        return self._feed(callback_query=callback)

    def inline(self, query: str, user_id: int = 1) -> list[TelegramMethod]:
        inline_query = InlineQuery(id=str(next(self._ids)), from_user=self.user(user_id), query=query, offset="")
        return self._feed(inline_query=inline_query)

    def register(self, group: str, user_id: int = 1) -> None:
        self.run(self.users.set_group(user_id, group))


@pytest.fixture
def harness():
    h = Harness()
    yield h
    h.close()


def texts_of(calls) -> list[str]:
    return [call.text for call in calls if hasattr(call, "text") and isinstance(call.text, str)]


def callback_data(markup) -> list[str]:
    return [button.callback_data for row in markup.inline_keyboard for button in row]
