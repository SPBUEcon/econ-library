# -*- coding: utf-8 -*-
"""Собирает представления тезисов из md-источников.

Источник правды — карточки theses/th*/README.md и сборки theses/assemblies/*.md.
Всё остальное — представления в едином стиле (theme.css):

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

    def __init__(self, src_dir, out_dir, theses=None):
        self.src_dir = Path(src_dir)
        self.out_dir = Path(out_dir)
        self.theses = theses or {}     # путь README.md → путь index.html и т.п.


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
    s = esc(s)
    s = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s)

    def em(m):
        t = m.group(1)
        return '<span class="chk">проверить</span>' if CHK.match(t) else f"<em>{t}</em>"

    s = re.sub(r"(?<![*\w])\*(?![\s*])(.+?)(?<![\s*])\*(?![*\w])", em, s)
    return re.sub(r"\x00(\d+)\x00", lambda m: keep[int(m.group(1))], s)


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
            out.append(("pre", "\n".join(lines[i + 1:j])))
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
            h.append(f"<h{lvl}>{inline(d[1], ctx)}</h{lvl}>")
        elif kind == "pre":
            h.append(f"<pre>{esc(d)}</pre>")
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
                cols.append(f'<div class="col"><div class="col-h">{inline(title, ctx)}'
                            + (f"<span>{inline(sub, ctx)}</span>" if sub else "") + "</div><ul>"
                            + "".join(f"<li>{inline(x, ctx)}</li>" for x in items) + "</ul></div>")
            h.append('<div class="cols">' + "".join(cols) + "</div>")
        elif kind == "table":
            head, rows = d
            h.append("<table><thead><tr>" + "".join(f"<th>{inline(c, ctx)}</th>" for c in head) + "</tr></thead><tbody>"
                     + "".join("<tr>" + "".join(f"<td>{inline(c, ctx)}</td>" for c in r) + "</tr>" for r in rows)
                     + "</tbody></table>")
    return "\n".join(h)


def md_html(md, ctx, layout="", skip_quotes=False):
    bl = blocks(md)
    if skip_quotes:
        bl = [b for b in bl if b[0] != "quote"]
    return render(bl, ctx, layout)


def plain(md):
    """md → простой текст (заметки PPTX)."""
    t = re.sub(r"<!--.*?-->", "", md, flags=re.S)
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
        lay = re.search(r"<!--\s*layout:\s*([\w-]+)\s*-->", md)
        content, notes = (re.split(r"<!--\s*notes\s*-->", md, maxsplit=1) + [""])[:2]
        t["slides"].append({"title": m.group(1).strip(), "layout": lay.group(1) if lay else "",
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
    return t


ITEM = re.compile(r"`(th\d+)`")


def load_assembly(path):
    text = Path(path).read_text(encoding="utf-8").replace("\r\n", "\n")
    meta, body = front(text)
    h1, lead, secs = sections(body)
    groups = []
    for title, md in secs:
        items = []
        for kind, d in blocks(md):
            if kind in ("ul", "ol"):
                for x in d:
                    m = ITEM.search(x)
                    items.append({"id": m.group(1) if m else "", "text": ITEM.sub("", x, count=1).strip() if m else x})
        groups.append((title, items))
    p = Path(path)
    return {"meta": meta, "h1": h1, "lead": lead, "groups": groups, "id": meta.get("id", p.stem),
            "title": meta.get("title", h1), "src": p.resolve(), "dir": p.parent, "out": p.with_suffix(".html")}


# ---------------------------------------------------------------- страницы

SCRIPT = """<script>
(function(){
  var slides=[].slice.call(document.querySelectorAll('main .slide')), stage=document.querySelector('.stage'), i=0;
  function show(k){i=Math.max(0,Math.min(slides.length-1,k));stage.innerHTML='';stage.appendChild(slides[i].cloneNode(true));}
  var q=new URLSearchParams(location.search);
  if(q.has('frame')){document.body.classList.add('frame');show((+q.get('frame')||1)-1);return;}
  function start(k){document.body.classList.add('present');show(k||0);
    if(document.documentElement.requestFullscreen)document.documentElement.requestFullscreen().catch(function(){});}
  function stop(){document.body.classList.remove('present');if(document.fullscreenElement)document.exitFullscreen();}
  [].forEach.call(document.querySelectorAll('[data-present]'),function(b){b.onclick=function(){start(0);};});
  [].forEach.call(document.querySelectorAll('[data-print]'),function(b){b.onclick=function(){window.print();};});
  slides.forEach(function(s,k){s.addEventListener('dblclick',function(){start(k);});s.title='Двойной клик — показ с этого слайда';});
  stage.addEventListener('click',function(e){show(e.clientX>innerWidth/3?i+1:i-1);});
  document.addEventListener('keydown',function(e){
    if(!document.body.classList.contains('present'))return;
    if(['ArrowRight','PageDown',' ','Enter'].indexOf(e.key)>=0){show(i+1);e.preventDefault();}
    else if(['ArrowLeft','PageUp','Backspace'].indexOf(e.key)>=0){show(i-1);e.preventDefault();}
    else if(e.key==='Escape')stop();});
  document.addEventListener('fullscreenchange',function(){if(!document.fullscreenElement)document.body.classList.remove('present');});
})();
</script>"""


def page(title, hero, main):
    css = (HERE / "theme.css").read_text(encoding="utf-8")
    return f"""<!DOCTYPE html>
