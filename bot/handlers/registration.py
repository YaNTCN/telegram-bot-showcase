"""Выбор группы: курс кнопкой, потом группа кнопкой, или название текстом."""

from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

from .. import keyboards, texts
from ..keyboards import BackCb, CourseCb, GroupCb, ProfileCb
from ..schedule import Schedule
from ..storage import Users
from .common import Clock


class Registration(StatesGroup):
    group = State()


async def start(message: Message, state: FSMContext, schedule: Schedule, clock: Clock) -> None:
    await state.set_state(Registration.group)
    courses = list(schedule.courses(clock().date()))
    await message.answer(texts.WELCOME, reply_markup=keyboards.courses(courses))


async def change_group(callback: CallbackQuery, state: FSMContext, schedule: Schedule, clock: Clock) -> None:
    await state.set_state(Registration.group)
    courses = list(schedule.courses(clock().date()))
    await callback.answer()
    if isinstance(callback.message, Message):
        await callback.message.answer(texts.WELCOME, reply_markup=keyboards.courses(courses))


async def course_chosen(callback: CallbackQuery, callback_data: CourseCb, schedule: Schedule, clock: Clock) -> None:
    names = schedule.courses(clock().date()).get(callback_data.course, [])
    await callback.answer()
    if isinstance(callback.message, Message):
        await callback.message.edit_text(
            texts.CHOOSE_GROUP.format(course=callback_data.course), reply_markup=keyboards.groups(names),
        )


async def back(callback: CallbackQuery, schedule: Schedule, clock: Clock) -> None:
    courses = list(schedule.courses(clock().date()))
    await callback.answer()
    if isinstance(callback.message, Message):
        await callback.message.edit_text(texts.WELCOME, reply_markup=keyboards.courses(courses))


async def group_chosen(
    callback: CallbackQuery, callback_data: GroupCb, state: FSMContext,
    users: Users, schedule: Schedule, clock: Clock,
) -> None:
    group = schedule.find_group(callback_data.name)
    if group is None or not isinstance(callback.message, Message):
        await callback.answer(texts.GROUP_NOT_FOUND.format(text=callback_data.name), show_alert=True)
        return
    await callback.answer()
    await callback.message.edit_reply_markup(reply_markup=None)
    await _finish(callback.message, callback.from_user.id, group, state, users, schedule, clock)


async def group_typed(message: Message, state: FSMContext, users: Users, schedule: Schedule, clock: Clock) -> None:
    group = schedule.find_group(message.text or "")
    if group is None:
        await message.answer(texts.GROUP_NOT_FOUND.format(text=message.text))
        return
    await _finish(message, message.from_user.id, group, state, users, schedule, clock)


async def _finish(message: Message, user_id: int, group: str, state: FSMContext,
                  users: Users, schedule: Schedule, clock: Clock) -> None:
    await users.set_group(user_id, group)
    await state.clear()
    await message.answer(texts.REGISTERED.format(group=group), reply_markup=keyboards.main_menu())
    now = clock()
    await message.answer(texts.day_schedule(group, now.date(), schedule.day(group, now.date()), now))


def router() -> Router:
    r = Router(name="registration")
    r.message.register(start, CommandStart())
    r.callback_query.register(change_group, ProfileCb.filter(F.action == "change"))
    r.callback_query.register(course_chosen, CourseCb.filter())
    r.callback_query.register(back, BackCb.filter())
    r.callback_query.register(group_chosen, GroupCb.filter())
    r.message.register(group_typed, Registration.group, F.text)
    return r
