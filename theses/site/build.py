# -*- coding: utf-8 -*-
"""Собирает представления тезисов из md-источников.

Источник правды — карточки theses/th*/README.md и сборки theses/assemblies/*.md.
Всё остальное — представления в едином стиле (theme.css). У тезиса и у сборки их два:

- слайды (thNN-…/slides.html, assemblies/<id>-slides.html) — чистый контент: показ, PDF, PPTX;
- карточка (thNN-…/index.html, assemblies/<id>.html) — слайды с подсветкой проверок, комментарии,
  вопросы, задания, связи.

Служебная строка слайда — индекс тезиса (ссылка на карточку) и дата обновления.

    python theses/site/build.py            # HTML-страницы, витрина, CSV-индексы

    python theses/site/build.py            # HTML-страницы, витрина, CSV-индексы
    python theses/site/build.py --pdf      # + PDF (слайды 16:9, по странице на слайд)
    python theses/site/build.py --pptx     # + PPTX (кадры слайдов + заметки докладчика)
    python theses/site/build.py --export   # всё сразу

HTML-страницы самодостаточны (стиль и скрипт встроены), работают по file:// и на GitHub Pages.
PDF и PPTX делаются из тех же HTML через headless Chrome / Edge и кладутся в theses/_export/
(в git не попадает). Путь к браузеру можно задать переменной THESES_BROWSER.
"""
import csv
import glob
import html
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent                     # theses/
REPO = ROOT.parent
EXPORT = ROOT / "_export"
GH = "https://github.com/SPBUEcon/econ-library/"
PAGES = "https://spbuecon.github.io/econ-library/"   # ссылки в PDF и PPTX ведут сюда
FOOT = "Мастерская «Технологии в экономике» · ЭФ СПбГУ"
FONTS = ('<link rel="preconnect" href="https://fonts.googleapis.com">\n'
         '<link href="https://fonts.googleapis.com/css2?family=Unbounded:wght@500;700'
         '&family=IBM+Plex+Sans:ital,wght@0,400;0,500;0,600;1,500&display=swap" rel="stylesheet">')

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

WARN = []


def warn(msg):
    WARN.append(msg)


def split(v):
    return [x.strip() for x in (v or "").split(";") if x.strip()]


def esc(s):
    return html.escape(s, quote=True)


# ---------------------------------------------------------------- md → html

class Ctx:
    """Где лежит md-источник и где окажется html (нужно для перевода ссылок)."""

    def __init__(self, src_dir, out_dir, theses=None, clean=False):
        self.src_dir = Path(src_dir)
        self.out_dir = Path(out_dir)
        self.theses = theses or {}     # путь README.md → путь index.html и т.п.
        self.clean = clean             # чистые слайды: без подсветки проверок и пометок


def link_target(url, ctx):
    """Относительная ссылка из md → ссылка из html.

    md тезисов и сборок → их html; прочие .md/.csv и папки → GitHub; остальное — относительно.
    """
    if re.match(r"^[a-z]+:|^#|^mailto:", url):
        return url
    path, _, anchor = url.partition("#")
    if not path:
        return url
    target = (ctx.src_dir / path).resolve()
    if target in ctx.theses:
        out = ctx.theses[target]
    elif target.suffix in (".md", ".csv") or target.is_dir() or not target.suffix:
        rel = target.relative_to(REPO).as_posix() if target.is_relative_to(REPO) else path
        kind = "tree" if target.is_dir() else "blob"
        return f"{GH}{kind}/main/{rel}" + (f"#{anchor}" if anchor else "")
    else:
        out = target
    rel = os.path.relpath(out, ctx.out_dir).replace(os.sep, "/")
    return rel + (f"#{anchor}" if anchor else "")


CHK = re.compile(r"^\(?(со слайда\s*[—-]\s*)?проверить\)?$")


def inline(s, ctx):
    keep = []

    def stash(h):
        keep.append(h)
        return f"\x00{len(keep) - 1}\x00"

    s = re.sub(r"!\[([^\]]*)\]\(([^)\s]+)\)",
               lambda m: stash(f'<img src="{esc(link_target(m.group(2), ctx))}" alt="{esc(m.group(1))}">'), s)
    s = re.sub(r"\[((?:[^\[\]]|\[[^\]]*\])*)\]\(([^)\s]+)\)",
               lambda m: stash(f'<a href="{esc(link_target(m.group(2), ctx))}">{inline(m.group(1), ctx)}</a>'), s)
    s = re.sub(r"`([^`]+)`", lambda m: stash(f"<code>{esc(m.group(1))}</code>"), s)
    # <mark>…</mark> — утверждение, которое нужно проверить: в карточке подсвечено, в слайдах — обычный текст
    s = s.replace("<mark>", "\x01").replace("</mark>", "\x02")
    s = esc(s)
    s = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s)

    def em(m):
        t = m.group(1)
        if CHK.match(t):
            return "" if ctx.clean else '<span class="chk">проверить</span>'
        return f"<em>{t}</em>"

    s = re.sub(r"(?<![*\w])\*(?![\s*])(.+?)(?<![\s*])\*(?![*\w])", em, s)
    s = s.replace("\x01", "" if ctx.clean else "<mark>").replace("\x02", "" if ctx.clean else "</mark>")
    return re.sub(r"\x00(\d+)\x00", lambda m: keep[int(m.group(1))], s)


