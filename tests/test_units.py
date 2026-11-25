import asyncio
import datetime as dt
from types import SimpleNamespace

import pytest

from bot import texts
from bot.dates import parse_day
from bot.middlewares.throttling import Throttling
from bot.schedule import EVEN, ODD, Lesson, Schedule, week_parity

WED = dt.date(2026, 12, 2)


@pytest.mark.parametrize("text, expected", [
    ("сегодня", WED), ("Завтра", dt.date(2026, 12, 3)), ("вчера", dt.date(2026, 12, 1)),
    ("ср", WED), ("пн", dt.date(2026, 12, 7)), ("в пятницу", dt.date(2026, 12, 4)),
    ("расписание на субботу", dt.date(2026, 12, 5)),
    ("12.12", dt.date(2026, 12, 12)), ("12/01", dt.date(2027, 1, 12)), ("1.11", dt.date(2026, 11, 1)),
    ("05.02.27", dt.date(2027, 2, 5)), ("31.02", None), ("привет", None), ("пн вт", None), ("", None),
])
def test_parse_day(text, expected):
    assert parse_day(text, WED) == expected


def test_week_parity_and_course():
    assert week_parity(WED) == ODD
    assert week_parity(dt.date(2026, 12, 9)) == EVEN
    assert Schedule.course("Б-ИВТ-26", WED) == 1
    assert Schedule.course("Б-ИВТ-25", dt.date(2027, 5, 1)) == 2
    assert Schedule.course("Без года", WED) is None


def test_find_group():
    schedule = Schedule([Lesson("Б-ИВТ-26", 1, "08:00", "09:35", "A"), Lesson("М-ИВТ-26", 1, "08:00", "09:35", "B"),
                         Lesson("ПК-26", 1, "08:00", "09:35", "C")])
    assert schedule.find_group("б ивт 26") == "Б-ИВТ-26"
    assert schedule.find_group("Б–ИВТ–26") == "Б-ИВТ-26"
    assert schedule.find_group("пк-26") == "ПК-26"
    assert schedule.find_group("ивт-26") is None  # бакалавриат или магистратура: неоднозначно
    assert schedule.group_in_text("покажи пк-26 на завтра") == ("ПК-26", "покажи на завтра")


def test_day_filters_week_parity():
    schedule = Schedule([
        Lesson("Г-АА-26", 3, "08:00", "09:35", "Каждая"),
        Lesson("Г-АА-26", 3, "09:50", "11:25", "Нечётная", week=ODD),
        Lesson("Г-АА-26", 3, "09:50", "11:25", "Чётная", week=EVEN),
    ])
    assert [lesson.subject for lesson in schedule.day("Г-АА-26", WED)] == ["Каждая", "Нечётная"]
    assert [lesson.subject for lesson in schedule.day("Г-АА-26", WED + dt.timedelta(days=7))] == ["Каждая", "Чётная"]


def test_current_and_next_pair_marks():
    lessons = [Lesson("Г", 3, "08:00", "09:35", "Первая", "лекция", "Ким Д.С.", "101"),
               Lesson("Г", 3, "09:50", "11:25", "Вторая", room="онлайн", week=ODD),
               Lesson("Г", 3, "11:40", "13:15", "Третья <b>")]
    at = lambda h, m: dt.datetime(2026, 12, 2, h, m)
    during = texts.day_schedule("Г", WED, lessons, at(10, 0))
    assert "▶️ <b>09:50-11:25</b>  Вторая (по нечётным)\n      онлайн" in during
    assert "Ким Д.С., ауд. 101" in during
    assert "Третья &lt;b&gt;" in during
    assert "⏭ <b>09:50-11:25</b>" in texts.day_schedule("Г", WED, lessons, at(9, 40))
    assert "▶️" not in texts.day_schedule("Г", WED, lessons, at(20, 0))
    assert texts.day_schedule("Г", WED, [], None).endswith("Пар нет 🎉")


def test_throttling_warns_once_per_burst():
    clock = SimpleNamespace(t=0.0)
    middleware = Throttling(1.0, clock=lambda: clock.t)
    answers, handled = [], []

    async def answer(text):
        answers.append(text)

    async def handler(event, data):
        handled.append(event)

    message = SimpleNamespace(from_user=SimpleNamespace(id=1), answer=answer)

    async def scenario():
        for moment in (0.0, 0.2, 0.4, 0.6, 2.0):
            clock.t = moment
            await middleware(handler, message, {})

    asyncio.run(scenario())
    assert len(handled) == 2
    assert answers == [texts.TOO_FAST]


def test_health_endpoints():
    from aiohttp import web
    from aiohttp.test_utils import TestClient, TestServer

    from bot import health

    async def scenario():
        app = web.Application()
        app.router.add_get("/healthz", health.healthz)
        app.router.add_get("/metrics", health.metrics)
        async with TestClient(TestServer(app)) as client:
            status = await (await client.get("/healthz")).json()
            metrics = await (await client.get("/metrics")).text()
        return status, metrics

    status, metrics = asyncio.run(scenario())
    assert status["status"] == "ok"
    assert "bot_updates_total" in metrics
