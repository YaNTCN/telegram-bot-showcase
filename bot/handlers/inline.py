"""Inline-режим: «@бот Б-ИВТ-26 завтра» в любом чате вставляет расписание.

Пустой запрос показывает свою группу на сегодня и завтра.
"""

from __future__ import annotations

import datetime as dt
import hashlib

from aiogram import Router
from aiogram.types import (
    InlineQuery,
    InlineQueryResultArticle,
    InlineQueryResultsButton,
    InputTextMessageContent,
)

from .. import texts
from ..dates import parse_day
from ..schedule import Schedule
from ..storage import Users
from .common import Clock


async def inline_query(query: InlineQuery, users: Users, schedule: Schedule, clock: Clock) -> None:
    now = clock()
    text = query.query.strip()
    group, rest = schedule.group_in_text(text)
    if group is None and not text:
        group = await users.group(query.from_user.id)
    if group is None:
        await query.answer(
            [], cache_time=10, is_personal=True,
            button=InlineQueryResultsButton(text=texts.INLINE_HINT if not text else texts.INLINE_NOT_FOUND,
                                            start_parameter="inline"),
        )
        return

    if rest:
        dates = [date] if (date := parse_day(rest, now.date())) else []
    else:
        dates = [now.date(), now.date() + dt.timedelta(days=1)]
    results = [_article(group, date, schedule, now) for date in dates]
    await query.answer(results, cache_time=60, is_personal=not text)


def _article(group: str, date: dt.date, schedule: Schedule, now: dt.datetime) -> InlineQueryResultArticle:
    lessons = schedule.day(group, date)
    result_id = hashlib.sha1(f"{group}|{date}".encode()).hexdigest()[:16]
    return InlineQueryResultArticle(
        id=result_id,
        title=texts.inline_title(group, date, len(lessons)),
        description=", ".join(lesson.subject for lesson in lessons)[:100] or None,
        input_message_content=InputTextMessageContent(message_text=texts.day_schedule(group, date, lessons, now)),
    )


def router() -> Router:
    r = Router(name="inline")
    r.inline_query.register(inline_query)
    return r
