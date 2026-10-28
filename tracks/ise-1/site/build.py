"""Собирает генерируемые блоки страницы трека ise-1. Логика общая с econ-3 — функции из
tracks/econ-3/site/build.py.

1. Слоты занятий — время · группы · курс и специальность (из groups.csv) · место — из расписания
   tracks/catalog/schedule-2026-fall.csv (строки предметов трека). В index.html слоты даты стоят между
   маркерами <!-- slots:ГГГГ-ММ-ДД --> и <!-- /slots:ГГГГ-ММ-ДД -->. Если у даты из расписания нет
   карточки — сборка останавливается.
2. Полные тексты заданий из карточек assignments/templates/*.md — между маркерами <!-- task:<id> --> и
   <!-- /task:<id> -->. Из карточки берутся только разделы для студента (TASKS ниже).

Всё между маркерами перезаписывается, руками не правится.

Запуск: python tracks/ise-1/site/build.py
"""

import importlib.util
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
PAGE = HERE / "index.html"
TRACK = "ise-1"

_spec = importlib.util.spec_from_file_location("econ3_build", REPO / "tracks" / "econ-3" / "site" / "build.py")
eb = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(eb)

# id задания → (файл карточки, уровень md-заголовка, который становится <h4>,
#               разделы для студента: с заголовка start до заголовка stop, не включая)
# В tpl22 пропущены «Синопсис», «Выдача по группам» и «Ход занятия» — это для преподавателя.
TASKS = {
    "tpl22": ("tpl22-first-forecast.md", 2,
              [("## Что предлагается сделать", "## Синопсис"),
               ("## Логика задачи", "## Выдача по группам"),
               ("## Ориентировочный результат", None)]),
}


def main():
    page = PAGE.read_text(encoding="utf-8")
    page, n_dates = eb.fill_slots(page, TRACK)
    print("slots:", n_dates, "dates")
    ctx = eb.tb.Ctx(eb.TEMPLATES, HERE, theses=eb.html_targets())
    for tid, (fname, top, parts) in TASKS.items():
        md = (eb.TEMPLATES / fname).read_text(encoding="utf-8")
        body = "\n".join(eb.convert(eb.cut(md, a, b), ctx, top) for a, b in parts)
        src = f"https://github.com/SPBUEcon/econ-library/blob/main/assignments/templates/{fname}"
        block = (f"<!-- task:{tid} -->\n"
                 f"<!-- Сгенерировано из assignments/templates/{fname} (tracks/ise-1/site/build.py). -->\n"
                 f'<div class="doc">\n{body}\n<p class="src">Источник — карточка '
                 f'<a href="{src}"><code>{tid}</code></a>.</p>\n</div>\n'
                 f"<!-- /task:{tid} -->")
        pat = re.compile(rf"<!-- task:{tid} -->.*?<!-- /task:{tid} -->", re.S)
        if not pat.search(page):
            raise SystemExit(f"в index.html нет маркеров <!-- task:{tid} --> … <!-- /task:{tid} -->")
        page = pat.sub(lambda _: block, page)
    PAGE.write_text(page, encoding="utf-8", newline="\n")
    print("written", PAGE, "tasks:", ", ".join(TASKS))


if __name__ == "__main__":
    main()