def slug(text):
    """Якорь заголовка, как у GitHub: нижний регистр, пробелы → дефис, без пунктуации."""
    t = re.sub(r"[`*]|\[|\]\([^)]*\)", "", text).strip().lower()
    return re.sub(r"[^\w\- ]", "", t).replace(" ", "-")


LIST = re.compile(r"^\s*([-*]|\d+[.)])\s+(.*)$")


def blocks(md):
    """md → список блоков (kind, data). Подмножество md, которого хватает карточкам."""
    lines = md.splitlines()
    out, i = [], 0
    while i < len(lines):
        ln = lines[i]
        if not ln.strip():
            i += 1
        elif ln.strip().startswith("<!--"):
            while "-->" not in lines[i]:
                i += 1
            i += 1
        elif ln.startswith("```"):
            j = i + 1
            while j < len(lines) and not lines[j].startswith("```"):
                j += 1
            lang = ln[3:].strip()
            out.append(("cycle" if lang == "cycle" else "pre", "\n".join(lines[i + 1:j])))
            i = j + 1
        elif re.match(r"^#{1,6} ", ln):
            lvl = len(ln) - len(ln.lstrip("#"))
            out.append(("h", (lvl, ln[lvl:].strip())))
            i += 1
        elif ln.startswith("|") and i + 1 < len(lines) and re.match(r"^\|[\s:|-]+\|\s*$", lines[i + 1]):
            rows = []
            while i < len(lines) and lines[i].startswith("|"):
                rows.append([c.strip() for c in lines[i].strip().strip("|").split("|")])
                i += 1
            out.append(("table", (rows[0], rows[2:])))
        elif ln.startswith(">"):
            inner = []
            while i < len(lines) and lines[i].startswith(">"):
                inner.append(re.sub(r"^> ?", "", lines[i]))
                i += 1
            out.append(("quote", "\n".join(inner)))
        elif LIST.match(ln):
            ordered = LIST.match(ln).group(1)[0].isdigit()
            items = []
            while i < len(lines) and lines[i].strip():
                m = LIST.match(lines[i])
                if m:
                    items.append(m.group(2))
                elif lines[i].startswith((" ", "\t")) and items:
                    items[-1] += " " + lines[i].strip()
                else:
                    break
                i += 1
            out.append(("ol" if ordered else "ul", items))
        else:
            para = []
            while (i < len(lines) and lines[i].strip() and not lines[i].startswith(("|", ">", "```", "#", "<!--"))
                   and not LIST.match(lines[i])):
                para.append(lines[i].strip())
                i += 1
            out.append(("p", " ".join(para)))
    return out


def render(bl, ctx, layout=""):
    h = []
    for kind, d in bl:
        if kind == "p":
            h.append(f"<p>{inline(d, ctx)}</p>")
        elif kind == "h":
            lvl = min(d[0] + 1, 6)
            h.append(f'<h{lvl} id="{slug(d[1])}">{inline(d[1], ctx)}</h{lvl}>')
        elif kind == "pre":
            h.append(f"<pre>{esc(d)}</pre>")
        elif kind == "cycle":
            h.append(cycle_html(d, ctx))
        elif kind == "quote":
            h.append(f"<blockquote>{render(blocks(d), ctx)}</blockquote>")
        elif kind in ("ul", "ol"):
            h.append(f"<{kind}>" + "".join(f"<li>{inline(x, ctx)}</li>" for x in d) + f"</{kind}>")
        elif kind == "table" and layout == "columns":
            head, rows = d
            cols = []
            for k, name in enumerate(head):
                title, _, sub = name.partition(" · ")
                items = [r[k] for r in rows if k < len(r) and r[k]]
                cols.append(f'<div class="col"><div class="col-h"><b>{inline(title, ctx)}</b>'
                            + (f"<span>{inline(sub, ctx)}</span>" if sub else "") + "</div><ul>"
                            + "".join(f"<li>{inline(x, ctx)}</li>" for x in items) + "</ul></div>")
            h.append('<div class="cols">' + "".join(cols) + "</div>")
        elif kind == "table":
            head, rows = d
            h.append("<table><thead><tr>" + "".join(f"<th>{inline(c, ctx)}</th>" for c in head) + "</tr></thead><tbody>"
                     + "".join("<tr>" + "".join(f"<td>{inline(c, ctx)}</td>" for c in r) + "</tr>" for r in rows)
                     + "</tbody></table>")
    return "\n".join(h)


CYCLE_STEP = re.compile(r"\s*-([^->]*)->\s*")


def cycle_html(src, ctx):
    """```cycle: «A -глагол-> B -глагол-> C -глагол-> A» → схема: узлы, стрелки с подписями, обратная дуга.

    На GitHub блок читается как текст, в HTML — как схема на тонких линиях.
    """
    parts = CYCLE_STEP.split(" ".join(src.split()))
    nodes, verbs = parts[0::2], parts[1::2]
    loop = len(nodes) > 2 and nodes[-1] == nodes[0]
    back = verbs.pop() if loop else ""
    if loop:
        nodes.pop()
    row = []
    for k, n in enumerate(nodes):
        row.append(f'<span class="cy-node">{inline(n, ctx)}</span>')
        if k < len(verbs):
            row.append(f'<span class="cy-arr"><i>{inline(verbs[k], ctx)}</i></span>')
    return ('<div class="cycle"><div class="cy-row">' + "".join(row) + "</div>"
            + (f'<div class="cy-back"><i>{inline(back, ctx)}</i></div>' if loop else "") + "</div>")


