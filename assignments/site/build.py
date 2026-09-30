# -*- coding: utf-8 -*-
"""Собирает витрину архива заданий assignments/site/index.html из CSV каталога.

Источник правды — assignments/catalog/*.csv и паспорта досье (dossiers/<досье>/README.md).
Страница самодостаточная: данные встроены, работает по file:// и на GitHub Pages.

    python assignments/site/build.py
"""
import csv
import datetime
import glob
import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)                      # assignments/
CAT = os.path.join(ROOT, "catalog")
OUT = os.path.join(HERE, "index.html")
GH = "https://github.com/SPBUEcon/econ-library/blob/main/assignments/"

# страницы кейсов курса по досье (путь относительно assignments/site/)
CASE_PAGES = {
    "red-bull": "../../disciplines/technologies-econ-fin/cases/red-bull/index.html",
}


def load(name):
    with open(os.path.join(CAT, name), encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def split(v):
    return [x.strip() for x in (v or "").split(";") if x.strip()]


def passport(path):
    """Стадия, версия и объект из таблицы «Паспорт» README досье."""
    text = open(path, encoding="utf-8").read()

    def field(name):
        m = re.search(r"^\| " + name + r" \| (.+?) \|$", text, re.M)
        return re.sub(r"\*\*|\[|\]\([^)]*\)|`", "", m.group(1)).strip() if m else ""

    title = re.search(r"^# (.+)$", text, re.M)
    return {
        "title": title.group(1).strip() if title else "",
        "object": field("Объект").split(" (")[0],
        "stage": field("Стадия"),
        "version": field("Версия").split(" ")[0],
        "updated": field("Последнее обновление"),
    }


templates = load("templates.csv")
issues = load("issues.csv")
issued = {}
for i in issues:
    issued[i["template_id"]] = issued.get(i["template_id"], 0) + 1

for t in templates:
    for k in ("mechanic_ids", "skill_ids", "scale", "entry_stage", "related_questions"):
        t[k] = split(t[k])
    t["issued"] = issued.get(t["template_id"], 0)
    f = t["file"]
    t["card_url"] = GH + f if f.startswith("templates/") else ""
    t["case_page"] = CASE_PAGES.get(t["dossier_id"], "")

dossiers = []
for readme in sorted(glob.glob(os.path.join(ROOT, "dossiers", "*", "README.md"))):
    did = os.path.basename(os.path.dirname(readme))
    p = passport(readme)
    p.update({
        "dossier_id": did,
        "url": GH + "dossiers/" + did + "/README.md",
        "gaps_url": GH + "dossiers/" + did + "/open-questions.md",
        "case_page": CASE_PAGES.get(did, ""),
        "tasks": [t["template_id"] for t in templates if t["dossier_id"] == did],
    })
    dossiers.append(p)

data = {
    "templates": templates,
    "types": load("types.csv"),
    "skills": load("skills.csv"),
    "mechanics": load("mechanics.csv"),
    "dossiers": dossiers,
    "issuesTotal": len(issues),
    "gh": GH,
}
DATA_JSON = json.dumps(data, ensure_ascii=False)
GEN_DATE = datetime.date.today().isoformat()

HTML = r"""<!DOCTYPE html>
<!--
  Архив заданий Мастерской «Технологии в экономике».
  СГЕНЕРИРОВАНО скриптом assignments/site/build.py из assignments/catalog/*.csv — не править руками.
  Собрано: __GEN_DATE__.
-->
<html lang="ru">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Архив заданий — Мастерская «Технологии в экономике»</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Unbounded:wght@500;700&family=IBM+Plex+Sans:wght@400;500;600&display=swap" rel="stylesheet">
<style>
:root{
  color-scheme: light;
  --ink:#1B2038; --ink2:#272E52; --card:#2E3660;
  --paper:#FAFBFE; --panel:#EFF3FA; --ice:#DCE6F5;
  --coral:#F0614F; --grey:#5A6072; --line:#D7E0F0;
  --green:#2FA37A; --amber:#D9932B; --blue:#3E7BD6; --violet:#7A5AD9;
  --disp:'Unbounded','Arial Black',sans-serif;
  --body:'IBM Plex Sans',Arial,sans-serif;
}
*{margin:0;padding:0;box-sizing:border-box}
html{scroll-behavior:smooth}
@media (prefers-reduced-motion: reduce){html{scroll-behavior:auto}}
body{font-family:var(--body);background:var(--paper);color:var(--ink);line-height:1.5}
.wrap{max-width:1200px;margin:0 auto;padding:0 28px}
section{padding:56px 0;scroll-margin-top:150px}
section.alt{background:var(--panel)}
a{color:inherit}
.eyebrow{font-size:13px;letter-spacing:.14em;text-transform:uppercase;color:var(--coral);font-weight:600;margin-bottom:14px}
h2{font-family:var(--disp);font-weight:700;font-size:clamp(24px,3vw,34px);line-height:1.15;margin-bottom:12px}
h2 .cnt{font-family:var(--body);font-weight:500;font-size:16px;color:var(--grey);vertical-align:middle;margin-left:10px}
.lead{font-size:clamp(15px,1.6vw,18px);color:var(--grey);max-width:860px;margin-bottom:22px}
.lead a,.small a{color:var(--coral);font-weight:600}

/* HERO */
.hero{background:var(--ink);color:#fff;padding:58px 0 52px}
.hero .eyebrow{color:var(--ice)}
.crumbs{font-size:13px;color:var(--ice);margin-bottom:20px}
.crumbs a{color:var(--ice)}
.hero h1{font-family:var(--disp);font-weight:700;font-size:clamp(26px,4vw,46px);line-height:1.12;max-width:980px}
.hero h1 .accent{color:var(--coral)}
.hero .sub{margin-top:18px;font-size:clamp(15px,1.8vw,19px);color:var(--ice);max-width:860px}
.stat-row{display:flex;flex-wrap:wrap;gap:10px;margin-top:30px}
.stat{background:var(--ink2);border-radius:14px;padding:12px 18px}
.stat b{font-family:var(--disp);font-weight:700;font-size:21px;color:#fff;display:block}
.stat span{font-size:12px;color:var(--ice);letter-spacing:.04em}

/* HOW */
.kinds{display:grid;grid-template-columns:repeat(3,1fr);gap:16px}
.steps4{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-top:22px;list-style:none;counter-reset:s}
@media (max-width:900px){.kinds,.steps4{grid-template-columns:1fr}}
.kind{background:#fff;border:1px solid var(--line);border-radius:18px;padding:20px;border-top:6px solid var(--grey)}
.kind.fixed{border-top-color:var(--blue)} .kind.param{border-top-color:var(--violet)} .kind.relay{border-top-color:var(--coral)}
.kind h3{font-family:var(--disp);font-weight:500;font-size:17px;margin-bottom:6px}
.kind p{font-size:14.5px;color:var(--grey)}
.kind .ex{margin-top:10px;font-size:13.5px;color:var(--ink)}
.steps4 li{counter-increment:s;background:#fff;border:1px solid var(--line);border-radius:14px;padding:14px 16px;font-size:14.5px}
.steps4 li::before{content:counter(s);display:block;font-family:var(--disp);font-weight:700;color:var(--coral);font-size:18px;margin-bottom:4px}
.steps4 li b{display:block}

/* CONTROLS */
.nav{position:sticky;top:0;z-index:50;background:rgba(250,251,254,.95);backdrop-filter:blur(8px);border-bottom:1px solid var(--line)}
.nav .wrap{display:flex;flex-direction:column;gap:10px;padding-top:12px;padding-bottom:12px}
.nav-links{display:flex;gap:6px;flex-wrap:wrap}
.nav-links a{font-size:13.5px;font-weight:600;color:var(--grey);text-decoration:none;padding:6px 11px;border-radius:9px}
.nav-links a:hover{background:var(--panel);color:var(--ink)}
.controls{display:flex;gap:8px;flex-wrap:wrap;align-items:center}
.chips{display:flex;gap:6px;flex-wrap:wrap}
.chip{font-family:var(--body);font-size:12.5px;font-weight:600;border:1.5px solid var(--line);background:#fff;color:var(--grey);
  border-radius:999px;padding:6px 13px;cursor:pointer}
.chip:hover{border-color:var(--coral);color:var(--ink)}
.chip.on{background:var(--ink);color:#fff;border-color:var(--ink)}
.chip.on[data-kind="fixed"]{background:var(--blue);border-color:var(--blue)}
.chip.on[data-kind="param"]{background:var(--violet);border-color:var(--violet)}
.chip.on[data-kind="relay"]{background:var(--coral);border-color:var(--coral)}
select,.search input{font-family:var(--body);font-size:13.5px;padding:7px 10px;border:1.5px solid var(--line);border-radius:10px;background:#fff;color:var(--ink)}
select{max-width:220px}
.search{flex:1;min-width:180px;max-width:300px}
.search input{width:100%}
@media (max-width:760px){.nav{position:static}.wrap{padding:0 18px}}
button.reset{font-family:var(--body);font-size:13px;font-weight:600;background:none;border:none;color:var(--coral);cursor:pointer;padding:6px}

/* LIST — задания лентой, одна широкая плашка на задание */
.list{display:flex;flex-direction:column;gap:10px}
.card{background:#fff;border:1px solid var(--line);border-left:6px solid var(--grey);border-radius:16px;
  padding:18px 22px;display:grid;grid-template-columns:150px minmax(0,1fr) 200px;gap:6px 26px;align-items:start}
.card:hover{box-shadow:0 8px 24px rgba(27,32,56,.07)}
.card[data-kind="fixed"]{border-left-color:var(--blue)}
.card[data-kind="param"]{border-left-color:var(--violet)}
.card[data-kind="relay"]{border-left-color:var(--coral)}
.card .side{display:flex;flex-direction:column;align-items:flex-start;gap:6px}
.cid{font-family:var(--disp);font-size:15px;font-weight:700;color:var(--ink)}
.badge{font-size:11.5px;font-weight:600;border-radius:999px;padding:2px 9px;background:var(--panel);color:var(--grey)}
.badge.fixed{background:#E6EEFB;color:var(--blue)} .badge.param{background:#EEE9FB;color:var(--violet)} .badge.relay{background:#FDE9E6;color:var(--coral)}
.badge.active{background:#E3F4EC;color:var(--green)}
.card .ty{font-size:12.5px;color:var(--grey);line-height:1.35}
.card h4{font-family:var(--disp);font-weight:500;font-size:17px;line-height:1.3;margin-bottom:6px}
.card p.brief{font-size:14.5px;margin-bottom:8px;max-width:820px}
.facts{font-size:13px;color:var(--grey);margin-bottom:6px}
.facts b{color:var(--ink);font-weight:600}
.facts .sep{margin:0 7px;color:var(--line)}
.sk{display:inline-block;font-size:12px;font-weight:600;background:var(--panel);color:var(--ink);border-radius:7px;padding:1px 8px;margin:0 4px 4px 0}
details{font-size:13.5px;margin-top:4px}
details summary{cursor:pointer;font-weight:600;color:var(--coral);width:max-content}
details p{margin-top:6px;max-width:860px}
.card .act{display:flex;flex-direction:column;gap:6px;font-size:13.5px}
.card .act a{font-weight:600;text-decoration:none;color:var(--coral);border:1.5px solid var(--line);border-radius:10px;padding:6px 11px}
.card .act a:hover{border-color:var(--coral)}
.card .act a.main{background:var(--coral);border-color:var(--coral);color:#fff}
.card .act .muted{color:var(--grey);font-size:12.5px}
@media (max-width:900px){
  .card{grid-template-columns:1fr;padding:16px 18px}
  .card .side{flex-direction:row;flex-wrap:wrap;align-items:center}
  .card .act{flex-direction:row;flex-wrap:wrap}
}
.empty{display:none;padding:30px;text-align:center;color:var(--grey);background:#fff;border:1px dashed var(--line);border-radius:16px}

/* DOSSIERS */
.dgrid{display:grid;grid-template-columns:repeat(auto-fill,minmax(min(340px,100%),1fr));gap:18px}
.dos{background:var(--ink);color:#fff;border-radius:20px;padding:22px 24px}
.dos h3{font-family:var(--disp);font-weight:700;font-size:19px;margin-bottom:6px}
.dos .st{font-size:13px;color:var(--ice);margin-bottom:12px}
.dos .st b{color:var(--coral)}
.dos .tl{font-size:13.5px;color:var(--ice);margin-bottom:14px}
.dos a{display:inline-block;font-size:13.5px;font-weight:600;color:#fff;background:var(--ink2);border-radius:10px;padding:7px 12px;margin:0 6px 6px 0;text-decoration:none}
.dos a.hot{background:var(--coral)}
.dos button{font-family:var(--body);font-size:13.5px;font-weight:600;color:var(--ink);background:var(--ice);border:none;border-radius:10px;padding:7px 12px;cursor:pointer;margin:0 6px 6px 0}

/* REFERENCE */
.tbl{overflow-x:auto;background:#fff;border:1px solid var(--line);border-radius:16px;margin-top:14px;margin-bottom:26px}
table{border-collapse:collapse;width:100%;font-size:14px}
th,td{text-align:left;padding:10px 14px;border-bottom:1px solid var(--line);vertical-align:top}
th{background:var(--panel);font-weight:600;font-size:12px;color:var(--grey);letter-spacing:.04em}
tr:last-child td{border-bottom:none}
td code{font-size:12.5px}
h3.ref{font-family:var(--disp);font-weight:500;font-size:18px;margin-top:8px}
footer{background:var(--ink);color:var(--ice);padding:34px 0;font-size:14px}
footer a{color:#fff}
footer p{margin-bottom:8px;max-width:920px}
</style>
</head>
<body>

<header class="hero">
  <div class="wrap">
    <div class="crumbs"><a href="../../index.html">Мастерская</a> · Архив заданий</div>
    <div class="eyebrow">ЭФ СПбГУ · задания для групп и потоков</div>
    <h1>Архив <span class="accent">заданий</span></h1>
    <p class="sub">Все задания мастерской в одном месте: конкретные, параметрические (индивидуальный вариант из пула)
      и эстафетные, которые продолжают накопленное досье. У каждого задания — тип, проверяемые навыки, результат и критерии.</p>
    <div class="stat-row" id="stats"></div>
  </div>
</header>

<nav class="nav"><div class="wrap">
  <div class="nav-links">
    <a href="#how">Как устроено</a><a href="#archive">Архив</a><a href="#dossiers">Досье</a>
    <a href="#reference">Типы · навыки · механики</a>
  </div>
  <div class="controls">
    <div class="chips" id="kinds"></div>
    <select id="f-type" aria-label="Тип задания"></select>
    <select id="f-skill" aria-label="Навык"></select>
    <select id="f-scale" aria-label="Масштаб"></select>
    <select id="f-dossier" aria-label="Досье"></select>
    <div class="search"><input id="q" type="search" placeholder="Поиск по заданиям…" aria-label="Поиск"></div>
    <button class="reset" id="reset">Сбросить</button>
  </div>
</div></nav>

<section id="how">
  <div class="wrap">
    <div class="eyebrow">01 · Как устроено</div>
    <h2>Три рода заданий</h2>
    <p class="lead">Род определяет, откуда берётся формулировка. Модель слоя заданий — в
      <a href="__GH__README.md">assignments/README.md</a>.</p>
    <div class="kinds">
      <div class="kind fixed"><h3>Конкретное</h3><p>Один текст выдаётся многим как есть; результаты сравнимы.</p>
        <div class="ex">Пример: «Red Bull Stratos как хлопушка»</div></div>
      <div class="kind param"><h3>Параметрическое</h3><p>Шаблон + вариант из пула каталога дисциплины → индивидуальное задание. В группе варианты не повторяются.</p>
        <div class="ex">Пример: «Компания {company} по трём укладам»</div></div>
      <div class="kind relay"><h3>Эстафетное</h3><p>Задание продолжает досье: следующий участник получает редакцию по текущему состоянию накопленного.</p>
        <div class="ex">Пример: досье Red Bull — модель → оппонирование → ставка</div></div>
    </div>
    <ol class="steps4">
      <li><b>Выбрать</b>Найдите задание в архиве по навыку, типу или досье.</li>
      <li><b>Получить выдачу</b>Преподаватель выдаёт задание или вы бронируете вариант; выдача фиксируется в журнале.</li>
      <li><b>Выполнить</b>По карточке задания: логика выполнения, результат, критерии.</li>
      <li><b>Сдать PR</b>Результат — Pull request в досье или в папку трека. Принятая работа обновляет досье.</li>
    </ol>
  </div>
</section>

<section id="archive" class="alt">
  <div class="wrap">
    <div class="eyebrow">02 · Архив</div>
    <h2>Задания <span class="cnt" id="c-archive"></span></h2>
    <p class="lead">Источник правды — <a href="__GH__catalog/templates.csv">catalog/templates.csv</a>.
      Фильтры сверху; ссылкой с фильтром можно поделиться — он сохраняется в адресе страницы.</p>
    <div class="list" id="g-archive"></div>
    <div class="empty" id="empty">Ничего не найдено. Измените фильтры или <button class="reset" onclick="resetAll()">сбросьте их</button>.</div>
  </div>
</section>

<section id="dossiers">
  <div class="wrap">
    <div class="eyebrow">03 · Накопительные досье</div>
    <h2>Досье</h2>
    <p class="lead">Досье — живой объект (компания, отрасль, технология), над которым работают сменяющие друг друга участники.
      От стадии досье зависит, какое задание выдаётся. Правила — <a href="__GH__dossiers/README.md">dossiers/README.md</a>.</p>
    <div class="dgrid" id="g-dossiers"></div>
  </div>
</section>

<section id="reference" class="alt">
  <div class="wrap">
    <div class="eyebrow">04 · Справочники</div>
    <h2>Типы, навыки, механики</h2>
    <p class="lead">Из чего собирается задание. Файлы — в <a href="__GH__catalog/README.md">catalog/</a>.</p>
    <h3 class="ref">Проверяемые навыки</h3>
    <div class="tbl"><table><thead><tr><th>Навык</th><th>Что это</th><th>Что должно быть видно в результате</th><th>Профильная роль</th></tr></thead><tbody id="t-skills"></tbody></table></div>
    <h3 class="ref">Типы заданий</h3>
    <div class="tbl"><table><thead><tr><th>Тип</th><th>Форма результата</th><th>Что это</th><th>Масштаб</th><th>Срок</th></tr></thead><tbody id="t-types"></tbody></table></div>
    <h3 class="ref">Механики</h3>
    <div class="tbl"><table><thead><tr><th>Механика</th><th>Как работает</th><th>Когда применять</th></tr></thead><tbody id="t-mech"></tbody></table></div>
  </div>
</section>

<footer>
  <div class="wrap">
    <p><b>Как пополнить архив.</b> Добавьте строку в <a href="__GH__catalog/templates.csv">templates.csv</a>, при необходимости карточку по
      <a href="__GH__templates/_card-template.md">шаблону</a>, и пересоберите страницу:
      <code>python assignments/site/build.py</code>. Изменения — через Pull request.</p>
    <p>Выдачи — по никам и <code>team_id</code>, без ФИО; оценки здесь не хранятся. Собрано: __GEN_DATE__.</p>
    <p><a href="../../index.html">← Дашборд мастерской</a> · <a href="../../disciplines/technologies-econ-fin/site/course.html">Курс дисциплины</a></p>
  </div>
</footer>

<script>
const DATA = __DATA_JSON__;
const esc = s => String(s ?? "").replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const KIND = {fixed:"Конкретное", param:"Параметрическое", relay:"Эстафетное"};
const TY = Object.fromEntries(DATA.types.map(t => [t.type_id, t]));
const SK = Object.fromEntries(DATA.skills.map(s => [s.skill_id, s]));
const MX = Object.fromEntries(DATA.mechanics.map(m => [m.mechanic_id, m]));
const DOS = Object.fromEntries(DATA.dossiers.map(d => [d.dossier_id, d]));
const T = DATA.templates;

// stats
const st = [
  [T.length, "заданий в архиве"],
  [T.filter(t => !t.dossier_id).length, "общих шаблонов"],
  [T.filter(t => t.dossier_id).length, "заданий досье"],
  [DATA.skills.length, "проверяемых навыков"],
  [DATA.dossiers.length, "досье"],
  [DATA.issuesTotal, "выдач"],
];
document.getElementById("stats").innerHTML = st.map(([n, l]) => `<div class="stat"><b>${n}</b><span>${l}</span></div>`).join("");

// controls
const F = {kind:"", type:"", skill:"", scale:"", dossier:"", q:""};
document.getElementById("kinds").innerHTML =
  [["", "Все"], ...Object.entries(KIND)].map(([k, l]) => `<button class="chip" data-kind="${k}">${l}</button>`).join("");
function fill(id, label, opts){
  document.getElementById(id).innerHTML = `<option value="">${label}</option>` + opts.map(([v, l]) => `<option value="${esc(v)}">${esc(l)}</option>`).join("");
}
fill("f-type", "Все типы", DATA.types.map(t => [t.type_id, t.title]));
fill("f-skill", "Все навыки", DATA.skills.map(s => [s.skill_id, s.title]));
fill("f-scale", "Любой масштаб", [["индивид", "Индивидуально"], ["команда", "Команда"]]);
fill("f-dossier", "Все задания", [["none", "Без досье (общие шаблоны)"], ...DATA.dossiers.map(d => [d.dossier_id, "Досье: " + d.object])]);

// cards
function card(t){
  const skills = t.skill_ids.map(s => `<span class="sk">${esc(SK[s] ? SK[s].title : s)}</span>`).join("");
  const mech = t.mechanic_ids.map(m => MX[m] ? MX[m].title : m).join(" · ");
  const d = DOS[t.dossier_id];
  const sep = '<span class="sep">|</span>';
  const facts = [`<b>Масштаб:</b> ${esc(t.scale.join(" / "))}`];
  if (t.duration) facts.push(`<b>Срок:</b> ${esc(t.duration)}`);
  if (mech) facts.push(`<b>Механика:</b> ${esc(mech)}`);
  const extra = [];
  if (t.parameters) extra.push(`<b>Варианты:</b> ${esc(t.parameters)}`);
  if (t.dossier_id) extra.push(`<b>Досье:</b> ${esc(d ? d.object : t.dossier_id)}` + (t.entry_stage.length ? `, стадия: ${esc(t.entry_stage.join(", "))}` : ""));
  else if (t.entry_stage.length) extra.push(`<b>Стадия досье:</b> ${esc(t.entry_stage.join(", "))}`);
  if (t.parent_template) extra.push(`<b>Шаблон:</b> <a href="#t-${esc(t.parent_template)}" onclick="showOne('${esc(t.parent_template)}')">${esc(t.parent_template)}</a>`);
  const links = [];
  if (t.card_url) links.push(`<a class="main" href="${t.card_url}">Карточка задания →</a>`);
  if (t.case_page) links.push(`<a href="${t.case_page}">Кейс курса</a>`);
  if (d) links.push(`<a href="${d.url}">Досье</a>`);
  if (t.issued) links.push(`<span class="muted">выдано: ${t.issued}</span>`);
  if (!t.card_url) links.push(`<span class="muted">описание — в этой строке архива</span>`);
  const text = [t.template_id, t.title, t.brief, t.deliverable, t.acceptance, t.parameters, mech,
    TY[t.type_id] ? TY[t.type_id].title : "", t.skill_ids.map(s => SK[s] ? SK[s].title : "").join(" ")].join(" ").toLowerCase();
  return `<article class="card" id="t-${esc(t.template_id)}" data-kind="${esc(t.kind)}" data-text="${esc(text)}">
    <div class="side"><span class="cid">${esc(t.template_id)}</span>
      <span class="badge ${esc(t.kind)}">${KIND[t.kind] || esc(t.kind)}</span>
      ${t.status === "активно" ? '<span class="badge active">активно</span>' : `<span class="badge">${esc(t.status)}</span>`}
      <span class="ty">${esc(TY[t.type_id] ? TY[t.type_id].title : t.type_id)}</span></div>
    <div class="body">
      <h4>${esc(t.title)}</h4>
      <p class="brief">${esc(t.brief)}</p>
      <div class="facts">${facts.join(sep)}</div>
      ${extra.length ? `<div class="facts">${extra.join(sep)}</div>` : ""}
      <div>${skills}</div>
      <details><summary>Результат и критерии</summary>
        <p><b>Что сдаётся:</b> ${esc(t.deliverable)}</p><p><b>Критерии приёмки:</b> ${esc(t.acceptance)}</p>
        ${t.related_questions.length ? `<p><b>Вопросы банка:</b> ${esc(t.related_questions.join(", "))}</p>` : ""}</details>
    </div>
    <div class="act">${links.join("")}</div></article>`;
}
document.getElementById("g-archive").innerHTML = T.map(card).join("");

function match(t){
  if (F.kind && t.kind !== F.kind) return false;
  if (F.type && t.type_id !== F.type) return false;
  if (F.skill && !t.skill_ids.includes(F.skill)) return false;
  if (F.scale && !t.scale.includes(F.scale)) return false;
  if (F.dossier === "none" && t.dossier_id) return false;
  if (F.dossier && F.dossier !== "none" && t.dossier_id !== F.dossier) return false;
  return true;
}
function apply(){
  const q = F.q.trim().toLowerCase();
  let n = 0;
  T.forEach(t => {
    const el = document.getElementById("t-" + t.template_id);
    const ok = match(t) && (!q || el.dataset.text.includes(q));
    el.style.display = ok ? "" : "none";
    if (ok) n++;
  });
  document.getElementById("c-archive").textContent = n === T.length ? `${n}` : `${n} из ${T.length}`;
  document.getElementById("empty").style.display = n ? "none" : "block";
  document.querySelectorAll("#kinds .chip").forEach(c => c.classList.toggle("on", c.dataset.kind === F.kind));
  ["type", "skill", "scale", "dossier"].forEach(k => document.getElementById("f-" + k).value = F[k]);
  document.getElementById("q").value = F.q;
  const h = Object.entries(F).filter(([, v]) => v).map(([k, v]) => k + "=" + encodeURIComponent(v)).join("&");
  history.replaceState(null, "", h ? "#" + h : location.pathname);
}
function resetAll(){ Object.keys(F).forEach(k => F[k] = ""); apply(); }
function showOne(id){ resetAll(); F.q = id.toLowerCase(); apply(); }
document.getElementById("kinds").addEventListener("click", e => { if (e.target.dataset.kind !== undefined) { F.kind = e.target.dataset.kind; apply(); } });
["type", "skill", "scale", "dossier"].forEach(k => document.getElementById("f-" + k).addEventListener("change", e => { F[k] = e.target.value; apply(); }));
document.getElementById("q").addEventListener("input", e => { F.q = e.target.value; apply(); });
document.getElementById("reset").addEventListener("click", resetAll);

// dossiers
document.getElementById("g-dossiers").innerHTML = DATA.dossiers.map(d => `<div class="dos">
  <h3>${esc(d.object || d.title)}</h3>
  <div class="st">Стадия: <b>${esc(d.stage)}</b> · версия ${esc(d.version)}${d.updated ? " · обновлено " + esc(d.updated) : ""}</div>
  <div class="tl">Задания досье: ${d.tasks.map(esc).join(", ")}</div>
  <button onclick="resetAll();F.dossier='${esc(d.dossier_id)}';apply();document.getElementById('archive').scrollIntoView()">Показать задания</button>
  ${d.case_page ? `<a class="hot" href="${d.case_page}">Кейс курса</a>` : ""}
  <a href="${d.url}">Досье</a><a href="${d.gaps_url}">Доска пробелов</a></div>`).join("");

// reference
document.getElementById("t-skills").innerHTML = DATA.skills.map(s =>
  `<tr><td><b>${esc(s.title)}</b><br><code>${esc(s.skill_id)}</code></td><td>${esc(s.what_it_is)}</td><td>${esc(s.evidence)}</td><td>${esc(s.related_role).replace(/;/g, ", ")}</td></tr>`).join("");
document.getElementById("t-types").innerHTML = DATA.types.map(t =>
  `<tr><td><b>${esc(t.title)}</b><br><code>${esc(t.type_id)}</code></td><td>${esc(t.result_form)}</td><td>${esc(t.description)}</td><td>${esc(t.typical_scale).replace(/;/g, ", ")}</td><td>${esc(t.typical_duration)}</td></tr>`).join("");
document.getElementById("t-mech").innerHTML = DATA.mechanics.map(m =>
  `<tr><td><b>${esc(m.title)}</b><br><code>${esc(m.mechanic_id)}</code></td><td>${esc(m.how)}</td><td>${esc(m.when_to_use)}</td></tr>`).join("");

// фильтр из адреса: #kind=relay&dossier=red-bull
new URLSearchParams(location.hash.slice(1)).forEach((v, k) => { if (k in F) F[k] = v; });
apply();
</script>
</body>
</html>
"""

with open(OUT, "w", encoding="utf-8") as fh:
    fh.write(HTML.replace("__DATA_JSON__", DATA_JSON)
                 .replace("__GEN_DATE__", GEN_DATE)
                 .replace("__GH__", GH))
print("written", OUT, "templates:", len(templates), "dossiers:", len(dossiers), "issues:", len(issues))
