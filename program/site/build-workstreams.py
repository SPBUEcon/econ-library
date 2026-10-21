# -*- coding: utf-8 -*-
"""Собирает карту воркстримов (workstreams/README.md) из паспортов в папках.

Источники правды:
- workstreams/<папка>/workstream.yml — паспорт воркстрима (поля — workstreams/_template/workstream.yml);
- workstreams/flagships.yml — флагманы, у которых пока нет своих папок;
- история git и файлы в папках (meetings/, deliverables/, data/) — для таблицы живости.

Перезаписываются только блоки между маркерами <!-- gen:ИМЯ --> … <!-- /gen:ИМЯ -->:
в workstreams/README.md (карта для всех) — map, infra, actions; в workstreams/curators.md
(страница для кураторов) — activity; в guides/index.html (гайд для студента, сайт) —
guide-workstreams (карточки воркстримов). Остальной текст правится руками. Если маркера нет,
сборка остановится.

Тем же запуском обновляется список воркстримов в форме «Заявка на вход»
(.github/ISSUE_TEMPLATE/join-workstream.yml, блок # <gen:join-options> … # </gen:join-options>).

Живость считается по цифровому следу: коммиты в папке за 4 недели до последнего коммита
репозитория (а не до «сегодня»), поэтому повторный запуск без новых коммитов не меняет файл.

    python program/site/build-workstreams.py           # пересобрать карту
    python program/site/build-workstreams.py --check   # только проверить паспорта (для PR)
"""
import html
import posixpath
import re
import subprocess
import sys
from datetime import date, timedelta
from pathlib import Path
from urllib.parse import quote

import yaml

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
WS = REPO / "workstreams"
PAGE = WS / "README.md"
CURATORS = WS / "curators.md"
FLAGSHIPS = WS / "flagships.yml"
JOIN_FORM = REPO / ".github" / "ISSUE_TEMPLATE" / "join-workstream.yml"
GUIDE = REPO / "guides" / "index.html"
GH = "https://github.com/SPBUEcon/econ-library/"

SECTIONS = {"map", "infra", "hub"}
KINDS = {"оперативный", "сквозной", "событие", "флагман", "прото", "инфраструктурный", "хаб"}
ALIVE_DAYS = 28
MD_LINK = re.compile(r"(\]\()([^)\s]+)(\))")
MD_LINK_FULL = re.compile(r"\[([^\]]*)\]\([^)\s]+\)")
SKIP_FILES = {"README.md", ".gitkeep"}
# Цвет плашки уровня на сайте-гайде (классы — в guides/index.html).
KIND_CLASS = {"оперативный": "k-oper", "сквозной": "k-cross", "событие": "k-event", "флагман": "k-flag",
              "прото": "k-proto", "инфраструктурный": "k-infra", "хаб": "k-infra"}

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


def title_link(e):
    """Название — ссылка на папку воркстрима (у флагманов без папки — на flagships.md)."""
    return f"[{cell(e, 'title')}]({e['_dir']}/)" if e.get("_dir") else f"[{cell(e, 'title')}](flagships.md)"


def table(head, rows):
    out = ["| " + " | ".join(head) + " |", "|" + "---|" * len(head)]
    out += ["| " + " | ".join(r) + " |" for r in rows]
    return "\n".join(out)


def by_n(entries, section):
    return sorted((e for e in entries if e.get("section") == section), key=lambda e: e["n"])


def build_map(entries):
    """Карта для всех: короткие колонки. Поток, роль партнёра, источники команд и стенды — в
    карточке воркстрима (папка) и на витрине."""
    rows = [[str(e["n"]), title_link(e), cell(e, "partner"), cell(e, "supertask"), cell(e, "level"),
             cell(e, "status")] for e in by_n(entries, "map")]
    total = len(rows)
    flag = sum(1 for e in entries if e.get("section") == "map" and e.get("kind") == "флагман")
    return (table(["№", "Воркстрим", "Партнёр", "Суперзадача", "Уровень", "Статус"], rows)
            + f"\n\nВсего в карте — **{total}**, из них флагманов — **{flag}**.")


def build_infra(entries):
    rows = [[str(e["n"]), title_link(e), cell(e, "partner"), cell(e, "supertask"), cell(e, "status")]
            for e in by_n(entries, "infra")]
    return table(["№", "Воркстрим", "Владелец", "Суперзадача", "Статус"], rows)


def build_actions(entries):
    rows = [[str(e["n"]), title_link(e), cell(e, "next_action"), cell(e, "next_action_status")]
            for e in by_n(entries, "map") + by_n(entries, "infra") if e.get("next_action")]
    return table(["№", "Воркстрим", "Ближайшее действие", "Статус"], rows)


