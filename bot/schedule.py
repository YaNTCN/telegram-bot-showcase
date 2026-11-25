"""Расписание: загрузка, поиск групп, пары на конкретную дату."""

from __future__ import annotations

import datetime as dt
import json
import re
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

ODD, EVEN, BOTH = "odd", "even", "both"
_GROUP_YEAR_RE = re.compile(r"-(\d{2})(?:-\d+)?$")
_GROUP_RE = re.compile(r"[А-ЯЁA-Z]{1,2}-[А-ЯЁA-Z]{2,6}-\d{2}(?:-\d{1,2})?|[А-ЯЁA-Z]{2,6}-\d{2}(?:-\d{1,2})?")


@dataclass(frozen=True)
class Lesson:
    group: str
    weekday: int
    start: str
    end: str
    subject: str
    type: str = ""
    teacher: str = ""
    room: str = ""
    week: str = BOTH


def week_parity(date: dt.date) -> str:
    """Нечётная или чётная неделя по ISO-номеру недели."""
    return ODD if date.isocalendar().week % 2 else EVEN


def study_year(date: dt.date) -> int:
    """Год начала учебного года: с 1 сентября."""
    return date.year if date.month >= 9 else date.year - 1


class Schedule:
    def __init__(self, lessons: list[Lesson]):
        self._by_group: dict[str, list[Lesson]] = defaultdict(list)
        for lesson in sorted(lessons, key=lambda item: (item.weekday, item.start)):
            self._by_group[lesson.group].append(lesson)
        self._names = {_key(group): group for group in self._by_group}

    @classmethod
    def from_json(cls, path: str | Path) -> Schedule:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        return cls([Lesson(**item) for item in data["lessons"]])

    @property
    def groups(self) -> list[str]:
        return sorted(self._by_group)

    def courses(self, today: dt.date) -> dict[int, list[str]]:
        result: dict[int, list[str]] = defaultdict(list)
        for group in self.groups:
            if (course := self.course(group, today)) is not None:
                result[course].append(group)
        return dict(sorted(result.items()))

    @staticmethod
    def course(group: str, today: dt.date) -> int | None:
        match = _GROUP_YEAR_RE.search(group)
        if not match:
            return None
        return study_year(today) % 100 - int(match.group(1)) + 1

    def find_group(self, text: str) -> str | None:
        """Группа по названию: регистр, пробелы и тип тире не важны, «ивт-26» тоже найдётся."""
        key = _key(text)
        if key in self._names:
            return self._names[key]
        matches = [name for k, name in self._names.items() if k.endswith("-" + key)]
        return matches[0] if len(matches) == 1 else None

    def group_in_text(self, text: str) -> tuple[str | None, str]:
        """Ищет название группы внутри фразы: (группа, остаток текста)."""
        normalized = re.sub(r"[‐-―]", "-", text.upper())
        for match in _GROUP_RE.finditer(normalized):
            if group := self.find_group(match.group()):
                rest = text[: match.start()] + " " + text[match.end():]
                return group, " ".join(rest.split())
        return None, text

    def day(self, group: str, date: dt.date) -> list[Lesson]:
        parity = week_parity(date)
        return [lesson for lesson in self._by_group.get(group, [])
                if lesson.weekday == date.isoweekday() and lesson.week in (BOTH, parity)]

    def week_has_lessons(self, group: str) -> list[int]:
        return sorted({lesson.weekday for lesson in self._by_group.get(group, [])})


def _key(text: str) -> str:
    """«б ивт 26», «Б–ИВТ–26» и «Б-ИВТ-26» дают один ключ."""
    return re.sub(r"[\s‐-―-]+", "-", text.strip()).upper()
