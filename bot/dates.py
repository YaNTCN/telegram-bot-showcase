"""Дата из слов пользователя: «сегодня», «завтра», «пт», «в среду», «12.12»."""

from __future__ import annotations

import datetime as dt
import re

_RELATIVE = {"сегодня": 0, "завтра": 1, "послезавтра": 2, "вчера": -1}
_WEEKDAYS = {
    1: ("пн", "понедельник"),
    2: ("вт", "вторник"),
    3: ("ср", "среда", "среду"),
    4: ("чт", "четверг"),
    5: ("пт", "пятница", "пятницу"),
    6: ("сб", "суббота", "субботу"),
    7: ("вс", "воскресенье"),
}
_WORD_TO_DAY = {word: day for day, words in _WEEKDAYS.items() for word in words}
_DATE_RE = re.compile(r"^(\d{1,2})[./](\d{1,2})(?:[./](\d{2}|\d{4}))?$")
_FILLER = {"в", "во", "на", "а", "расписание", "пары", "что"}

MONTHS = ("января", "февраля", "марта", "апреля", "мая", "июня", "июля",
          "августа", "сентября", "октября", "ноября", "декабря")
WEEKDAY_NAMES = ("понедельник", "вторник", "среда", "четверг", "пятница", "суббота", "воскресенье")


def parse_day(text: str, today: dt.date) -> dt.date | None:
    """Дата по фразе или None, если фраза не про день.

    День недели означает ближайший такой день, начиная с сегодняшнего.
    Дата без года берётся в ближайшем будущем (12.01 в декабре это январь).
    """
    words = [word for word in re.findall(r"[\w./]+", text.lower()) if word not in _FILLER]
    if len(words) != 1:
        return None
    word = words[0].rstrip(".")
    if word in _RELATIVE:
        return today + dt.timedelta(days=_RELATIVE[word])
    if word in _WORD_TO_DAY:
        return today + dt.timedelta(days=(_WORD_TO_DAY[word] - today.isoweekday()) % 7)
    if match := _DATE_RE.match(word):
        return _date(match, today)
    return None


def _date(match: re.Match, today: dt.date) -> dt.date | None:
    day, month, year = match.groups()
    try:
        if year:
            return dt.date(int(year) + (2000 if len(year) == 2 else 0), int(month), int(day))
        date = dt.date(today.year, int(month), int(day))
    except ValueError:
        return None
    if date < today - dt.timedelta(days=60):
        date = date.replace(year=today.year + 1)
    return date


def human(date: dt.date) -> str:
    """«вторник, 2 декабря»."""
    return f"{WEEKDAY_NAMES[date.weekday()]}, {date.day} {MONTHS[date.month - 1]}"
