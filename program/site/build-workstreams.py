# -*- coding: utf-8 -*-
"""Собирает карту воркстримов (workstreams/README.md) из паспортов в папках.

Источники правды:
- workstreams/<папка>/workstream.yml — паспорт воркстрима (поля — workstreams/_template/workstream.yml);
- workstreams/flagships.yml — флагманы, у которых пока нет своих папок;
- история git и файлы в папках (meetings/, deliverables/, data/) — для таблицы живости.

В workstreams/README.md перезаписываются только блоки между маркерами
<!-- gen:ИМЯ --> … <!-- /gen:ИМЯ --> (map, infra, actions, activity). Остальной текст карты
правится руками. Если маркера нет, сборка остановится.

Живость считается по цифровому следу: коммиты в папке за 4 недели до последнего коммита
репозитория (а не до «сегодня»), поэтому повторный запуск без новых коммитов не меняет файл.

    python program/site/build-workstreams.py           # пересобрать карту
    python program/site/build-workstreams.py --check   # только проверить паспорта (для PR)
"""
import posixpath
import re
import subprocess
import sys
from datetime import date, timedelta
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
WS = REPO / "workstreams"
PAGE = WS / "README.md"
FLAGSHIPS = WS / "flagships.yml"

SECTIONS = {"map", "infra", "hub"}
KINDS = {"оперативный", "сквозной", "событие", "флагман", "прото", "инфраструктурный", "хаб"}
ALIVE_DAYS = 28
MD_LINK = re.compile(r"(\]\()([^)\s]+)(\))")
SKIP_FILES = {"README.md", ".gitkeep"}

# ---------------------------------------------------------------- паспорта


def load():
    """Паспорта: список словарей; у записей из папок есть ключ _dir."""
    entries, errors = [], []
    for d in sorted(p for p in WS.iterdir() if p.is_dir() and not p.name.startswith(("_", "."))):
        f = d / "workstream.yml"
        if not f.exists():
            errors.append(f"workstreams/{d.name}/: нет workstream.yml (шаблон — workstreams/_template/)")
            continue
        try:
            e = yaml.safe_load(f.read_text(encoding="utf-8")) or {}
        except yaml.YAMLError as exc:
            errors.append(f"workstreams/{d.name}/workstream.yml: ошибка YAML — {exc}")
            continue
        if not isinstance(e, dict):
            errors.append(f"workstreams/{d.name}/workstream.yml: ожидался набор полей «ключ: значение»")
            continue
        e["_dir"] = d.name
        e["_src"] = f"workstreams/{d.name}/workstream.yml"
        if e.get("id") != d.name:
            errors.append(f"{e['_src']}: id «{e.get('id')}» не совпадает с именем папки «{d.name}»")
        if not (d / "README.md").exists():
            errors.append(f"workstreams/{d.name}/: нет карточки README.md")
        entries.append(e)
    if FLAGSHIPS.exists():
        try:
            items = yaml.safe_load(FLAGSHIPS.read_text(encoding="utf-8")) or []
        except yaml.YAMLError as exc:
            items = []
            errors.append(f"workstreams/flagships.yml: ошибка YAML — {exc}")
        for e in items:
            e["_dir"] = None
            e["_src"] = "workstreams/flagships.yml"
            entries.append(e)
    return entries, errors


def validate(entries):
    errors, seen_n, seen_id = [], {}, {}
    stands = {p.name for p in (REPO / "stands").iterdir() if p.is_dir()} if (REPO / "stands").exists() else set()
    for e in entries:
        src = e["_src"]
        for key in ("id", "title", "section"):
            if not e.get(key):
                errors.append(f"{src}: не заполнено поле {key}")
        if e.get("id") in seen_id:
            errors.append(f"{src}: id «{e['id']}» уже занят в {seen_id[e['id']]}")
        seen_id[e.get("id")] = src
        if e.get("section") and e["section"] not in SECTIONS:
            errors.append(f"{src}: section «{e['section']}» — допустимо: {', '.join(sorted(SECTIONS))}")
        if e.get("kind") and e["kind"] not in KINDS:
            errors.append(f"{src}: kind «{e['kind']}» — допустимо: {', '.join(sorted(KINDS))}")
        if e.get("section") in ("map", "infra"):
            n = e.get("n")
            if not isinstance(n, int):
                errors.append(f"{src}: для section {e['section']} нужен номер n (целое число)")
            elif n in seen_n:
                errors.append(f"{src}: номер {n} уже занят в {seen_n[n]}")
            else:
                seen_n[n] = src
        st = e.get("stands") or []
        if not isinstance(st, list):
            errors.append(f"{src}: stands — список в квадратных скобках, например [insurance]")
            st = []
        for s in st:
            if s not in stands:
                errors.append(f"{src}: стенда «{s}» нет в stands/")
    return errors


# ---------------------------------------------------------------- markdown


def cell(e, key, default="—"):
    """Значение поля для ячейки таблицы: ссылки — от workstreams/, без переносов и «|»."""
    v = e.get(key)
    if v is None or str(v).strip() == "":
        return default
    v = re.sub(r"\s+", " ", str(v)).strip().replace("|", "\\|")
    if e.get("_dir"):
        def fix(m):
            href = m.group(2)
            if re.match(r"^([a-z]+:|#|/)", href):
                return m.group(0)
            return m.group(1) + posixpath.normpath(f"{e['_dir']}/{href}") + m.group(3)
        v = MD_LINK.sub(fix, v)
    return v


def folder_link(e):
    return f"[`{e['_dir']}/`]({e['_dir']}/)" if e.get("_dir") else "[`flagships.md`](flagships.md)"