def join_options(entries):
    """Варианты выпадающего списка формы «Заявка на вход»: «id — №n Название».

    Порядок — как в карте (map и infra по номеру), затем потоки-хабы. Подпись начинается с id:
    по нему registry/register-participant.py находит воркстрим.
    """
    hubs = sorted((e for e in entries if e.get("section") == "hub"), key=lambda e: e["id"])
    out = []
    for e in sorted(by_n(entries, "map") + by_n(entries, "infra"), key=lambda e: e["n"]) + hubs:
        num = f"№{e['n']} " if isinstance(e.get("n"), int) else ""
        tail = " (флагман)" if e.get("kind") == "флагман" else ""
        label = f"{e['id']} — {num}{e['title']}{tail}".replace('"', "'")
        out.append(f'        - "{label}"')
    return "\n".join(out)


def put_join_options(form, block):
    a, b = "        # <gen:join-options>", "        # </gen:join-options>"
    if a not in form or b not in form:
        raise SystemExit(f"{JOIN_FORM.relative_to(REPO).as_posix()}: нет маркеров # <gen:join-options> … "
                         "# </gen:join-options>")
    head, rest = form.split(a, 1)
    _, tail = rest.split(b, 1)
    return head + a + "\n" + block + "\n" + b + tail


# ---------------------------------------------------------------- сайт-гайд для студента


def plain(v):
    """Значение паспорта → простой текст для сайта: без markdown-ссылок и разметки."""
    v = re.sub(r"\s+", " ", str(v or "")).strip()
    return re.sub(r"[*`]", "", MD_LINK_FULL.sub(r"\1", v))


def build_guide(entries):
    """Карточки воркстримов для guides/index.html: как в карте (map и infra по номеру).

    «Подать заявку» открывает форму с названием воркстрима в заголовке: GitHub подставляет из
    ссылки только заголовок, сам воркстрим студент выбирает в списке формы.
    """
    esc = lambda s: html.escape(s, quote=True)
    cards = []
    for e in sorted(by_n(entries, "map") + by_n(entries, "infra"), key=lambda e: e["n"]):
        title = plain(e.get("title"))
        card = (GH + f"tree/main/workstreams/{e['_dir']}") if e.get("_dir") else \
            GH + "blob/main/workstreams/flagships.md"
        join = GH + "issues/new?template=join-workstream.yml&title=" + quote(f"[Вход] {title} — ")
        out = ['<article class="ws">',
               f'  <div class="ws-top"><span class="ws-n">{e["n"]}</span>'
               f'<span class="badge {KIND_CLASS.get(e.get("kind"), "")}">{esc(plain(e.get("level") or e.get("kind")))}</span></div>',
               f"  <h3>{esc(title)}</h3>"]
        if e.get("partner"):
            out.append(f'  <p class="partner">{esc(plain(e["partner"]))}</p>')
        if e.get("supertask"):
            out.append(f'  <p class="task">{esc(plain(e["supertask"]))}</p>')
        if e.get("status"):
            out.append(f'  <p class="status">Статус: <b>{esc(plain(e["status"]))}</b></p>')
        out.append(f'  <div class="ws-links"><a class="join" href="{esc(join)}">Подать заявку</a>'
                   f'<a href="{esc(card)}">Карточка на GitHub</a></div>')
        out.append("</article>")
        cards.append("\n".join(out))
    return '<div class="ws-grid">\n' + "\n".join(cards) + "\n</div>"


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


def put(page, name, block, where="workstreams/README.md"):
    a, b = f"<!-- gen:{name} -->", f"<!-- /gen:{name} -->"
    if a not in page or b not in page:
        raise SystemExit(f"{where}: нет маркеров {a} … {b}")
    head, rest = page.split(a, 1)
    _, tail = rest.split(b, 1)
    return head + a + "\n" + block + "\n" + b + tail


def write_blocks(path, builders, entries):
    """Пересобрать блоки gen:* в одном файле; записать, только если что-то изменилось."""
    where = path.relative_to(REPO).as_posix()
    page = path.read_text(encoding="utf-8")
    new = page
    for name, fn in builders:
        new = put(new, name, fn(entries), where)
    if new != page:
        path.write_text(new, encoding="utf-8", newline="\n")
        print(f"written {where}: {len(entries)} паспортов")
    else:
        print(f"{where} без изменений: {len(entries)} паспортов")


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
    write_blocks(PAGE, (("map", build_map), ("infra", build_infra), ("actions", build_actions)), entries)
    write_blocks(CURATORS, (("activity", build_activity),), entries)
    if GUIDE.exists():
        write_blocks(GUIDE, (("guide-workstreams", build_guide),), entries)
    if JOIN_FORM.exists():
        form = JOIN_FORM.read_text(encoding="utf-8")
        new_form = put_join_options(form, join_options(entries))
        if new_form != form:
            JOIN_FORM.write_text(new_form, encoding="utf-8", newline="\n")
            print("written .github/ISSUE_TEMPLATE/join-workstream.yml: список воркстримов")


if __name__ == "__main__":
    main()
