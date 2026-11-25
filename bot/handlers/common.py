"""/help, /cancel и общие типы для обработчиков."""

from __future__ import annotations

import datetime as dt
from typing import Callable

from aiogram import Bot, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from .. import texts

Clock = Callable[[], dt.datetime]


async def help_command(message: Message, bot: Bot) -> None:
    me = await bot.me()
    await message.answer(texts.HELP.format(bot=me.username))


async def cancel(message: Message, state: FSMContext) -> None:
    if await state.get_state() is None:
        await message.answer(texts.NOTHING_TO_CANCEL)
        return
    await state.clear()
    await message.answer(texts.CANCELLED)


def router() -> Router:
    r = Router(name="common")
    r.message.register(help_command, Command("help"))
    r.message.register(cancel, Command("cancel"))
    return r
