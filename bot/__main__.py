"""Запуск: python -m bot"""

from __future__ import annotations

import asyncio
import datetime as dt
import logging

from . import health
from .app import build_dispatcher, create_bot, set_commands
from .config import load_config
from .schedule import Schedule
from .storage import Users


async def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    config = load_config()
    schedule = Schedule.from_json(config.schedule_path)
    users = Users(config.db_path)
    await users.open()

    bot = create_bot(config.token)
    dp = build_dispatcher(config, schedule, users, clock=lambda: dt.datetime.now(config.timezone))
    runner = await health.start(config.http_host, config.http_port)
    logging.info("Групп в расписании: %d, мониторинг на %s:%d", len(schedule.groups), config.http_host, config.http_port)
    try:
        await set_commands(bot)
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        await runner.cleanup()
        await users.close()
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
