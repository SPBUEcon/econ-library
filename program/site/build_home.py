# -*- coding: utf-8 -*-
"""Собирает главную (index.html в корне) из каталогов и индекс поиска по репозиторию.

Источники правды:
- группы, предметы, расписание — tracks/catalog/*.csv, паспорта треков tracks/<трек>/README.md;
- партнёры — таблицы «Реестр партнёров» и «Папки партнёров» в partners/README.md;
- тезисы и сборки — theses/catalog/*.csv; задания — assignments/catalog/templates.csv;
- воркстримы, стенды, документы — их README.md и прочие .md; страницы — .html репозитория.

В index.html перезаписываются только блоки между маркерами
<!-- gen:ИМЯ --> … <!-- /gen:ИМЯ --> (tracks, partners, content). Всё остальное —
оболочка страницы, её можно править руками. Если маркера нет, сборка остановится.

Индекс поиска пишется в program/site/search-index.js (подключается главной при первом поиске,
поэтому главная остаётся лёгкой и работает по file://).

Сборка детерминированная: без даты сборки, повторный запуск без изменений данных не меняет файлы.

    python program/site/build_home.py
"""
import csv
import html
import json
import re
from collections import OrderedDict
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
PAGE = REPO / "index.html"
INDEX = HERE / "search-index.js"
GH = "https://github.com/SPBUEcon/econ-library/"

# ---------------------------------------------------------------- утилиты

def rel(p):
    return Path(p).relative_to(REPO).as_posix()


def blob(path):
    return GH + "blob/main/" + path


def edit(path):
    return GH + "edit/main/" + path


def tree(path):
    return GH + "tree/main/" + path


def esc(s):
    return html.escape(s or "", quote=True)