def md_html(md, ctx, layout="", skip_quotes=False):
    bl = blocks(md)
    if skip_quotes:
        bl = [b for b in bl if b[0] != "quote"]
    return render(bl, ctx, layout)


def plain(md):
    """md → простой текст (заметки PPTX)."""
    t = re.sub(r"<!--.*?-->|</?mark>", "", md, flags=re.S)
    t = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", t)
    t = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", t)
    t = re.sub(r"[*`]|^> ?|^#+ ", "", t, flags=re.M)
    t = re.sub(r"^\|[\s:|-]+\|$", "", t, flags=re.M)
    return re.sub(r"\n{3,}", "\n\n", t).strip()


# ---------------------------------------------------------------- источники

def front(text):
    meta = {}
    m = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    if m:
        for ln in m.group(1).splitlines():
            k, _, v = ln.partition(":")
            if k.strip():
                meta[k.strip()] = v.strip()
        text = text[m.end():]
    return meta, text


def sections(body):
    """→ (h1, lead_md, [(заголовок, md)])"""
    h1 = re.search(r"^# (.+)$", body, re.M)
    rest = body[h1.end():] if h1 else body
    parts = re.split(r"^## (.+)$", rest, flags=re.M)
    return (h1.group(1).strip() if h1 else ""), parts[0], list(zip(parts[1::2], parts[2::2]))


SLIDE = re.compile(r"^Слайд\s*\d+\s*[.:·]?\s*(.*)$")


def load_thesis(readme):
    text = Path(readme).read_text(encoding="utf-8").replace("\r\n", "\n")
    meta, body = front(text)
    h1, lead, secs = sections(body)
    t = {"meta": meta, "h1": h1, "lead": lead, "slides": [], "sections": [],
         "dir": Path(readme).parent, "src": Path(readme).resolve()}
    for title, md in secs:
        m = SLIDE.match(title)
        if not m:
            t["sections"].append((title, md))
            continue
        def directive(name):
            d = re.search(r"<!--\s*" + name + r":\s*(\S+)\s*-->", md)
            return d.group(1) if d else ""

        lay = directive("layout")
        content, notes = (re.split(r"<!--\s*notes\s*-->", md, maxsplit=1) + [""])[:2]
        t["slides"].append({"title": m.group(1).strip(), "layout": lay,
                            "logo": directive("logo"), "bg": directive("bg"),
                            "md": content, "notes": notes.strip()})
    tid = meta.get("id", "")
    if not tid:
        warn(f"{readme}: нет id во frontmatter")
    if not meta.get("formula"):
        warn(f"{tid}: нет формулы — тезис должен укладываться в одну фразу")
    if not 1 <= len(t["slides"]) <= 3:
        warn(f"{tid}: слайдов {len(t['slides'])}, а тезис — это 1–3 слайда")
    t["id"], t["title"] = tid, meta.get("title", h1)
    t["out"] = t["dir"] / "index.html"
    t["deck"] = t["dir"] / "slides.html"
    return t


ITEM = re.compile(r"`(th\d+)`")


def load_assembly(path):
    """Сборка: разделы со списками `thNN` — группы тезисов, остальные разделы — текст.

    Сборки лежат в theses/assemblies/<id>.md (→ <id>.html, <id>-slides.html) или, для кейса, в
    README.md папки кейса с `kind: кейс` (→ index.html, slides.html рядом).
    """
    text = Path(path).read_text(encoding="utf-8").replace("\r\n", "\n")
    meta, body = front(text)
    h1, lead, secs = sections(body)
    parts, groups = [], []
    for title, md in secs:
        items = []
        for kind, d in blocks(md):
            if kind in ("ul", "ol"):
                for x in d:
                    m = ITEM.search(x)
                    items.append({"id": m.group(1) if m else "", "text": ITEM.sub("", x, count=1).strip() if m else x})
        if any(i["id"] for i in items):
            groups.append((title, items))
            parts.append(("group", title, items))
        else:
            parts.append(("text", title, md))
    p = Path(path)
    readme = p.name == "README.md"
    return {"meta": meta, "h1": h1, "lead": lead, "groups": groups, "parts": parts,
            "id": meta.get("id", p.parent.name if readme else p.stem),
            "title": meta.get("title", h1), "src": p.resolve(), "dir": p.parent,
            "out": p.parent / "index.html" if readme else p.with_suffix(".html"),
            "deck": p.parent / "slides.html" if readme else p.with_name(p.stem + "-slides.html")}


def case_sources():
    """README кейсов дисциплин, размеченные как сборка (`kind: кейс` во frontmatter)."""
    out = []
    for p in sorted(glob.glob(str(REPO / "disciplines" / "*" / "cases" / "*" / "README.md"))):
        meta, _ = front(Path(p).read_text(encoding="utf-8").replace("\r\n", "\n"))
        if meta.get("kind") == "кейс":
            out.append(p)
    return out


# ---------------------------------------------------------------- страницы

