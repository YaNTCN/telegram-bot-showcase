"""Сборка бота: зависимости, слои обработки, роутеры, обработчик ошибок."""

from __future__ import annotations

import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.base import BaseStorage
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand, ErrorEvent

from . import texts
from .config import Config
from .handlers import admin, common, inline, registration, schedule as schedule_handlers
from .handlers.common import Clock
from .metrics import ERRORS
from .middlewares.stats import HandlerStats, UpdateTimer
from .middlewares.throttling import Throttling
from .schedule import Schedule
from .storage import Users

log = logging.getLogger(__name__)

COMMANDS = [
    BotCommand(command="today", description="Пары на сегодня"),
    BotCommand(command="tomorrow", description="Пары на завтра"),
    BotCommand(command="week", description="Неделя"),
    BotCommand(command="start", description="Сменить группу"),
    BotCommand(command="help", description="Что умеет бот"),
]


def create_bot(token: str, **kwargs) -> Bot:
    default = DefaultBotProperties(parse_mode=ParseMode.HTML, link_preview_is_disabled=True)
    return Bot(token, default=default, **kwargs)


def build_dispatcher(
    config: Config, schedule: Schedule, users: Users, clock: Clock, storage: BaseStorage | None = None,
) -> Dispatcher:
    # Зависимости лежат в контексте диспетчера, aiogram передаёт их в обработчики по имени аргумента.
    dp = Dispatcher(storage=storage or MemoryStorage(), config=config, schedule=schedule, users=users, clock=clock)

    dp.update.outer_middleware(UpdateTimer())
    dp.message.outer_middleware(Throttling(config.message_interval))
    for kind in ("message", "callback_query", "inline_query"):
        dp.observers[kind].middleware(HandlerStats(kind))

    # Порядок важен: команды и шаги регистрации раньше, чем разбор свободного текста.
    dp.include_routers(
        common.router(),
        registration.router(),
        admin.router(),
        inline.router(),
        schedule_handlers.router(),
    )
    dp.errors.register(on_error)
    return dp


async def on_error(event: ErrorEvent) -> bool:
    ERRORS.labels(type(event.exception).__name__).inc()
    log.exception("Ошибка при обработке события %s", event.update.update_id, exc_info=event.exception)
    target = event.update.message or (event.update.callback_query and event.update.callback_query.message)
    if target is not None:
        try:
            await target.answer(texts.ERROR)
        except Exception:
            log.warning("Не удалось сообщить пользователю об ошибке", exc_info=True)
    return True


async def set_commands(bot: Bot) -> None:
    """Меню команд. Сбой здесь не должен мешать запуску."""
    try:
        await bot.set_my_commands(COMMANDS)
    except Exception:
        log.warning("Не удалось обновить меню команд", exc_info=True)
