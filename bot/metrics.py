"""Метрики Prometheus. Отдаются на /metrics (см. health.py)."""

from __future__ import annotations

from prometheus_client import Counter, Gauge, Histogram

UPDATES = Counter(
    "bot_updates_total", "Обработанные события по обработчикам", ["kind", "handler", "outcome"],
)
DURATION = Histogram(
    "bot_update_duration_seconds", "Время обработки события", ["kind"],
    buckets=(0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5),
)
THROTTLED = Counter("bot_throttled_total", "Сообщения, отброшенные ограничением частоты")
ERRORS = Counter("bot_errors_total", "Необработанные исключения", ["error"])


class Activity:
    """Время последнего события для /healthz (time.time())."""

    last_update: float | None = None


LAST_UPDATE = Gauge("bot_last_update_timestamp_seconds", "Когда пришло последнее событие (unix time)")