DECK_SCRIPT = """<script>
(function(){
  var slides=[].slice.call(document.querySelectorAll('main .slide')), stage=document.querySelector('.stage'), i=0;
  var links=[].slice.call(document.querySelectorAll('a[data-pages]')), q=new URLSearchParams(location.search);
  function web(on){links.forEach(function(a){if(!a.dataset.local)a.dataset.local=a.getAttribute('href');
    a.setAttribute('href',on?a.dataset.pages:a.dataset.local);});}
  function show(k){i=Math.max(0,Math.min(slides.length-1,k));stage.innerHTML='';stage.appendChild(slides[i].cloneNode(true));}
  if(q.has('export'))web(true);
  if(q.has('frame')){document.body.classList.add('frame');show((+q.get('frame')||1)-1);return;}
  window.addEventListener('beforeprint',function(){web(true);});
  window.addEventListener('afterprint',function(){if(!q.has('export'))web(false);});
  if(q.has('print'))(document.fonts?document.fonts.ready:Promise.resolve()).then(function(){setTimeout(function(){window.print();},300);});
  function start(k){document.body.classList.add('present');show(k||0);
    if(document.documentElement.requestFullscreen)document.documentElement.requestFullscreen().catch(function(){});}
  function stop(){document.body.classList.remove('present');if(document.fullscreenElement)document.exitFullscreen();}
  if(q.has('present'))start((+q.get('present')||1)-1);
  function current(){var k=0;slides.forEach(function(s,j){if(s.getBoundingClientRect().top<innerHeight/2)k=j;});return k;}
  [].forEach.call(document.querySelectorAll('[data-present]'),function(b){b.onclick=function(){start(current());};});
  [].forEach.call(document.querySelectorAll('[data-print]'),function(b){b.onclick=function(){window.print();};});
  slides.forEach(function(s,k){s.addEventListener('dblclick',function(){start(k);});});
  stage.addEventListener('click',function(e){if(e.target.closest('a'))return;show(e.clientX>innerWidth/3?i+1:i-1);});
  document.addEventListener('keydown',function(e){
    if(!document.body.classList.contains('present')){
      if(['f','F','а','А'].indexOf(e.key)>=0&&!e.ctrlKey&&!e.metaKey)start(current());return;}
    if(['ArrowRight','ArrowDown','PageDown',' ','Enter'].indexOf(e.key)>=0){show(i+1);e.preventDefault();}
    else if(['ArrowLeft','ArrowUp','PageUp','Backspace'].indexOf(e.key)>=0){show(i-1);e.preventDefault();}
    else if(['f','F','а','А'].indexOf(e.key)>=0&&!document.fullscreenElement)document.documentElement.requestFullscreen().catch(function(){});
    else if(e.key==='Escape')stop();});
  document.addEventListener('fullscreenchange',function(){if(!document.fullscreenElement)document.body.classList.remove('present');});
})();
</script>"""


def head(title, extra_css=""):
    css = (HERE / "theme.css").read_text(encoding="utf-8")
    return f"""<!DOCTYPE html>
<!-- Сгенерировано theses/site/build.py из md-источников. Не править руками: правьте md и пересоберите. -->
<html lang="ru"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(title)}</title>
{FONTS}
<style>
{css}{extra_css}</style></head>"""


def page(title, hero, main):
    """Карточка: шапка + текст."""
    return head(title) + f"""
<body>
<header class="hero"><div class="wrap">
{hero}
</div></header>
<main><div class="wrap">
{main}
</div></main>
{CARD_SCRIPT}
</body></html>
"""


def deck_page(title, slides):
    """Чистые слайды: только слайды; показ, печать 16:9."""
    return head(title, "@page{size:1280px 720px;margin:0}\n") + f"""
<body class="deckpage">
<main><div class="deck">
{slides}
</div></main>
<div class="fab"><button data-present title="Показ: F или двойной клик по слайду">▶</button><button data-print title="Печать / PDF">⎙</button></div>
<div class="stage"></div>
{DECK_SCRIPT}
</body></html>
"""


def rel(target, from_dir):
    return os.path.relpath(target, from_dir).replace(os.sep, "/")


def pages_url(path):
    return PAGES + Path(path).relative_to(REPO).as_posix()


def tools(deck, base, src):
    href = rel(deck, base)
    return (f'<div class="tools"><a class="btn" href="{href}">▶ Слайды</a>'
            f'<a class="btn ghost" href="{href}?print">⎙ PDF</a>'
            f'<a class="btn ghost" href="{GH}blob/main/{src.relative_to(REPO).as_posix()}">md-источник</a></div>')


def s_top(label, link, ctx, updated):
    return (f'<div class="s-top"><a class="s-id" href="{rel(link, ctx.out_dir)}" data-pages="{pages_url(link)}">'
            f'{esc(label)}</a><span class="s-upd">обновлено {esc(updated)}</span></div>')


def slide_html(t, k, ctx, link, num, total):
    """Слайд. Служебная строка — индекс тезиса (ссылка link) и дата обновления, внизу — номер."""
    s = t["slides"][k]
    lay = s["layout"]
    bg = f' style="background-image:url(\'{esc(link_target(s["bg"], ctx))}\')"' if s["bg"] else ""
    logo = f'<img class="s-logo" src="{esc(link_target(s["logo"], ctx))}" alt="">' if s["logo"] else ""
    return (f'<section class="slide{" l-" + lay if lay else ""}"{bg}><div class="s-in">'
            + s_top(f'{t["id"]} · {t["title"]}', link, ctx, t["meta"].get("updated", ""))
            + f'<div class="s-head"><h2 class="s-title">{inline(s["title"], ctx)}</h2>{logo}</div>'
            f'<div class="s-body">{md_html(s["md"], ctx, lay)}</div>'
            f'<div class="s-foot"><span>{FOOT}</span><span>{num} / {total}</span></div>'
            "</div></section>")


