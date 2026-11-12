"""Собирает публичный data.js для страницы «Задание 1: кто сдал доклад».

Источник — приватный разбор registry/private/reviews/2026-fall-assignment-1/works.csv
(в git не попадает). Наружу уходят ТОЛЬКО четыре поля, которые показывает страница:
код работы, тема, группа, число авторов. Оценки уровня, ставки, замечания и сведения
об ИИ из works.csv сюда не переносятся — не добавляйте их.

Запуск из корня репозитория после каждого обновления разбора:
    python tracks/econ-3/site/assignment-1/build_data.py
    python tracks/econ-3/site/assignment-1/build_data.py --src путь/к/works.csv
"""
import argparse
import csv
import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
REVIEW = REPO / "registry" / "private" / "reviews" / "2026-fall-assignment-1"
OUT = HERE / "data.js"
PUBLIC_FIELDS = ("code", "title", "groups", "team_size")


def public_title(title):
    """Тема без пометок рецензента: «… (А); новая версия …» → «…»."""
    m = re.match(r"^(.*?)\s*\((?:А|В)\)", title)
    return (m.group(1) if m else title).strip()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", type=Path, default=REVIEW / "works.csv")
    args = ap.parse_args()
    if not args.src.exists():
        raise SystemExit(f"Нет {args.src} — разбор лежит только у преподавателя.")

    with args.src.open(encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    works = [{k: (public_title(r[k]) if k == "title" else r[k]) for k in PUBLIC_FIELDS} for r in rows]

    updated = ""
    readme = args.src.parent / "README.md"
    if readme.exists():
        m = re.search(r"Обновлено:\s*(\d{2}\.\d{2}\.\d{4})", readme.read_text(encoding="utf-8"))
        if m:
            updated = m.group(1)

    OUT.write_text(
        "// Сгенерировано build_data.py — не править вручную. Только публичные поля.\n"
        "window.DATA = " + json.dumps({"updated": updated, "works": works}, ensure_ascii=False, indent=1) + ";\n",
        encoding="utf-8",
    )
    print(f"{len(works)} works -> {OUT.relative_to(REPO)}")


if __name__ == "__main__":
    main()
