FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY bot ./bot
COPY data/schedule.json ./data/schedule.json

RUN useradd --create-home --uid 1000 bot && mkdir -p /app/data/db && chown bot /app/data/db
USER bot

ENV DB_PATH=/app/data/db/bot.sqlite3 HTTP_HOST=0.0.0.0
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=5s CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/healthz', timeout=3)"

CMD ["python", "-m", "bot"]