def slides_seq(t, ctx, link, notes=False, start=0, total=None):
    h = []
    for k, s in enumerate(t["slides"]):
        h.append(slide_html(t, k, ctx, link, start + k + 1, total or len(t["slides"])))
        if notes and s["notes"]:
            h.append(f'<details class="notes doc"><summary>Комментарий к слайду {k + 1}</summary>'
                     f'{md_html(s["notes"], ctx)}</details>')
    return "\n".join(h)


def carousel(t, ctx, link, notes=False):
    """Компактная лента для карточки: один слайд на виду, ‹ ›, список слайдов, ▶ — показ с текущего слайда."""
    n = len(t["slides"])
    play = rel(t["deck"], ctx.out_dir)
    track = "".join(f'<div class="cr-item{" on" if k == 0 else ""}">{slide_html(t, k, ctx, link, k + 1, n)}</div>'
                    for k in range(n))
    nav = ('<button class="cr-btn cr-prev" aria-label="Предыдущий слайд">‹</button>'
           '<button class="cr-btn cr-next" aria-label="Следующий слайд">›</button>') if n > 1 else ""
    items = "".join(f'<li class="{"on" if k == 0 else ""}"><b>{k + 1}</b>{inline(s["title"], ctx)}</li>'
                    for k, s in enumerate(t["slides"]))
    com = ""
    if notes:
        com = "".join(f'<div class="cr-note doc{" on" if k == 0 else ""}">'
                      + (md_html(s["notes"], ctx) if s["notes"] else '<p class="empty">Комментария нет.</p>') + "</div>"
                      for k, s in enumerate(t["slides"]))
        com = f'<div class="cr-notes"><div class="cr-cap">Комментарий к слайду</div>{com}</div>'
    return (f'<div class="carousel" data-n="{n}"><div class="cr-stage">{track}{nav}</div>'
            f'<aside class="cr-side"><a class="btn cr-play" href="{play}?present=1" data-play="{play}">▶ Показ</a>'
            f'<ol class="cr-list">{items}</ol>{com}</aside></div>')


CARD_SCRIPT = """<script>
[].forEach.call(document.querySelectorAll('.carousel'),function(c){
  var items=c.querySelectorAll('.cr-item'),li=c.querySelectorAll('.cr-list li'),notes=c.querySelectorAll('.cr-note'),
      play=c.querySelector('.cr-play'),i=0;
  function go(k){i=(k+items.length)%items.length;
    [items,li,notes].forEach(function(l){[].forEach.call(l,function(e,j){e.classList.toggle('on',j===i);});});
    play.setAttribute('href',play.dataset.play+'?present='+(i+1));}
  var p=c.querySelector('.cr-prev'),n=c.querySelector('.cr-next');
  if(p)p.onclick=function(){go(i-1);}; if(n)n.onclick=function(){go(i+1);};
  [].forEach.call(li,function(e,j){e.onclick=function(){go(j);};});
  c.tabIndex=0;
  c.addEventListener('keydown',function(e){if(e.key==='ArrowRight'){go(i+1);e.preventDefault();}
    else if(e.key==='ArrowLeft'){go(i-1);e.preventDefault();}});
  [].forEach.call(items,function(e){e.addEventListener('dblclick',function(){location.href=play.getAttribute('href');});});
  c.go=go;
});
// старые якоря (#formula и т.п.) ведут на слайд тезиса в карусели
function hashSlide(){var a=location.hash&&document.getElementById(decodeURIComponent(location.hash.slice(1)));
  if(!a||!a.dataset.slide)return;var c=a.parentNode.querySelector('.carousel');if(c&&c.go){c.go(+a.dataset.slide-1);c.scrollIntoView();}}
window.addEventListener('hashchange',hashSlide);hashSlide();
</script>"""


def tags(meta, keys):
    out = []
    for k in keys:
        for v in split(meta.get(k)):
            out.append(f'<span class="tag">{esc(v)}</span>')
    return '<div class="tags">' + "".join(out) + "</div>"


def thesis_page(t, links, member_of):
    """Карточка тезиса: слайды с подсветкой проверок, комментарии, вопросы, задания, связи."""
    ctx = Ctx(t["dir"], t["dir"], links)
    m = t["meta"]
    hero = (f'<div class="crumbs"><a href="../site/index.html">Тезисы</a> · {esc(t["id"])}'
            + "".join(f' · <a href="{rel(a["out"], t["dir"])}">{esc(a["title"])}</a>' for a in member_of) + "</div>"
            f'<div class="eyebrow">Карточка тезиса · {esc(m.get("kind", ""))} · {len(t["slides"])} сл.</div>'
            f'<h1>{esc(t["title"])}</h1><div class="formula">{inline(m.get("formula", ""), ctx)}</div>'
            + tags(m, ["blocks", "refs"])
            + f'<div class="tags"><span class="tag">{esc(m.get("status", ""))} · {esc(m.get("version", ""))}'
              f' · обновлено {esc(m.get("updated", ""))}</span></div>' + tools(t["deck"], t["dir"], t["src"]))
    legend = ""
    if any("<mark>" in s["md"] for s in t["slides"]):
        legend = ('<p class="legend"><mark>Подсвечено</mark> то, что нужно проверить: список — в разделе '
                  '<a href="#что-проверить">«Что проверить»</a>. В <a href="slides.html">слайдах</a> '
                  'подсветки нет.</p>')
    main = (f'<div class="lead doc">{md_html(t["lead"], ctx, skip_quotes=True)}</div>{legend}'
            + carousel(t, ctx, t["deck"], notes=True)
            + '<div class="doc">' + "".join(f'<h2 id="{slug(title)}">{inline(title, ctx)}</h2>{md_html(md, ctx)}'
                                            for title, md in t["sections"]) + "</div>")
    return page(f'{t["id"]} · {t["title"]}', hero, main)


