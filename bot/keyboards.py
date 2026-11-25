"""Клавиатуры и данные кнопок.

Данные inline-кнопок описаны через CallbackData: у каждого вида кнопок свой
префикс, а aiogram сам собирает и разбирает строку и следит за типами.
"""

from __future__ import annotations

import datetime as dt

from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder

from . import texts

SHORT_DAYS = ("Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс")


class CourseCb(CallbackData, prefix="course"):
    course: int


class GroupCb(CallbackData, prefix="group"):
    name: str


class BackCb(CallbackData, prefix="back"):
    pass


class DayCb(CallbackData, prefix="day"):
    group: str
    date: str


class ProfileCb(CallbackData, prefix="profile"):
    action: str


def main_menu() -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    builder.button(text=texts.BTN_TODAY)
    builder.button(text=texts.BTN_TOMORROW)
    builder.button(text=texts.BTN_WEEK)
    builder.button(text=texts.BTN_PROFILE)
    builder.adjust(2)
    return builder.as_markup(resize_keyboard=True, is_persistent=True)


def courses(courses: list[int]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for course in courses:
        builder.button(text=f"{course} курс", callback_data=CourseCb(course=course))
    builder.adjust(3)
    return builder.as_markup()


def groups(names: list[str]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for name in names:
        builder.button(text=name, callback_data=GroupCb(name=name))
    builder.adjust(2)
    builder.row(InlineKeyboardButton(text=texts.BTN_BACK, callback_data=BackCb().pack()))
    return builder.as_markup()


def week(group: str, monday: dt.date, selected: dt.date | None, days_with_lessons: list[int]) -> InlineKeyboardMarkup:
    """Дни недели и переход на соседние недели. Выбранный день отмечен точкой."""
    builder = InlineKeyboardBuilder()
    count = 0
    for offset in range(7):
        date = monday + dt.timedelta(days=offset)
        if date.isoweekday() not in days_with_lessons:
            continue
        label = SHORT_DAYS[offset] + (" •" if date == selected else "")
        builder.button(text=label, callback_data=DayCb(group=group, date=date.isoformat()))
        count += 1
    previous_week = monday - dt.timedelta(days=7)
    next_week = monday + dt.timedelta(days=7)
    builder.button(text="« Неделя", callback_data=DayCb(group=group, date=previous_week.isoformat()))
    builder.button(text="Неделя »", callback_data=DayCb(group=group, date=next_week.isoformat()))
    builder.adjust(*([count] if count else []), 2)
    return builder.as_markup()


def profile() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text=texts.BTN_CHANGE_GROUP, callback_data=ProfileCb(action="change"))
    return builder.as_markup()
