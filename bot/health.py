"""HTTP для мониторинга: /healthz для проверки живости и /metrics для Prometheus."""

from __future__ import annotations

import time

from aiohttp import web
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from .metrics import Activity

STARTED = time.time()


async def healthz(_: web.Request) -> web.Response:
    last = Activity.last_update
    return web.json_response({
        "status": "ok",
        "uptime_seconds": round(time.time() - STARTED),
        "seconds_since_last_update": round(time.time() - last) if last else None,
    })


async def metrics(_: web.Request) -> web.Response:
    return web.Response(body=generate_latest(), headers={"Content-Type": CONTENT_TYPE_LATEST})


async def start(host: str, port: int) -> web.AppRunner:
    app = web.Application()
    app.router.add_get("/healthz", healthz)
    app.router.add_get("/metrics", metrics)
    runner = web.AppRunner(app, access_log=None)
    await runner.setup()
    await web.TCPSite(runner, host, port).start()
    return runner