def thesis_slides(t, links):
    """Чистые слайды тезиса: индекс на слайде ведёт в карточку."""
    ctx = Ctx(t["dir"], t["dir"], links, clean=True)
    return deck_page(f'{t["id"]} · {t["title"]}', slides_seq(t, ctx, t["out"]))


def members(a, theses):
    return [theses[i["id"]] for _, its in a["groups"] for i in its if i["id"] in theses]


def anchors(meta):
    """`anchors: formula=th01:2; numbers=цифры-и-статус-проверки` → {тезис: [(якорь, слайд)]}, {раздел: [якорь]}.

    Сохраняет старые ссылки на страницу: якорь на слайд тезиса листает карусель, якорь на раздел — синоним.
    """
    to_slide, to_sec = {}, {}
    for pair in split(meta.get("anchors")):
        name, _, target = pair.partition("=")
        tid, _, num = target.strip().partition(":")
        if num:
            to_slide.setdefault(tid, []).append((name.strip(), int(num)))
        else:
            to_sec.setdefault(target.strip(), []).append(name.strip())
    return to_slide, to_sec


def assembly_page(a, theses, links):
    """Карточка сборки: разделы по порядку; группа — оглавление и карусели тезисов, текст — как есть."""
    ctx = Ctx(a["dir"], a["dir"], links)
    m = a["meta"]
    to_slide, to_sec = anchors(m)
    body = []
    for kind, title, data in a["parts"]:
        sid = slug(title)
        alias = "".join(f'<span class="anchor" id="{esc(x)}"></span>' for x in to_sec.get(sid, []))
        head = f'{alias}<h2 id="{sid}">{inline(title, ctx)}</h2>'
        if kind == "text":
            body.append(f'<div class="doc">{head}{md_html(data, ctx)}</div>')
            continue
        lis, units = [], []
        for it in data:
            t = theses.get(it["id"])
            if t:
                href = rel(t["out"], a["dir"])
                lis.append(f'<li><a href="{href}"><code>{t["id"]}</code> {esc(t["title"])}</a> — '
                           f'{inline(t["meta"].get("formula", ""), ctx)}</li>')
                tctx = Ctx(t["dir"], a["dir"], links, clean=True)
                marks = "".join(f'<span class="anchor" id="{esc(x)}" data-slide="{n}"></span>'
                                for x, n in to_slide.get(t["id"], []))
                units.append(f'<div class="unit" id="{t["id"]}">{marks}<div class="unit-h"><h3><a href="{href}">'
                             f'{t["id"]} · {esc(t["title"])}</a></h3><span class="fx">'
                             f'{inline(t["meta"].get("formula", ""), tctx)}</span></div>'
                             f'{carousel(t, tctx, t["out"])}</div>')
            else:
                if it["id"]:
                    warn(f'{a["id"]}: тезис {it["id"]} не найден')
                lis.append(f'<li class="planned">{inline(it["text"], ctx)} <span class="chk">планируется</span></li>')
        body.append(f'<div class="doc">{head}<ol>{"".join(lis)}</ol></div>{"".join(units)}')
    kind = m.get("kind", "")
    parent, _, phref = m.get("parent", "").partition("|")
    crumbs = (f'<a href="{esc(link_target(phref.strip(), ctx))}">{esc(parent.strip())}</a> · {esc(kind)}'
              if parent else f'<a href="{rel(HERE / "index.html", a["dir"])}">Тезисы</a> · сборки')
    hero = (f'<div class="crumbs">{crumbs} · {esc(a["id"])}</div>'
            f'<div class="eyebrow">{"Кейс" if kind == "кейс" else "Карточка сборки · " + esc(kind)}</div>'
            f'<h1>{esc(a["title"])}</h1>'
            + (f'<div class="formula">{inline(m["formula"], ctx)}</div>' if m.get("formula") else "")
            + tags(m, ["frame"]) + tools(a["deck"], a["dir"], a["src"]))
    main = f'<div class="lead doc">{md_html(a["lead"], ctx, skip_quotes=True)}</div>{"".join(body)}'
    return page(f'{a["title"]} · {kind or "сборка"}', hero, main)


