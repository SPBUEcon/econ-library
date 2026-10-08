"""Вставляет полные тексты семестровых заданий в страницу трека econ-3.

Источник — карточки заданий assignments/templates/*.md. В index.html текст карточки стоит между
маркерами <!-- task:<id> --> и <!-- /task:<id> -->; всё между ними перезаписывается, руками не правится.
Из карточки берутся только разделы для студента (TASKS ниже). Ссылки переводятся так же, как в
тезисах: md тезисов, сборок и кейсов → их html, прочие .md и .csv → GitHub.

Запуск: python tracks/econ-3/site/build.py
"""

import importlib.util
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
PAGE = HERE / "index.html"
TEMPLATES = REPO / "assignments" / "templates"

# id задания → (файл карточки, уровень md-заголовка, который становится <h4>,
#               разделы для студента: с заголовка start до заголовка stop, не включая)
# В tpl19 текст для студента — подразделы «## Текст задания…»: сам этот заголовок не выводится.
TASKS = {
    "tpl19": ("tpl19-essay-company-or-technology-starter.md", 3,
              [("## Текст задания (выдаётся студенту)", None)]),
    "tpl18": ("tpl18-essay-company-or-technology.md", 2,
              [("## Что предлагается сделать", "## Синопсис"),
               ("## Вопросы", "## Что дальше")]),
}

# md → html и перевод ссылок — из сборщика тезисов, чтобы ссылки вели туда же, что и в тезисах
_spec = importlib.util.spec_from_file_location("theses_build", REPO / "theses" / "site" / "build.py")
tb = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(tb)


def html_targets():
    """md-источник → его html: тезисы, сборки, кейсы."""
    out = {}
    for md in REPO.glob("theses/th*/README.md"):
        out[md.resolve()] = md.parent / "index.html"
    for md in REPO.glob("theses/assemblies/*.md"):
        out[md.resolve()] = md.with_suffix(".html")
    for md in REPO.glob("disciplines/*/cases/*/README.md"):
        if (md.parent / "index.html").exists():
            out[md.resolve()] = md.parent / "index.html"
    return out


def cut(md, start, stop):
    a = md.index(start + "\n")
    b = md.index(stop + "\n", a) if stop else len(md)
    return md[a:b]


ITEM = re.compile(r"^(\s*)(?:([-*])|(\d+)[.)])\s+(.*)$")
TABLE_SEP = re.compile(r"^\|[\s:|-]+\|\s*$")


def indent(ln):
    return len(ln) - len(ln.lstrip())


def parse_list(lines, i, ctx):
    """Список с вложенными списками и абзацами внутри пунктов; нумерация продолжается с номера в md."""
    m = ITEM.match(lines[i])
    base, ordered = indent(lines[i]), m.group(3) is not None
    start = int(m.group(3)) if ordered else 1
    items, blank = [], False
    while i < len(lines):
        ln = lines[i]
        if not ln.strip():
            blank, i = True, i + 1
            continue
        m = ITEM.match(ln)
        if m and indent(ln) == base and (m.group(3) is not None) == ordered:
            items.append([m.group(4)])
        elif m and indent(ln) > base and items:
            sub, i = parse_list(lines, i, ctx)
            items[-1].append(("html", sub))
            blank = False
            continue
        elif indent(ln) > base and items:
            if not blank and isinstance(items[-1][-1], str):
                items[-1][-1] += " " + ln.strip()
            else:
                items[-1].append(ln.strip())
        else:
            break
        blank, i = False, i + 1

    def li(parts):
        h = []
        for k, p in enumerate(parts):
            if isinstance(p, tuple):
                h.append(p[1])
            else:
                h.append(tb.inline(p, ctx) if k == 0 else f"<p>{tb.inline(p, ctx)}</p>")
        return "<li>" + "".join(h) + "</li>"

    tag = "ol" if ordered else "ul"
    attr = f' start="{start}"' if ordered and start != 1 else ""
    return f"<{tag}{attr}>" + "".join(li(p) for p in items) + f"</{tag}>", i


def convert(md, ctx, top):
    """md → html. Заголовок уровня top становится <h4>, следующий — <h5>."""
    lines, out, i = md.splitlines(), [], 0
    while i < len(lines):
        ln = lines[i]
        if not ln.strip() or ln.strip() == "---":
            i += 1
        elif ln.lstrip().startswith("<!--"):
            while "-->" not in lines[i]:
                i += 1
            i += 1
        elif re.match(r"^#{1,6} ", ln):
            lvl = len(ln) - len(ln.lstrip("#"))
            if lvl >= top:                 # заголовки выше top — обёртки разделов, не выводятся
                h = min(4 + lvl - top, 6)
                out.append(f"<h{h}>{tb.inline(ln[lvl:].strip(), ctx)}</h{h}>")
            i += 1
        elif ln.startswith("|") and i + 1 < len(lines) and TABLE_SEP.match(lines[i + 1]):
            rows = []
            while i < len(lines) and lines[i].startswith("|"):
                rows.append([c.strip() for c in lines[i].strip().strip("|").split("|")])
                i += 1
            head, body = rows[0], rows[2:]
            out.append('<div class="tbl"><table><thead><tr>'
                       + "".join(f"<th>{tb.inline(c, ctx)}</th>" for c in head) + "</tr></thead><tbody>"
                       + "".join("<tr>" + "".join(f"<td>{tb.inline(c, ctx)}</td>" for c in r) + "</tr>"
                                 for r in body)
                       + "</tbody></table></div>")
        elif ITEM.match(ln):
            h, i = parse_list(lines, i, ctx)
            out.append(h)
        else:
            para = []
            while (i < len(lines) and lines[i].strip() and not lines[i].startswith(("|", "#", "<!--"))
                   and not ITEM.match(lines[i])):
                para.append(lines[i].strip())
                i += 1
            out.append(f"<p>{tb.inline(' '.join(para), ctx)}</p>")
    return "\n".join(out)


def main():
    page = PAGE.read_text(encoding="utf-8")
    ctx = tb.Ctx(TEMPLATES, HERE, theses=html_targets())
    for tid, (fname, top, parts) in TASKS.items():
        md = (TEMPLATES / fname).read_text(encoding="utf-8")
        body = "\n".join(convert(cut(md, a, b), ctx, top) for a, b in parts)
        src = f"https://github.com/SPBUEcon/econ-library/blob/main/assignments/templates/{fname}"
        block = (f"<!-- task:{tid} -->\n"
                 f"<!-- Сгенерировано из assignments/templates/{fname} (tracks/econ-3/site/build.py). -->\n"
                 f'<div class="doc">\n{body}\n<p class="src">Источник — карточка '
                 f'<a href="{src}"><code>{tid}</code></a>.</p>\n</div>\n'
                 f"<!-- /task:{tid} -->")
        pat = re.compile(rf"<!-- task:{tid} -->.*?<!-- /task:{tid} -->", re.S)
        if not pat.search(page):
            raise SystemExit(f"в index.html нет маркеров <!-- task:{tid} --> … <!-- /task:{tid} -->")
        page = pat.sub(lambda _: block, page)
    PAGE.write_text(page, encoding="utf-8")
    print("written", PAGE, "tasks:", ", ".join(TASKS))


if __name__ == "__main__":
    main()
