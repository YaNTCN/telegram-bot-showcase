"""Генерирует выдуманное расписание в data/schedule.json.

Формат тот же, что выдаёт excel-schedule-normalizer (поля на английском).

    python scripts/make_demo_data.py
"""

from __future__ import annotations

import json
import random
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "data" / "schedule.json"
SLOTS = [("08:00", "09:35"), ("09:50", "11:25"), ("11:40", "13:15"), ("14:00", "15:35"), ("15:50", "17:25")]
TEACHERS = ["Белова М.К.", "Гусев В.В.", "Ким Д.С.", "Кузнецова Л.П.", "Ли А.В.", "Носов Т.Р.",
            "Орлов А.Н.", "Петров П.П.", "Сидорова Е.В.", "Яковлева О.И."]
SUBJECTS = {
    "ИВТ": ["Программирование", "Математический анализ", "Физика", "Базы данных", "Компьютерные сети",
            "Алгоритмы и структуры данных", "Английский язык", "Операционные системы"],
    "ПМИ": ["Алгебра", "Геометрия", "Дискретная математика", "Теория вероятностей",
            "Численные методы", "Программирование", "Английский язык"],
    "ЭК": ["Микроэкономика", "Эконометрика", "Финансовые рынки", "Деловые коммуникации", "Анализ данных"],
    "ПК": ["Информатика", "Математика", "Русский язык", "История", "Физическая культура"],
}
GROUPS = ["Б-ИВТ-26", "Б-ИВТ-25", "Б-ПМИ-26", "Б-ПМИ-25", "М-ЭК-26", "ПК-26"]
TYPES = ["лекция", "практика", "практика", "лабораторная"]
PRACTICE_ONLY = {"Английский язык", "Физическая культура", "Русский язык"}


def lesson(rng: random.Random, group: str, weekday: int, slot: int, week: str, subjects: list[str]) -> dict:
    start, end = SLOTS[slot]
    subject = rng.choice(subjects)
    kind = "практика" if subject in PRACTICE_ONLY else rng.choice(TYPES)
    return {
        "group": group, "weekday": weekday, "start": start, "end": end, "week": week,
        "subject": subject, "type": kind, "teacher": rng.choice(TEACHERS),
        "room": "онлайн" if rng.random() < 0.07 else str(rng.choice([101, 102, 205, 214, 305, 330, 412])),
    }


def main() -> None:
    rng = random.Random(2026)
    lessons = []
    for group in GROUPS:
        subjects = SUBJECTS[group.split("-")[-2]]
        for weekday in range(1, 7):
            if weekday == 6 and rng.random() < 0.5:
                continue
            first = rng.choice([0, 0, 1, 2])
            count = rng.randint(2, 4) if weekday < 6 else rng.randint(1, 2)
            for slot in range(first, min(first + count, len(SLOTS))):
                if rng.random() < 0.2:
                    lessons.append(lesson(rng, group, weekday, slot, "odd", subjects))
                    lessons.append(lesson(rng, group, weekday, slot, "even", subjects))
                else:
                    lessons.append(lesson(rng, group, weekday, slot, "both", subjects))
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps({"lessons": lessons}, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{len(lessons)} пар, {len(GROUPS)} групп: {OUT}")


if __name__ == "__main__":
    main()