def assembly_slides(a, theses, links):
    """Чистые слайды сборки: обложка + слайды тезисов со сквозной нумерацией."""
    ctx = Ctx(a["dir"], a["dir"], links, clean=True)
    m = a["meta"]
    ts = members(a, theses)
    total = 1 + sum(len(t["slides"]) for t in ts)
    items = []
    for _, its in a["groups"]:
        for it in its:
            t = theses.get(it["id"])
            items.append(f'<li>{esc(t["title"])}</li>' if t else
                         f'<li style="opacity:.55">{inline(it["text"], ctx)}</li>')
    h = [f'<section class="slide cover"><div class="s-in">'
         + s_top(f'{m.get("kind", "сборка")} · {a["title"]}', a["out"], ctx, m.get("updated", ""))
         + f'<h2 class="s-title">{esc(a["title"])}</h2><div class="s-body"><ol>{"".join(items)}</ol></div>'
         f'<div class="s-foot"><span>{FOOT}</span><span>1 / {total}</span></div></div></section>']
    n = 1
    for t in ts:
        h.append(slides_seq(t, Ctx(t["dir"], a["dir"], links, clean=True), t["out"], start=n, total=total))
        n += len(t["slides"])
    return deck_page(f'{a["title"]} · слайды', "\n".join(h))


def index_page(theses, assemblies):
    def card(kind, title, href, deck, fx, meta):
        return (f'<div class="card"><span class="k">{kind}</span><h3><a href="{href}">{esc(title)}</a></h3>'
                f'<span class="fx">{esc(fx)}</span><span class="meta">{meta}</span>'
                f'<span class="meta"><a href="{href}">карточка</a> · <a href="{deck}">слайды</a></span></div>')

    cards = "".join(card(f'{t["id"]} · {esc(t["meta"].get("kind", ""))} · {len(t["slides"])} сл.', t["title"],
                         rel(t["out"], HERE), rel(t["deck"], HERE), t["meta"].get("formula", ""),
                         f'{esc(t["meta"].get("blocks", ""))} · {esc(t["meta"].get("status", ""))} · '
                         f'обновлено {esc(t["meta"].get("updated", ""))}') for t in theses.values())
    acards = "".join(card(esc(a["meta"].get("kind", "")), a["title"], rel(a["out"], HERE), rel(a["deck"], HERE), "",
                          f'{len(members(a, theses))} тезисов собрано · '
                          f'{sum(1 for _, its in a["groups"] for i in its if i["id"] not in theses)} планируется')
                     for a in assemblies)
    hero = ('<div class="crumbs"><a href="../../index.html">Мастерская</a> · тезисы</div>'
            '<div class="eyebrow">База единиц контента</div><h1>Тезисы</h1>'
            '<div class="formula">Одна мысль — одна формула — 1–3 слайда. Из тезисов собираются лекции, курсы, '
            'серии и методологии; каждый тезис порождает вопросы и задания.</div>'
            f'<div class="tools"><a class="btn ghost" href="{GH}blob/main/theses/README.md">Модель слоя</a></div>')
    main = (f'<div class="doc"><h2>Тезисы · {len(theses)}</h2></div><div class="cards">{cards}</div>'
            f'<div class="doc"><h2>Сборки · {len(assemblies)}</h2></div><div class="cards">{acards}</div>')
    return page("Тезисы мастерской", hero, main)


# ---------------------------------------------------------------- индексы CSV

