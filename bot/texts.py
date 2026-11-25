"""Все тексты, которые видит пользователь. Разметка HTML."""

from __future__ import annotations

import datetime as dt
from html import escape

from .dates import human
from .schedule import EVEN, ODD, Lesson, week_parity

BTN_TODAY = "Сегодня"
BTN_TOMORROW = "Завтра"
BTN_WEEK = "Неделя"
BTN_PROFILE = "Профиль"
BTN_BACK = "« Назад"
BTN_CHANGE_GROUP = "Сменить группу"

PARITY = {ODD: "нечётная неделя", EVEN: "чётная неделя"}
WEEK_MARK = {ODD: " (по нечётным)", EVEN: " (по чётным)"}

WELCOME = (
    "Привет! Я показываю расписание пар.\n\n"
    "Выбери курс кнопкой ниже или просто напиши название группы, например <code>Б-ИВТ-26</code>."
)
CHOOSE_GROUP = "{course} курс. Выбери группу:"
GROUP_NOT_FOUND = "Не нашёл группу «{text}». Проверь название или выбери кнопкой."
REGISTERED = "Готово, твоя группа: <b>{group}</b>.\nКнопки внизу покажут пары на сегодня, завтра и неделю."
NEED_GROUP = "Сначала выбери группу: /start"
WEEK_TITLE = "<b>{group}</b>, неделя с {monday}\nВыбери день:"
PROFILE = "Твоя группа: <b>{group}</b>"
CANCELLED = "Отменил."
NOTHING_TO_CANCEL = "Отменять нечего."
UNKNOWN = (
    "Не понял. Можно написать:\n"
    "• <code>завтра</code>, <code>пт</code>, <code>12.12</code> для своей группы\n"
    "• <code>Б-ПМИ-26</code> или <code>Б-ПМИ-26 завтра</code> для другой группы\n\n"
    "Все команды: /help"
)
HELP = (
    "<b>Что я умею</b>\n\n"
    "/today, /tomorrow, /week: пары своей группы\n"
    "/start: сменить группу\n"
    "/cancel: отменить ввод\n\n"
    "Можно писать словами: <code>завтра</code>, <code>в среду</code>, <code>12.12</code>.\n"
    "Чужая группа: <code>Б-ПМИ-26</code> или <code>Б-ПМИ-26 пт</code>.\n\n"
    "В любом чате: <code>@{bot} Б-ИВТ-26 завтра</code> вставит расписание прямо в переписку."
)
TOO_FAST = "Не так быстро, пожалуйста."
ERROR = "Что-то пошло не так, уже разбираюсь. Попробуй ещё раз через минуту."
INLINE_HINT = "Напиши группу, например Б-ИВТ-26 завтра"
INLINE_NOT_FOUND = "Нет такой группы"
STATS = "<b>Статистика</b>\nПользователей: {total}\nАктивны за неделю: {active}\n\n{groups}"


def day_schedule(group: str, date: dt.date, lessons: list[Lesson], now: dt.datetime | None = None) -> str:
    """Расписание группы на день. Текущая пара помечена ▶️, следующая ⏭."""
    title = f"<b>{escape(group)}</b>, {human(date)}\n<i>{PARITY[week_parity(date)]}</i>"
    if not lessons:
        return f"{title}\n\nПар нет 🎉"

    current = next_up = None
    if now is not None and now.date() == date:
        clock = now.strftime("%H:%M")
        current = next((i for i, item in enumerate(lessons) if item.start <= clock < item.end), None)
        if current is None:
            next_up = next((i for i, item in enumerate(lessons) if item.start > clock), None)

    blocks = []
    for index, lesson in enumerate(lessons):
        mark = "▶️ " if index == current else "⏭ " if index == next_up else ""
        kind = f" ({escape(lesson.type)})" if lesson.type else ""
        details = ", ".join(part for part in (escape(lesson.teacher), _room(lesson.room)) if part)
        lines = [f"{mark}<b>{lesson.start}-{lesson.end}</b>  {escape(lesson.subject)}{kind}{WEEK_MARK.get(lesson.week, '')}"]
        if details:
            lines.append(f"      {details}")
        blocks.append("\n".join(lines))
    return title + "\n\n" + "\n\n".join(blocks)


def inline_title(group: str, date: dt.date, count: int) -> str:
    return f"{group}, {human(date)}: {count} пар" if count else f"{group}, {human(date)}: пар нет"


def stats(data: dict) -> str:
    groups = "\n".join(f"{escape(name)}: {count}" for name, count in data["groups"]) or "пока никого"
    return STATS.format(total=data["total"], active=data["active"], groups=groups)


def _room(room: str) -> str:
    if not room:
        return ""
    return escape(room) if not room[0].isdigit() else f"ауд. {escape(room)}"
