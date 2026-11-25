"""Расписание: кнопки меню, команды, неделя с переключением дней и свободный текст."""

from __future__ import annotations

import contextlib
import datetime as dt

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command, or_f
from aiogram.types import CallbackQuery, Message

from .. import keyboards, texts
from ..dates import parse_day
from ..keyboards import DayCb
from ..schedule import Schedule
from ..storage import Users
from .common import Clock


async def today(message: Message, users: Users, schedule: Schedule, clock: Clock) -> None:
    await _own_day(message, 0, users, schedule, clock)


async def tomorrow(message: Message, users: Users, schedule: Schedule, clock: Clock) -> None:
    await _own_day(message, 1, users, schedule, clock)


async def week(message: Message, users: Users, schedule: Schedule, clock: Clock) -> None:
    group = await _own_group(message, users)
    if group is None:
        return
    now = clock()
    text, markup = _week_view(group, now.date(), schedule, now)
    await message.answer(text, reply_markup=markup)


async def week_day(callback: CallbackQuery, callback_data: DayCb, schedule: Schedule, clock: Clock) -> None:
    await callback.answer()
    if not isinstance(callback.message, Message):
        return
    text, markup = _week_view(callback_data.group, dt.date.fromisoformat(callback_data.date), schedule, clock())
    # Повторное нажатие на тот же день: Telegram отвечает «message is not modified».
    with contextlib.suppress(TelegramBadRequest):
        await callback.message.edit_text(text, reply_markup=markup)


async def profile(message: Message, users: Users) -> None:
    group = await _own_group(message, users)
    if group is not None:
        await message.answer(texts.PROFILE.format(group=group), reply_markup=keyboards.profile())


async def free_text(message: Message, users: Users, schedule: Schedule, clock: Clock) -> None:
    """«завтра», «пт», «12.12», «Б-ПМИ-26», «Б-ПМИ-26 завтра»."""
    now = clock()
    group, rest = schedule.group_in_text(message.text or "")
    if group is not None:
        date = parse_day(rest, now.date()) if rest else now.date()
    else:
        date = parse_day(message.text or "", now.date())
        if date is not None:
            group = await _own_group(message, users)
            if group is None:
                return
    if group is None or date is None:
        await message.answer(texts.UNKNOWN)
        return
    await message.answer(texts.day_schedule(group, date, schedule.day(group, date), now))


async def _own_day(message: Message, offset: int, users: Users, schedule: Schedule, clock: Clock) -> None:
    group = await _own_group(message, users)
    if group is None:
        return
    now = clock()
    date = now.date() + dt.timedelta(days=offset)
    await message.answer(texts.day_schedule(group, date, schedule.day(group, date), now))


async def _own_group(message: Message, users: Users) -> str | None:
    group = await users.group(message.from_user.id)
    if group is None:
        await message.answer(texts.NEED_GROUP)
    return group


def _week_view(group: str, date: dt.date, schedule: Schedule, now: dt.datetime):
    monday = date - dt.timedelta(days=date.weekday())
    text = texts.day_schedule(group, date, schedule.day(group, date), now)
    return text, keyboards.week(group, monday, date, schedule.week_has_lessons(group))


def router() -> Router:
    r = Router(name="schedule")
    r.message.register(today, or_f(Command("today"), F.text == texts.BTN_TODAY))
    r.message.register(tomorrow, or_f(Command("tomorrow"), F.text == texts.BTN_TOMORROW))
    r.message.register(week, or_f(Command("week"), F.text == texts.BTN_WEEK))
    r.message.register(profile, or_f(Command("profile"), F.text == texts.BTN_PROFILE))
    r.callback_query.register(week_day, DayCb.filter())
    r.message.register(free_text, F.text)
    return r