def read_csv(path):
    with open(REPO / path, encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def split(v):
    return [x.strip() for x in re.split(r"[;,]", v or "") if x.strip()]


def tracked_files():
    """Файлы репозитория без служебных папок (git не нужен — сборка работает и из архива)."""
    skip = {".git", "node_modules", "__pycache__", "_export", "source-private", "private"}
    out = []
    for p in REPO.rglob("*"):
        if p.is_file() and not (set(p.relative_to(REPO).parts) & skip):
            out.append(p)
    return sorted(out, key=lambda p: rel(p))


MD_LINK = re.compile(r"!?\[([^\]]*)\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")


def md_plain(s):
    """Markdown → простой текст для поиска и подписей."""
    s = re.sub(r"```.*?```", " ", s, flags=re.S)
    s = re.sub(r"<!--.*?-->", " ", s, flags=re.S)
    s = re.sub(r"<[^>]+>", " ", s)
    s = MD_LINK.sub(r"\1", s)
    s = re.sub(r"^\s*\|?\s*:?-{3,}.*$", " ", s, flags=re.M)      # разделители таблиц
    s = re.sub(r"^\s{0,3}(#{1,6}|>|[-*+]|\d+\.)\s+", "", s, flags=re.M)
    s = s.replace("|", " ")
    s = re.sub(r"(\*\*|__|\*|`|~~)", "", s)
    s = re.sub(r"(?<!\w)_(?=\S)|(?<=\S)_(?!\w)", "", s)
    return re.sub(r"\s+", " ", s).strip()


def md_parts(path):
    """Заголовок H1, заголовки разделов и текст md-файла."""
    text = path.read_text(encoding="utf-8", errors="ignore")
    fm = re.match(r"^---\n(.*?)\n---\n", text, flags=re.S)       # front matter (шаблоны Issues и т.п.)
    h1, about = "", ""
    if fm:
        text = text[fm.end():]
        name = re.search(r'^name:\s*"?(.*?)"?\s*$', fm.group(1), flags=re.M)
        desc = re.search(r'^about:\s*"?(.*?)"?\s*$', fm.group(1), flags=re.M)
        h1 = name.group(1) if name else ""
        about = (desc.group(1) + " ") if desc else ""
    m = re.search(r"^#\s+(.+)$", text, flags=re.M)
    if m and not h1:
        h1 = md_plain(m.group(1))
        text = text[:m.start()] + text[m.end():]
    heads = [md_plain(h) for h in re.findall(r"^#{2,3}\s+(.+)$", text, flags=re.M)]
    return h1, heads, about + md_plain(text)


def html_parts(path):
    t = path.read_text(encoding="utf-8", errors="ignore")
    title = re.search(r"<title>(.*?)</title>", t, flags=re.S)
    body = re.sub(r"<(script|style|head)\b.*?</\1>", " ", t, flags=re.S | re.I)
    body = html.unescape(re.sub(r"<[^>]+>", " ", body))
    return (html.unescape(title.group(1)).strip() if title else path.name,
            re.sub(r"\s+", " ", body).strip())


def md_table(text, heading):
    """Строки первой таблицы после заголовка heading: список списков ячеек (сырой markdown)."""
    m = re.search(r"^#{2,3}\s+" + re.escape(heading) + r"\s*$", text, flags=re.M)
    if not m:
        raise SystemExit(f"partners/README.md: нет раздела «{heading}»")
    rows = []
    for line in text[m.end():].splitlines():
        line = line.strip()
        if not line:
            if rows:
                break
            continue
        if not line.startswith("|"):
            if rows:
                break
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if all(re.fullmatch(r":?-{3,}:?", c) for c in cells):
            continue
        rows.append(cells)
    return rows[1:]                                   # без шапки


def first_sentence(s, n=220):
    s = s.strip()
    if len(s) <= n:
        return s
    cut = s[:n]
    i = max(cut.rfind(". "), cut.rfind("; "))
    return (cut[:i + 1] if i > 80 else cut.rsplit(" ", 1)[0]) + " …"


def strip_parens(s):
    prev = None
    while prev != s:
        prev, s = s, re.sub(r"\s*\([^()]*\)", "", s)
    return re.sub(r"\s+,", ",", s).strip()


# ---------------------------------------------------------------- данные

RU_WD = ["пн", "вт", "ср", "чт", "пт", "сб", "вс"]


def dm(d):
    return f"{d.day:02d}.{d.month:02d}"


def lesson_kind(r):
    t = (r["lesson_type"] or "").lower()
    if t.startswith("самостоятельная"):
        return "Сам. работа" + (" онлайн" if (r["format"] or "").startswith("онлайн") else "")
    if t.startswith("практическ"):
        return "Практические"
    if t.startswith("лекц"):
        return "Лекции"
    return "Занятия"


def schedule_summary(rows):
    """«Практические: чт 17.09–22.10, сб 17.10 и 24.10» — по типам занятий и дням недели."""
    by_kind = OrderedDict()
    for r in sorted(rows, key=lambda r: (r["date"], r["time_start"])):
        by_kind.setdefault(lesson_kind(r), OrderedDict()).setdefault(
            date.fromisoformat(r["date"]).weekday(), [])
        lst = by_kind[lesson_kind(r)][date.fromisoformat(r["date"]).weekday()]
        d = date.fromisoformat(r["date"])
        if d not in lst:
            lst.append(d)
    lines = []
    for kind, wds in by_kind.items():
        parts = []
        for wd, ds in sorted(wds.items(), key=lambda kv: kv[1][0]):
            if len(ds) >= 3:
                parts.append(f"{RU_WD[wd]} {dm(ds[0])}–{dm(ds[-1])}")
            elif len(ds) == 2:
                parts.append(f"{RU_WD[wd]} {dm(ds[0])} и {dm(ds[1])}")
            else:
                parts.append(f"{RU_WD[wd]} {dm(ds[0])}")
        lines.append(f"{kind}: " + ", ".join(parts))
    return lines


def track_passport(track_id):
    """Поле «Поток» из паспорта трека tracks/<трек>/README.md."""
    p = REPO / "tracks" / track_id / "README.md"
    if not p.exists():
        return ""
    m = re.search(r"^\|\s*Поток\s*\|\s*(.+?)\s*\|\s*$", p.read_text(encoding="utf-8"), flags=re.M)
    return md_plain(m.group(1)) if m else ""


def build_tracks():
    subjects = read_csv("tracks/catalog/subjects.csv")
    groups = read_csv("tracks/catalog/groups.csv")
    sched_files = sorted((REPO / "tracks" / "catalog").glob("schedule-*.csv"))
    schedule = [r for f in sched_files for r in read_csv(rel(f))]
    subjects.sort(key=lambda s: (not s["track_id"],))         # сначала заведённые треки
    rows_html, status_data = [], {}
    for s in subjects:
        sid = s["subject_id"]
        gs = [g for g in groups if sid in split(g["subject_ids"])]
        lessons = [r for r in schedule if r["subject_id"] == sid]
        # курс · специальность
        cs = OrderedDict()
        for g in gs:
            cs[(g["course"], g["specialty"])] = 1
        if cs:
            course = "<br>".join(f'{esc(c)} · {esc(sp) if sp else "<i>уточнить</i>"}' for c, sp in cs)
        else:
            course = esc(track_passport(s["track_id"])) or "<i>уточнить</i>"
        # группы: наборы, которые ходят вместе
        sets, seen = [], set()
        for r in sorted(lessons, key=lambda r: (r["date"], r["time_start"])):
            ids = tuple(split(r["group_ids"]))
            if ids and ids not in sets:
                sets.append(ids)
        for ids in sets:
            seen.update(ids)
        sets += [(g["group_id"],) for g in gs if g["group_id"] not in seen]
        sets.sort(key=lambda ids: ids[0])
        groups_html = "".join('<span class="gset">' + "".join(f'<span class="g">{esc(i)}</span>' for i in ids)
                              + "</span>" for ids in sets) or '<span class="muted">номера уточнить</span>'
        # предмет
        title = esc(s["title"]) if s["title"] else "<i>уточнить</i>"
        page = REPO / "tracks" / s["track_id"] / "site" / "index.html" if s["track_id"] else None
        if page and page.exists():
            subj = (f'<a href="{rel(page)}" title="Расписание занятий и материалы"><b>{title}</b></a>'
                    if s["title"] else f'<a href="{rel(page)}" title="Расписание занятий и материалы">{title}</a>')
        else:
            subj = f"<b>{title}</b>"
        note = "" if s["track_id"] else '<span class="sub">трек не заведён</span>'
        subj += f'<span class="sub" data-status="{esc(sid)}"></span>{note}'
        when = "<br>".join(esc(x) for x in schedule_summary(lessons)) or '<span class="muted">нет в расписании</span>'
        when += f'<span class="sub" data-next="{esc(sid)}"></span>'
        rows_html.append(f"<tr><td>{course}</td><td>{groups_html}</td><td>{subj}</td><td>{when}</td></tr>")
        status_data[sid] = [[r["date"], r["time_start"], r["room"], r["format"]]
                            for r in sorted(lessons, key=lambda r: (r["date"], r["time_start"]))]
    edits = " · ".join(f'<a href="{edit("tracks/catalog/" + f)}">{f}</a>'
                       for f in ["groups.csv", "subjects.csv"] + [x.name for x in sched_files])
    block = ('<div class="tbl"><table>\n'
             '<thead><tr><th>Курс · специальность</th><th>Группы</th><th>Предмет</th><th>Занятия</th></tr></thead>\n'
             "<tbody>\n" + "\n".join(rows_html) + "\n</tbody></table></div>\n"
             f'<p class="src">Собрано из каталога <a href="{tree("tracks/catalog")}">tracks/catalog</a>. '
             f'<span class="edit-row">✎ Править: {edits}</span></p>\n'
             '<script>window.HOME_SCHEDULE = ' + json.dumps(status_data, ensure_ascii=False) + ';</script>')
    return block, subjects, groups


def build_partners():
    path = REPO / "partners" / "README.md"
    text = path.read_text(encoding="utf-8")
    folders = {}
    for cells in md_table(text, "Папки партнёров"):
        m = MD_LINK.search(cells[1]) if len(cells) > 1 else None
        if m:
            folders[md_plain(cells[0]).split(" (")[0]] = m.group(2).strip("/")
    out, records = [], []
    for cells in md_table(text, "Реестр партнёров"):
        name, contact, role, ws_cell = (cells + ["", "", "", ""])[:4]
        name = md_plain(name)
        page = None
        for _, href in MD_LINK.findall(" ".join(cells)):
            if href.endswith("site/index.html"):
                page = (path.parent / href).resolve()
        folder = folders.get(name)
        if not page and folder and (REPO / "partners" / folder / "site" / "index.html").exists():
            page = REPO / "partners" / folder / "site" / "index.html"
        if page:
            link = rel(page)
        elif folder:
            link = blob(f"partners/{folder}/README.md")
        else:
            link = ""
        ws = [t for t, href in MD_LINK.findall(ws_cell)
              if "workstreams/" in href and "flagships" not in href and not href.endswith(".html")]
        ws_txt = ", ".join(ws) if ws else strip_parens(md_plain(ws_cell))
        role_txt = md_plain(role)
        contact_txt = strip_parens(md_plain(contact)) or "—"
        name_html = f'<a href="{esc(link)}">{esc(name)}</a>' if link else esc(name)
        out.append(f"<tr><td>{name_html}</td><td>{esc(role_txt)}</td><td>{esc(ws_txt)}</td>"
                   f"<td>{esc(contact_txt)}</td></tr>")
        records.append({"name": name, "role": role_txt, "ws": ws_txt, "contact": contact_txt,
                        "url": link or blob("partners/README.md")})
    block = ('<div class="tbl"><table>\n'
             '<thead><tr><th>Партнёр</th><th>Роль</th><th>Воркстрим(ы)</th><th>Связной</th></tr></thead>\n'
             "<tbody>\n" + "\n".join(out) + "\n</tbody></table></div>\n"
             f'<p class="src">Собрано из <a href="{blob("partners/README.md")}">partners/README.md</a> '
             f'(«Реестр партнёров»). <span class="edit-row">✎ <a href="{edit("partners/README.md")}">Править реестр</a></span></p>')
    return block, records


def list_dirs(base):
    return sorted(p for p in (REPO / base).iterdir()
                  if p.is_dir() and not p.name.startswith(("_", ".")) and (p / "README.md").exists())


def build_content(theses, assemblies, units, templates, dossiers):
    workstreams = list_dirs("workstreams")
    stands = list_dirs("stands")
    nodes = sum(len(read_csv(rel(s / "nodes.csv"))) for s in stands if (s / "nodes.csv").exists())
    cand = sum(1 for u in units if u["status"] == "кандидат")
    tiles = [
        ("theses/site/index.html", "Тезисы и лекции",
         f"{len(theses)} тезисов · {len(assemblies)} сборки (лекции, серии, кейсы) · "
         f"{len(units)} единиц каталога дисциплины, из них {cand} — кандидаты в тезисы",
         [("theses/catalog/", "каталог тезисов")]),
        ("assignments/site/index.html", "Архив заданий",
         f"{len(templates)} заданий: конкретные, параметрические, эстафетные · досье: {len(dossiers)}; "
         "фильтры по навыку, типу, досье", [("assignments/catalog/templates.csv", "templates.csv")]),
        (blob("workstreams/README.md"), "Воркстримы",
         f"{len(workstreams)} папок воркстримов: формула, инверт, узлы, участники, хроника. Карта — на GitHub",
         [("workstreams/README.md", "карту")]),
        (blob("stands/README.md"), "Стенды",
         f"{len(stands)} стенда, {nodes} узлов прогресса — где выполняются задания и проверяется результат",
         [("stands/README.md", "README")]),
    ]
    out = []
    for href, title, desc, edits in tiles:
        ext = href.startswith("http")
        e = " · ".join(f'<a href="{edit(p) if not p.endswith("/") else tree(p.rstrip("/"))}">{esc(lbl)}</a>'
                       for p, lbl in edits)
        out.append(f'<div class="tile"><a class="tile-main" href="{esc(href)}"><span class="rt">{esc(title)}</span>'
                   f'<span class="rd">{esc(desc)}</span>'
                   f'<span class="go">{"Открыть на GitHub" if ext else "Открыть"} →</span></a>'
                   f'<div class="tile-edit">✎ Править: {e}</div></div>')
    return '<div class="res">\n' + "\n".join(out) + "\n</div>"


# ---------------------------------------------------------------- индекс поиска

TYPES = OrderedDict([
    ("thesis", "Тезис"), ("assembly", "Сборка"), ("task", "Задание"), ("unit", "Каталог дисциплины"),
    ("track", "Трек"), ("group", "Группа"), ("partner", "Партнёр"), ("workstream", "Воркстрим"),
    ("stand", "Стенд"), ("page", "Страница"), ("doc", "Документ"),
])
TEXT_CAP = 800        # символов текста документа в индексе (остальное — заголовки разделов)


def body(text, heads):
    """Текст для поиска и подписи: начало документа, затем заголовки разделов."""
    t = text[:TEXT_CAP]
    if len(text) > TEXT_CAP:
        t = t.rsplit(" ", 1)[0] + " …"
    h = " · ".join(heads)[:400]
    return t + (" ¶ " + h if h else "")


def rec(t, n, d="", u="", e="", k="", x="", s=""):
    return {"t": t, "n": n, "d": d, "u": u, "e": e, "k": k, "x": x, "s": s}


def build_index(theses, assemblies, units, templates, subjects, groups, partners):
    items, covered = [], set()
    # тезисы
    for t in theses:
        src = "theses/" + t["file"]
        covered.add(src)
        items.append(rec("thesis", t["title"], t["formula"], str(Path(src).parent / "index.html"),
                         edit(src), t["thesis_id"],
                         " ".join([t["kind"], t["blocks"], t["status"], t["refs"]]), src))
    # сборки (лекции, серии, кейсы)
    for a in assemblies:
        src = (Path("theses") / a["file"]).as_posix()
        src = str(Path(*[p for p in Path(src).parts]))
        src = rel((REPO / src).resolve())
        covered.add(src)
        page = (Path(src).parent / "index.html") if src.endswith("README.md") else Path(src).with_suffix(".html")
        items.append(rec("assembly", a["title"], f'{a["kind"]} · тезисы: {a["theses"]}', page.as_posix(),
                         edit(src), a["assembly_id"], a["kind"] + " " + a["status"], src))
    # задания
    for t in templates:
        f = t["file"] or ""
        src = "assignments/" + f if f.startswith("templates/") else "assignments/catalog/templates.csv"
        if f.startswith("templates/"):
            covered.add(src)
        items.append(rec("task", t["title"], t["brief"],
                         "assignments/site/index.html#q=" + t["template_id"].lower(), edit(src),
                         t["template_id"], " ".join([t["deliverable"], t["block"], t["dossier_id"]]), src))
    # единицы каталога дисциплины (кроме тезисов — они выше)
    by_thesis = {t["thesis_id"]: str(Path("theses/" + t["file"]).parent / "index.html") for t in theses}
    for u in units:
        if u["source"] == "theses":
            continue
        src = f'disciplines/{u["discipline"]}/catalog/{u["source"]}'
        th = split(u["theses"])
        url = by_thesis.get(th[0], "") if th else ""
        items.append(rec("unit", u["title"], u["summary"], url or "theses/site/index.html#units", edit(src),
                         u["unit_id"], f'{u["kind"]} {u["status"]} {u["block"]}', src))
    # треки и группы
    subj_title = {s["subject_id"]: s["title"] or "предмет уточнить" for s in subjects}
    for d in sorted((REPO / "tracks").iterdir()):
        readme = d / "README.md"
        if d.is_dir() and readme.exists() and d.name not in ("catalog", "data"):
            h1, heads, text = md_parts(readme)
            page = d / "site" / "index.html"
            covered.add(rel(readme))
            items.append(rec("track", h1.replace("`", ""), first_sentence(text),
                             rel(page) if page.exists() else blob(rel(readme)), edit(rel(readme)), d.name,
                             " ".join(heads), rel(readme)))
    for g in groups:
        track = g["track_id"]
        page = REPO / "tracks" / track / "site" / "index.html" if track else None
        subj = ", ".join(subj_title.get(s, s) for s in split(g["subject_ids"]))
        items.append(rec("group", g["group_id"],
                         f'{g["course"]} курс · {g["specialty"] or "специальность уточнить"} · {subj}',
                         rel(page) if page and page.exists() else blob("tracks/catalog/groups.csv"),
                         edit("tracks/catalog/groups.csv"), track, g["semester_id"], "tracks/catalog/groups.csv"))
    # партнёры
    for p in partners:
        items.append(rec("partner", p["name"], f'{p["role"]} · {p["ws"]} · связной: {p["contact"]}', p["url"],
                         edit("partners/README.md"), "", "", "partners/README.md"))
    # воркстримы и стенды
    for kind, base, prefix in (("workstream", "workstreams", r"^(Воркстрим|Поток):?\s*"),
                               ("stand", "stands", r"^Стенд:?\s*")):
        for d in list_dirs(base):
            readme = d / "README.md"
            covered.add(rel(readme))
            h1, heads, text = md_parts(readme)
            title = re.sub(r"\s*\((?:[a-z0-9-]+)\)\s*$", "", re.sub(prefix, "", h1)) or d.name
            page = d / "site" / "index.html"
            items.append(rec(kind, title, "", rel(page) if page.exists() else blob(rel(readme)),
                             edit(rel(readme)), d.name, body(text, heads), rel(readme)))
    # страницы
    files = tracked_files()
    for p in files:
        r = rel(p)
        if p.suffix != ".html" or r == "index.html":
            continue
        raw = p.read_text(encoding="utf-8", errors="ignore")
        if 'http-equiv="refresh"' in raw or p.name == "slides.html" or p.name.endswith("-slides.html"):
            continue
        if re.match(r"theses/th\d+", r) or r.startswith("theses/assemblies/") or "/cases/" in r:
            continue                                       # карточки — в тезисах и сборках
        title, text = html_parts(p)
        generated = "СГЕНЕРИРОВАНО" in raw or "build.py" in raw
        if r.startswith("tracks/"):
            e = edit(str(Path(r).parents[1] / "README.md"))   # блоки страницы трека собираются скриптом
        elif generated:
            e = ""
        else:
            e = edit(r)
        items.append(rec("page", title, "", r, e, "", body(text, []), r))
    # документы (.md, не вошедшие выше)
    for p in files:
        r = rel(p)
        if p.suffix != ".md" or r in covered or "/_template/" in r or r.startswith("_template"):
            continue
        h1, heads, text = md_parts(p)
        url = blob(r)
        if r.startswith(".github/ISSUE_TEMPLATE/"):
            url = GH + "issues/new?template=" + p.name
        items.append(rec("doc", h1 or p.stem, "", url, edit(r), "", body(text, heads), r))
    order = {k: i for i, k in enumerate(TYPES)}
    items.sort(key=lambda i: (order[i["t"]], i["k"], i["n"]))
    return items


# ---------------------------------------------------------------- запись

def put(page, name, block):
    a, b = f"<!-- gen:{name} -->", f"<!-- /gen:{name} -->"
    if a not in page or b not in page:
        raise SystemExit(f"index.html: нет маркеров {a} … {b}")
    head, rest = page.split(a, 1)
    _, tail = rest.split(b, 1)
    return head + a + "\n" + block + "\n" + b + tail


def main():
    theses = read_csv("theses/catalog/theses.csv")
    assemblies = read_csv("theses/catalog/assemblies.csv")
    units = read_csv("theses/catalog/units.csv")
    templates = read_csv("assignments/catalog/templates.csv")
    dossiers = sorted(p.parent.name for p in (REPO / "assignments" / "dossiers").glob("*/README.md"))

    tracks_html, subjects, groups = build_tracks()
    partners_html, partners = build_partners()
    content_html = build_content(theses, assemblies, units, templates, dossiers)
    items = build_index(theses, assemblies, units, templates, subjects, groups, partners)

    page = PAGE.read_text(encoding="utf-8")
    page = put(page, "tracks", tracks_html)
    page = put(page, "partners", partners_html)
    page = put(page, "content", content_html)
    PAGE.write_text(page, encoding="utf-8", newline="\n")

    payload = {"types": TYPES, "items": items}
    js = ("// СГЕНЕРИРОВАНО скриптом program/site/build_home.py — не править руками.\n"
          "window.HOME_INDEX = " + json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
          + ";\n")
    INDEX.write_text(js, encoding="utf-8", newline="\n")

    counts = OrderedDict((k, 0) for k in TYPES)
    for i in items:
        counts[i["t"]] += 1
    print(f"written {rel(PAGE)}; {rel(INDEX)}: {len(items)} записей, {INDEX.stat().st_size // 1024} КБ")
    print("  " + ", ".join(f"{TYPES[k]}: {v}" for k, v in counts.items()))


if __name__ == "__main__":
    main()