def write_csv(name, header, rows):
    (ROOT / "catalog").mkdir(exist_ok=True)
    with open(ROOT / "catalog" / name, "w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(header)
        w.writerows(rows)


# ---------------------------------------------------------------- экспорт

def browser():
    cands = [os.environ.get("THESES_BROWSER", "")]
    cands += [shutil.which(n) or "" for n in ("chrome", "google-chrome", "chromium", "chromium-browser", "msedge")]
    cands += [r"C:\Program Files\Google\Chrome\Application\chrome.exe",
              r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
              r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
              "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
              "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge"]
    for c in cands:
        if c and os.path.exists(c):
            return c
    sys.exit("Не найден Chrome/Edge для экспорта. Укажите путь в переменной THESES_BROWSER.")


def headless(args, url, out):
    """Запускает браузер и ждёт файл: на Windows msedge.exe возвращается раньше, чем допишет результат."""
    out.unlink(missing_ok=True)
    prof = tempfile.mkdtemp(prefix="theses-browser-")
    subprocess.run([browser(), "--headless=new", "--disable-gpu", "--hide-scrollbars",
                    f"--user-data-dir={prof}", "--virtual-time-budget=8000", *args, url],
                   check=True, capture_output=True)
    size, deadline = -1, time.time() + 90
    while time.time() < deadline:
        cur = out.stat().st_size if out.exists() else -1
        if cur > 0 and cur == size:
            break
        size = cur
        time.sleep(0.7)
    else:
        sys.exit(f"Браузер не создал {out}")
    shutil.rmtree(prof, ignore_errors=True)


def export_pdf(deck, name):
    out = EXPORT / f"{name}.pdf"
    headless(["--no-pdf-header-footer", f"--print-to-pdf={out}"], deck.as_uri() + "?export", out)
    print("  pdf ", out.relative_to(REPO))


def link_box(prs, sl, url, label):
    """Невидимая кликабельная область поверх индекса на кадре слайда → карточка на GitHub Pages."""
    from pptx.enum.shapes import MSO_SHAPE
    from pptx.dml.color import RGBColor
    from pptx.oxml.ns import qn
    px = prs.slide_width / 1280
    w = min(len(label) * 10 + 24, 900)
    shp = sl.shapes.add_shape(MSO_SHAPE.RECTANGLE, int(44 * px), int(28 * px), int(w * px), int(34 * px))
    style = shp._element.find(qn("p:style"))
    if style is not None:
        shp._element.remove(style)
    shp.fill.solid()
    shp.fill.fore_color.rgb = RGBColor(255, 255, 255)
    clr = shp._element.spPr.find(qn("a:solidFill"))[0]
    clr.append(clr.makeelement(qn("a:alpha"), {"val": "0"}))
    shp.line.fill.background()
    shp.click_action.hyperlink.address = url
    shp.name = "Ссылка на карточку"


def export_pptx(deck, name, frames_info):
    """frames_info: [(заметки, url карточки, подпись индекса)] по слайдам."""
    from pptx import Presentation
    from pptx.util import Inches
    frames = EXPORT / "frames" / name
    frames.mkdir(parents=True, exist_ok=True)
    prs = Presentation()
    prs.slide_width, prs.slide_height = Inches(13.333), Inches(7.5)
    for k, (notes, url, label) in enumerate(frames_info):
        png = frames / f"{k + 1:02d}.png"
        headless(["--window-size=1280,720", "--force-device-scale-factor=2", f"--screenshot={png}"],
                 f"{deck.as_uri()}?frame={k + 1}", png)
        sl = prs.slides.add_slide(prs.slide_layouts[6])
        sl.shapes.add_picture(str(png), 0, 0, prs.slide_width, prs.slide_height)
        link_box(prs, sl, url, label)
        sl.notes_slide.notes_text_frame.text = notes
    out = EXPORT / f"{name}.pptx"
    prs.save(out)
    print("  pptx", out.relative_to(REPO))


def frames_info(t):
    label = f'{t["id"]} · {t["title"]}'
    return [(f'{s["title"]}\n\n{plain(s["md"])}' + (f'\n\n— Комментарий —\n{plain(s["notes"])}' if s["notes"] else ""),
             pages_url(t["out"]), label) for s in t["slides"]]


# ---------------------------------------------------------------- main

def main():
    want_pdf = "--pdf" in sys.argv or "--export" in sys.argv
    want_pptx = "--pptx" in sys.argv or "--export" in sys.argv

    theses = {}
    for readme in sorted(glob.glob(str(ROOT / "th*" / "README.md"))):
        t = load_thesis(readme)
        if t["id"] in theses:
            warn(f'{t["id"]}: повторяющийся id')
        theses[t["id"]] = t
    assemblies = [load_assembly(p) for p in sorted(glob.glob(str(ROOT / "assemblies" / "*.md"))) + case_sources()]

    links = {t["src"]: t["out"] for t in theses.values()}
    links.update({a["src"]: a["out"] for a in assemblies})
    member = {tid: [a for a in assemblies if any(i["id"] == tid for _, its in a["groups"] for i in its)]
              for tid in theses}

    def write(path, text):
        path.write_text(text, encoding="utf-8")
        print("html", path.relative_to(REPO))

    for t in theses.values():
        write(t["out"], thesis_page(t, links, member[t["id"]]))
        write(t["deck"], thesis_slides(t, links))
    for a in assemblies:
        write(a["out"], assembly_page(a, theses, links))
        write(a["deck"], assembly_slides(a, theses, links))
    write(HERE / "index.html", index_page(theses, assemblies))

    write_csv("theses.csv",
              ["thesis_id", "title", "formula", "kind", "blocks", "refs", "questions", "assignments", "dossier",
               "slides", "assemblies", "status", "version", "updated", "file"],
              [[t["id"], t["title"], t["meta"].get("formula", ""), t["meta"].get("kind", ""),
                t["meta"].get("blocks", ""), t["meta"].get("refs", ""), t["meta"].get("questions", ""),
                t["meta"].get("assignments", ""), t["meta"].get("dossier", ""), len(t["slides"]),
                ";".join(a["id"] for a in member[t["id"]]), t["meta"].get("status", ""),
                t["meta"].get("version", ""), t["meta"].get("updated", ""),
                t["src"].relative_to(ROOT).as_posix()] for t in theses.values()])
    write_csv("assemblies.csv",
              ["assembly_id", "title", "kind", "frame", "theses", "planned", "status", "updated", "file"],
              [[a["id"], a["title"], a["meta"].get("kind", ""), a["meta"].get("frame", ""),
                ";".join(t["id"] for t in members(a, theses)),
                ";".join(plain(i["text"]) for _, its in a["groups"] for i in its if i["id"] not in theses),
                a["meta"].get("status", ""), a["meta"].get("updated", ""),
                rel(a["src"], ROOT)] for a in assemblies])
    print("csv  theses/catalog/theses.csv, theses/catalog/assemblies.csv")

    if want_pdf or want_pptx:
        EXPORT.mkdir(exist_ok=True)
        for t in theses.values():
            name = t["dir"].name
            if want_pdf:
                export_pdf(t["deck"], name)
            if want_pptx:
                export_pptx(t["deck"], name, frames_info(t))
        for a in assemblies:
            if want_pdf:
                export_pdf(a["deck"], a["id"])
            if want_pptx:
                cover = (a["title"], pages_url(a["out"]), f'{a["meta"].get("kind", "сборка")} · {a["title"]}')
                export_pptx(a["deck"], a["id"], [cover] + [f for t in members(a, theses) for f in frames_info(t)])

    for w in WARN:
        print("ВНИМАНИЕ:", w)


if __name__ == "__main__":
    main()