<!-- Сгенерировано theses/site/build.py из md-источников. Не править руками: правьте md и пересоберите. -->
<html lang="ru"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(title)}</title>
{FONTS}
<style>
{css}</style></head>
<body>
<header class="hero"><div class="wrap">
{hero}
</div></header>
<main><div class="wrap">
{main}
</div></main>
<div class="stage"></div>
{SCRIPT}
</body></html>
"""


def tools(src):
    return ('<div class="tools"><button class="btn" data-present>▶ Показать</button>'
            '<button class="btn ghost" data-print>⎙ Печать / PDF</button>'
            f'<a class="btn ghost" href="{GH}blob/main/{src.relative_to(REPO).as_posix()}">md-источник</a></div>')


def slide_html(t, k, ctx):
    s = t["slides"][k]
    lay = s["layout"]
    return (f'<section class="slide{" l-" + lay if lay else ""}"><div class="s-in">'
            f'<div class="s-top"><span>{esc(t["id"])} · {esc(t["title"])}</span>'
            f'<span class="n">{k + 1} / {len(t["slides"])}</span></div>'
            f'<h2 class="s-title">{inline(s["title"], ctx)}</h2>'
            f'<div class="s-body">{md_html(s["md"], ctx, lay)}</div>'
            f'<div class="s-foot"><span>{FOOT}</span><span>{esc(t["meta"].get("version", ""))}</span></div>'
            "</div></section>")


def deck_html(t, ctx, notes=True):
    h = []
    for k, s in enumerate(t["slides"]):
        h.append(slide_html(t, k, ctx))
        if notes and s["notes"]:
            h.append(f'<details class="notes doc"><summary>Комментарий к слайду {k + 1}</summary>'
                     f'{md_html(s["notes"], ctx)}</details>')
    return '<div class="deck">' + "\n".join(h) + "</div>"


def tags(meta, keys):
    out = []
    for k in keys:
        for v in split(meta.get(k)):
            out.append(f'<span class="tag">{esc(v)}</span>')
    return '<div class="tags">' + "".join(out) + "</div>"


def thesis_page(t, links, member_of):
    ctx = Ctx(t["dir"], t["dir"], links)
    m = t["meta"]
    hero = (f'<div class="crumbs"><a href="../site/index.html">Тезисы</a> · {esc(t["id"])}'
            + "".join(f' · <a href="{os.path.relpath(a["out"], t["dir"]).replace(os.sep, "/")}">{esc(a["title"])}</a>'
                      for a in member_of) + "</div>"
            f'<div class="eyebrow">Тезис · {esc(m.get("kind", ""))} · {len(t["slides"])} сл.</div>'
            f'<h1>{esc(t["title"])}</h1><div class="formula">{inline(m.get("formula", ""), ctx)}</div>'
            + tags(m, ["blocks", "refs"])
            + f'<div class="tags"><span class="tag">{esc(m.get("status", ""))} · {esc(m.get("version", ""))}'
              f' · {esc(m.get("updated", ""))}</span></div>' + tools(t["src"]))
    main = (f'<div class="lead doc">{md_html(t["lead"], ctx, skip_quotes=True)}</div>'
            + deck_html(t, ctx)
            + '<div class="doc">' + "".join(f"<h2>{inline(title, ctx)}</h2>{md_html(md, ctx)}"
                                            for title, md in t["sections"]) + "</div>")
    return page(f'{t["id"]} · {t["title"]}', hero, main)


def assembly_page(a, theses, links):
    ctx = Ctx(a["dir"], a["dir"], links)
    m = a["meta"]
    toc, units, cover_items = [], [], []
    for gtitle, items in a["groups"]:
        lis = []
        for it in items:
            t = theses.get(it["id"])
            if t:
                href = os.path.relpath(t["out"], a["dir"]).replace(os.sep, "/")
                lis.append(f'<li><a href="{href}"><code>{t["id"]}</code> {esc(t["title"])}</a> — '
                           f'{inline(t["meta"].get("formula", ""), ctx)}</li>')
                cover_items.append(f'<li>{esc(t["title"])}</li>')
                tctx = Ctx(t["dir"], a["dir"], links)
                units.append(f'<div class="unit" id="{t["id"]}"><div class="unit-h"><h2><a href="{href}">'
                             f'{t["id"]} · {esc(t["title"])}</a></h2><span class="fx">'
                             f'{inline(t["meta"].get("formula", ""), tctx)}</span></div>{deck_html(t, tctx, notes=False)}</div>')
            else:
                if it["id"]:
                    warn(f'{a["id"]}: тезис {it["id"]} не найден')
                lis.append(f'<li class="planned">{inline(it["text"], ctx)} <span class="chk">планируется</span></li>')
                cover_items.append(f'<li style="opacity:.55">{inline(it["text"], ctx)}</li>')
        toc.append(f"<h2>{inline(gtitle, ctx)}</h2><ol>{''.join(lis)}</ol>")
    cover = (f'<div class="deck"><section class="slide cover"><div class="s-in">'
             f'<div class="s-top"><span>{esc(m.get("kind", "сборка"))}</span><span class="n">{esc(a["id"])}</span></div>'
             f'<h2 class="s-title">{esc(a["title"])}</h2><div class="s-body"><ol>{"".join(cover_items)}</ol></div>'
             f'<div class="s-foot"><span>{FOOT}</span><span>{esc(m.get("updated", ""))}</span></div></div></section></div>')
    hero = (f'<div class="crumbs"><a href="../site/index.html">Тезисы</a> · сборки · {esc(a["id"])}</div>'
            f'<div class="eyebrow">Сборка · {esc(m.get("kind", ""))}</div><h1>{esc(a["title"])}</h1>'
            + tags(m, ["frame"]) + tools(a["src"]))
    main = (f'<div class="lead doc">{md_html(a["lead"], ctx, skip_quotes=True)}</div>'
            f'<div class="doc">{"".join(toc)}</div>{cover}{"".join(units)}')
    return page(f'{a["title"]} · сборка', hero, main)


def index_page(theses, assemblies):
    cards = "".join(
        f'<a class="card" style="text-decoration:none;color:inherit" href="../{t["dir"].name}/index.html">'
        f'<span class="k">{t["id"]} · {esc(t["meta"].get("kind", ""))} · {len(t["slides"])} сл.</span>'
        f'<h3>{esc(t["title"])}</h3><span class="fx">{esc(t["meta"].get("formula", ""))}</span>'
        f'<span class="meta">{esc(t["meta"].get("blocks", ""))} · {esc(t["meta"].get("status", ""))} · '
        f'{esc(t["meta"].get("updated", ""))}</span></a>' for t in theses.values())
    acards = "".join(
        f'<a class="card" style="text-decoration:none;color:inherit" href="../assemblies/{a["out"].name}">'
        f'<span class="k">{esc(a["meta"].get("kind", ""))}</span><h3>{esc(a["title"])}</h3>'
        f'<span class="meta">{sum(1 for _, its in a["groups"] for i in its if i["id"] in theses)} тезисов собрано · '
        f'{sum(1 for _, its in a["groups"] for i in its if i["id"] not in theses)} планируется</span></a>'
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


def export_pdf(src, name):
    out = EXPORT / f"{name}.pdf"
    headless(["--no-pdf-header-footer", f"--print-to-pdf={out}"], src.as_uri(), out)
    print("  pdf ", out.relative_to(REPO))


def export_pptx(src, name, n, notes):
    from pptx import Presentation
    from pptx.util import Inches
    frames = EXPORT / "frames" / name
    frames.mkdir(parents=True, exist_ok=True)
    prs = Presentation()
    prs.slide_width, prs.slide_height = Inches(13.333), Inches(7.5)
    for k in range(n):
        png = frames / f"{k + 1:02d}.png"
        headless(["--window-size=1280,720", "--force-device-scale-factor=2", f"--screenshot={png}"],
                 f"{src.as_uri()}?frame={k + 1}", png)
        sl = prs.slides.add_slide(prs.slide_layouts[6])
        sl.shapes.add_picture(str(png), 0, 0, prs.slide_width, prs.slide_height)
        sl.notes_slide.notes_text_frame.text = notes[k]
    out = EXPORT / f"{name}.pptx"
    prs.save(out)
    print("  pptx", out.relative_to(REPO))


def slide_notes(t):
    return [f'{s["title"]}\n\n{plain(s["md"])}' + (f'\n\n— Комментарий —\n{plain(s["notes"])}' if s["notes"] else "")
            for s in t["slides"]]


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
    assemblies = [load_assembly(p) for p in sorted(glob.glob(str(ROOT / "assemblies" / "*.md")))]

    links = {t["src"]: t["out"] for t in theses.values()}
    links.update({a["src"]: a["out"] for a in assemblies})
    member = {tid: [a for a in assemblies if any(i["id"] == tid for _, its in a["groups"] for i in its)]
              for tid in theses}

    for t in theses.values():
        t["out"].write_text(thesis_page(t, links, member[t["id"]]), encoding="utf-8")
        print("html", t["out"].relative_to(REPO))
    for a in assemblies:
        a["out"].write_text(assembly_page(a, theses, links), encoding="utf-8")
        print("html", a["out"].relative_to(REPO))
    (HERE / "index.html").write_text(index_page(theses, assemblies), encoding="utf-8")
    print("html", (HERE / "index.html").relative_to(REPO))

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
                ";".join(i["id"] for _, its in a["groups"] for i in its if i["id"] in theses),
                ";".join(plain(i["text"]) for _, its in a["groups"] for i in its if i["id"] not in theses),
                a["meta"].get("status", ""), a["meta"].get("updated", ""),
                a["src"].relative_to(ROOT).as_posix()] for a in assemblies])
    print("csv  theses/catalog/theses.csv, theses/catalog/assemblies.csv")

    if want_pdf or want_pptx:
        EXPORT.mkdir(exist_ok=True)
        for t in theses.values():
            name = t["dir"].name
            if want_pdf:
                export_pdf(t["out"], name)
            if want_pptx:
                export_pptx(t["out"], name, len(t["slides"]), slide_notes(t))
        for a in assemblies:
            ts = [theses[i["id"]] for _, its in a["groups"] for i in its if i["id"] in theses]
            if want_pdf:
                export_pdf(a["out"], a["id"])
            if want_pptx:
                notes = [a["title"]] + [n for t in ts for n in slide_notes(t)]
                export_pptx(a["out"], a["id"], len(notes), notes)

    for w in WARN:
        print("ВНИМАНИЕ:", w)


if __name__ == "__main__":
    main()
