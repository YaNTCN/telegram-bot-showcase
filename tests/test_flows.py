"""Сценарии целиком: от сообщения пользователя до вызовов Telegram API."""

from aiogram.methods import AnswerCallbackQuery, AnswerInlineQuery, EditMessageText, SendMessage
from aiogram.types import ReplyKeyboardMarkup
from prometheus_client import REGISTRY

from bot import texts
from bot.keyboards import CourseCb, DayCb, GroupCb

from .conftest import ADMIN_ID, callback_data, texts_of


def test_registration_with_buttons(harness):
    [welcome] = harness.send("/start")
    assert welcome.text == texts.WELCOME
    assert callback_data(welcome.reply_markup) == ["course:1", "course:2"]

    calls = harness.press(CourseCb(course=1).pack())
    edit = next(call for call in calls if isinstance(call, EditMessageText))
    assert edit.text == texts.CHOOSE_GROUP.format(course=1)
    assert GroupCb(name="Б-ИВТ-26").pack() in callback_data(edit.reply_markup)

    calls = harness.press(GroupCb(name="Б-ИВТ-26").pack())
    sent = [call for call in calls if isinstance(call, SendMessage)]
    assert sent[0].text == texts.REGISTERED.format(group="Б-ИВТ-26")
    assert isinstance(sent[0].reply_markup, ReplyKeyboardMarkup)
    assert sent[1].text.startswith("<b>Б-ИВТ-26</b>, среда, 2 декабря")
    assert harness.run(harness.users.group(1)) == "Б-ИВТ-26"


def test_registration_by_typing_and_back(harness):
    harness.send("/start")
    calls = harness.press("back")
    assert any(isinstance(call, EditMessageText) and call.text == texts.WELCOME for call in calls)

    assert texts_of(harness.send("Б-ИВТ-99")) == [texts.GROUP_NOT_FOUND.format(text="Б-ИВТ-99")]
    reply = texts_of(harness.send("пми 26"))
    assert reply[0] == texts.REGISTERED.format(group="Б-ПМИ-26")
    assert harness.run(harness.users.group(1)) == "Б-ПМИ-26"


def test_schedule_needs_group(harness):
    for text in (texts.BTN_TODAY, "/week", "пт"):
        assert texts_of(harness.send(text)) == [texts.NEED_GROUP]


def test_today_and_tomorrow(harness):
    harness.register("Б-ИВТ-26")
    [today] = texts_of(harness.send(texts.BTN_TODAY))
    [tomorrow] = texts_of(harness.send("/tomorrow"))
    assert "среда, 2 декабря" in today
    assert "четверг, 3 декабря" in tomorrow


def test_week_view_switches_days_in_place(harness):
    harness.register("Б-ИВТ-26")
    [message] = harness.send(texts.BTN_WEEK)
    assert "среда, 2 декабря" in message.text
    buttons = callback_data(message.reply_markup)
    monday = DayCb(group="Б-ИВТ-26", date="2026-11-30").pack()
    assert monday in buttons
    assert DayCb(group="Б-ИВТ-26", date="2026-12-07").pack() in buttons

    calls = harness.press(monday)
    assert isinstance(calls[0], AnswerCallbackQuery)
    edit = calls[1]
    assert isinstance(edit, EditMessageText) and "понедельник, 30 ноября" in edit.text


def test_free_text(harness):
    harness.register("Б-ИВТ-26")
    assert "пятница, 4 декабря" in texts_of(harness.send("в пятницу"))[0]
    assert "11 декабря" in texts_of(harness.send("11.12"))[0]
    other = texts_of(harness.send("пми-26 завтра"))[0]
    assert other.startswith("<b>Б-ПМИ-26</b>, четверг, 3 декабря")
    assert texts_of(harness.send("как дела?")) == [texts.UNKNOWN]


def test_profile_and_change_group(harness):
    harness.register("Б-ИВТ-26")
    [message] = harness.send(texts.BTN_PROFILE)
    assert message.text == texts.PROFILE.format(group="Б-ИВТ-26")
    calls = harness.press(callback_data(message.reply_markup)[0])
    assert texts.WELCOME in texts_of(calls)
    assert texts_of(harness.send("ПК-26"))[0] == texts.REGISTERED.format(group="ПК-26")


def test_inline_mode(harness):
    [answer] = harness.inline("")
    assert isinstance(answer, AnswerInlineQuery) and answer.results == []
    assert answer.button.text == texts.INLINE_HINT

    harness.register("Б-ИВТ-26")
    [answer] = harness.inline("")
    assert [result.title.split(":")[0] for result in answer.results] == [
        "Б-ИВТ-26, среда, 2 декабря", "Б-ИВТ-26, четверг, 3 декабря"]
    assert answer.is_personal

    [answer] = harness.inline("Б-ПМИ-25 пт")
    assert len(answer.results) == 1 and answer.results[0].title.startswith("Б-ПМИ-25, пятница")
    [answer] = harness.inline("Б-ХХХ-26")
    assert answer.results == [] and answer.button.text == texts.INLINE_NOT_FOUND


def test_cancel_and_help(harness):
    assert texts_of(harness.send("/cancel")) == [texts.NOTHING_TO_CANCEL]
    harness.send("/start")
    assert texts_of(harness.send("/cancel")) == [texts.CANCELLED]
    assert "@demo_bot Б-ИВТ-26 завтра" in texts_of(harness.send("/help"))[0]


def test_stats_only_for_admins(harness):
    harness.register("Б-ИВТ-26", user_id=1)
    harness.register("Б-ИВТ-26", user_id=2)
    harness.register("ПК-26", user_id=3)
    assert texts_of(harness.send("/stats", user_id=1)) == [texts.UNKNOWN]
    [reply] = texts_of(harness.send("/stats", user_id=ADMIN_ID))
    assert "Пользователей: 3" in reply and "Б-ИВТ-26: 2" in reply


def test_error_is_reported_to_user_and_metrics(harness, monkeypatch):
    harness.register("Б-ИВТ-26")

    def broken(*args):
        raise RuntimeError("база недоступна")

    monkeypatch.setattr(harness.schedule, "day", broken)
    before = REGISTRY.get_sample_value("bot_errors_total", {"error": "RuntimeError"}) or 0
    assert texts_of(harness.send(texts.BTN_TODAY)) == [texts.ERROR]
    assert REGISTRY.get_sample_value("bot_errors_total", {"error": "RuntimeError"}) == before + 1


def test_handler_metrics(harness):
    labels = {"kind": "message", "handler": "today", "outcome": "ok"}
    before = REGISTRY.get_sample_value("bot_updates_total", labels) or 0
    harness.register("Б-ИВТ-26")
    harness.send("/today")
    assert REGISTRY.get_sample_value("bot_updates_total", labels) == before + 1