def stand_cell(e):
    links = [f"[`{s}`](../stands/{s}/README.md)" for s in e.get("stands") or []]
    if not links:
        return "—"
    note = f" *({e['stand_note']})*" if e.get("stand_note") else ""
    return ", ".join(links) + note


def table(head, rows):
    out = ["| " + " | ".join(head) + " |", "|" + "---|" * len(head)]
    out += ["| " + " | ".join(r) + " |" for r in rows]
    return "\n".join(out)


def by_n(entries, section):
    return sorted((e for e in entries if e.get("section") == section), key=lambda e: e["n"])


def build_map(entries):
    rows = [[str(e["n"]), cell(e, "title"), cell(e, "stream"), cell(e, "level"), cell(e, "partner"),
             cell(e, "partner_role"), cell(e, "supertask"), cell(e, "team_sources"), stand_cell(e),
             cell(e, "status"), folder_link(e)] for e in by_n(entries, "map")]
    total = len(rows)
    flag = sum(1 for e in entries if e.get("section") == "map" and e.get("kind") == "флагман")
    return (table(["#", "Воркстрим", "Поток (лендинг)", "Уровень", "Партнёр / куратор", "Роль партнёра",
                   "Суперзадача", "Источники команд", "Стенд", "Статус", "Папка"], rows)
            + f"\n\n**Итого в карте:** воркстримов — **{total}**; флагманов (B) — **{flag}**. "
              "*(Считается по паспортам `workstream.yml` автоматически.)*")


def build_infra(entries):
    rows = [[str(e["n"]), cell(e, "title"), cell(e, "level"), cell(e, "partner"), cell(e, "supertask"),
             cell(e, "status"), folder_link(e)] for e in by_n(entries, "infra")]
    return table(["#", "Воркстрим", "Уровень", "Владелец / носитель ставки", "Суперзадача", "Состояние",
                  "Папка"], rows)


def build_actions(entries):
    rows = [[str(e["n"]), cell(e, "next_action"), cell(e, "next_action_status")]
            for e in by_n(entries, "map") + by_n(entries, "infra") if e.get("next_action")]
    return table(["#", "Ближайшее действие", "Статус"], rows)


# ---------------------------------------------------------------- живость


def git_history():
    """{папка воркстрима: [даты коммитов]} и дата последнего коммита репозитория."""
    try:
        head = subprocess.run(["git", "log", "-1", "--format=%cs"], cwd=REPO, capture_output=True,
                              text=True, check=True).stdout.strip()
        log = subprocess.run(["git", "log", "--format=%x1e%cs", "--name-only", "--", "workstreams/"],
                             cwd=REPO, capture_output=True, text=True, check=True, encoding="utf-8").stdout
    except (OSError, subprocess.CalledProcessError):
        return None, None
    dates = {}
    for commit in log.split("")[1:]:                 # один коммит: дата, затем изменённые файлы
        day, *files = commit.split("\n")
        folders = {f.split("/")[1] for f in files if f.count("/") >= 2 and f.startswith("workstreams/")}
        for name in folders:
            dates.setdefault(name, []).append(day.strip())
    return dates, date.fromisoformat(head) if head else None


def count_files(d, sub):
    p = d / sub
    if not p.exists():
        return 0
    return sum(1 for f in p.rglob("*") if f.is_file() and f.name not in SKIP_FILES)


def build_activity(entries):
    dates, ref = git_history()
    if ref is None:
        return "*История git недоступна — таблица живости не собрана.*"
    since = ref - timedelta(days=ALIVE_DAYS)
    rows = []
    for e in sorted((e for e in entries if e.get("_dir")), key=lambda e: (e.get("n") or 999, e["_dir"])):
        d = WS / e["_dir"]
        ds = dates.get(e["_dir"], [])
        recent = sum(1 for x in ds if date.fromisoformat(x) >= since)
        last = max(ds) if ds else "—"
        alive = "живой" if recent else "спящий"
        rows.append([f"[{cell(e, 'title')}]({e['_dir']}/)", last, str(recent),
                     str(count_files(d, "meetings")), str(count_files(d, "deliverables")),
                     str(count_files(d, "data")), alive])
    return (table(["Воркстрим", "Последнее изменение", f"Коммитов за {ALIVE_DAYS // 7} нед.", "Встречи",
                   "Результаты", "Данные", "Живость"], rows)
            + f"\n\n*Окно — {ALIVE_DAYS} дней до последнего коммита репозитория ({ref.isoformat()}). "
              "Считаются файлы в `meetings/`, `deliverables/`, `data/` (без README).*")


# ---------------------------------------------------------------- запись


def put(page, name, block):
    a, b = f"<!-- gen:{name} -->", f"<!-- /gen:{name} -->"
    if a not in page or b not in page:
        raise SystemExit(f"workstreams/README.md: нет маркеров {a} … {b}")
    head, rest = page.split(a, 1)
    _, tail = rest.split(b, 1)
    return head + a + "\n" + block + "\n" + b + tail


def main():
    entries, errors = load()
    errors += validate(entries)
    if errors:
        print("Паспорта воркстримов с ошибками:", file=sys.stderr)
        for err in errors:
            print("  - " + err, file=sys.stderr)
        sys.exit(1)
    if "--check" in sys.argv:
        print(f"ok: {len(entries)} паспортов без ошибок")
        return
    page = PAGE.read_text(encoding="utf-8")
    new = page
    for name, fn in (("map", build_map), ("infra", build_infra), ("actions", build_actions),
                     ("activity", build_activity)):
        new = put(new, name, fn(entries))
    if new != page:
        PAGE.write_text(new, encoding="utf-8", newline="\n")
        print(f"written workstreams/README.md: {len(entries)} паспортов")
    else:
        print(f"workstreams/README.md без изменений: {len(entries)} паспортов")


if __name__ == "__main__":
    main()
