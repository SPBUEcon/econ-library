#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Генератор HTML-курса из CSV-каталога дисциплины.

Читает ../catalog/*.csv и собирает самодостаточную страницу course.html
(данные встроены в страницу как JSON — работает по file:// без сервера).

Запуск:  python build.py     (из папки site/)
"""
import csv, json, os, datetime

HERE = os.path.dirname(os.path.abspath(__file__))
CAT = os.path.normpath(os.path.join(HERE, "..", "catalog"))
OUT = os.path.join(HERE, "course.html")


def load(name):
    with open(os.path.join(CAT, name), encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def split(v):
    return [x.strip() for x in (v or "").split(";") if x.strip()]


data = {
    "topics": load("topics.csv"),
    "technologies": load("technologies.csv"),
    "concepts": load("concepts.csv"),
    "methodologies": load("methodologies.csv"),
    "businessModels": load("business-models.csv"),
    "cases": load("cases.csv"),
    "industries": load("industries.csv"),
    "questions": load("questions.csv"),
    "sources": load("sources.csv"),
}
# нормализуем списочные поля
for r in data["topics"]:
    r["source_ids"] = split(r["source_ids"])
for r in data["concepts"]:
    r["source_ids"] = split(r["source_ids"])
for r in data["methodologies"]:
    r["source_ids"] = split(r["source_ids"])
for r in data["businessModels"]:
    r["source_ids"] = split(r["source_ids"])
for r in data["cases"]:
    r["source_ids"] = split(r["source_ids"])
    r["related_concepts"] = split(r["related_concepts"])
for r in data["industries"]:
    r["source_ids"] = split(r["source_ids"])
for r in data["technologies"]:
    r["source_ids"] = split(r["source_ids"])
    r["subtechnologies"] = split(r["subtechnologies"])
    r["related_cases"] = split(r["related_cases"])

counts = {k: len(v) for k, v in data.items()}
DATA_JSON = json.dumps(data, ensure_ascii=False)
GEN_DATE = datetime.date.today().isoformat()

HTML = r"""<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Технологии и информационные системы в экономике и финансах</title>
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
section{padding:60px 0;scroll-margin-top:140px}
a{color:inherit}
.eyebrow{font-size:13px;letter-spacing:.14em;text-transform:uppercase;color:var(--coral);font-weight:600;margin-bottom:14px}
h2{font-family:var(--disp);font-weight:700;font-size:clamp(24px,3vw,36px);line-height:1.15;margin-bottom:12px}
h2 .cnt{font-family:var(--body);font-weight:500;font-size:16px;color:var(--grey);vertical-align:middle;margin-left:10px}
.lead{font-size:clamp(15px,1.6vw,18px);color:var(--grey);max-width:820px;margin-bottom:8px}

/* HERO */
.hero{background:var(--ink);color:#fff;padding:64px 0 56px}
.hero .eyebrow{color:var(--ice)}
.hero h1{font-family:var(--disp);font-weight:700;font-size:clamp(26px,4vw,46px);line-height:1.12;max-width:960px}
.hero h1 .accent{color:var(--coral)}
.hero .sub{margin-top:18px;font-size:clamp(15px,1.8vw,20px);color:var(--ice);max-width:820px}
.hero .stat-row{display:flex;flex-wrap:wrap;gap:10px;margin-top:32px}
.stat{background:var(--ink2);border-radius:14px;padding:12px 18px}
.stat b{font-family:var(--disp);font-weight:700;font-size:22px;color:#fff;display:block}
.stat span{font-size:12px;color:var(--ice);letter-spacing:.04em}

/* STICKY NAV */
.nav{position:sticky;top:0;z-index:50;background:rgba(250,251,254,.92);backdrop-filter:blur(8px);border-bottom:1px solid var(--line)}
.nav .wrap{display:flex;flex-direction:column;gap:10px;padding-top:12px;padding-bottom:12px}
.nav-links{display:flex;gap:6px;flex-wrap:wrap}
.nav-links a{font-size:13.5px;font-weight:600;color:var(--grey);text-decoration:none;padding:6px 11px;border-radius:9px}
.nav-links a:hover{background:var(--panel);color:var(--ink)}
.controls{display:flex;gap:10px;flex-wrap:wrap;align-items:center}
.chips{display:flex;gap:6px;flex-wrap:wrap}
.chip{font-size:12.5px;font-weight:600;border:1.5px solid var(--line);background:#fff;color:var(--grey);
  border-radius:999px;padding:6px 13px;cursor:pointer;transition:all .12s ease}
.chip:hover{border-color:var(--coral);color:var(--ink)}
.chip.on{background:var(--ink);color:#fff;border-color:var(--ink)}
.chip.on[data-block="transition"]{background:var(--coral);border-color:var(--coral)}
.chip.on[data-block="landscape"]{background:var(--blue);border-color:var(--blue)}
.chip.on[data-block="ai-business"]{background:var(--violet);border-color:var(--violet)}
.chip.on[data-block="management"]{background:var(--green);border-color:var(--green)}
.search{flex:1;min-width:200px;max-width:340px;position:relative}
.search input{width:100%;font-family:var(--body);font-size:14px;padding:9px 14px 9px 34px;border:1.5px solid var(--line);
  border-radius:11px;background:#fff;color:var(--ink)}
.search input:focus{outline:none;border-color:var(--coral)}
.search::before{content:"⌕";position:absolute;left:12px;top:7px;font-size:17px;color:var(--grey)}

/* BLOCK DOTS */
.bd{display:inline-block;width:9px;height:9px;border-radius:50%;vertical-align:middle;margin-right:6px}
.bd.transition{background:var(--coral)} .bd.landscape{background:var(--blue)}
.bd.ai-business{background:var(--violet)} .bd.management{background:var(--green)}
.btag{display:inline-block;font-size:11px;font-weight:600;border-radius:999px;padding:3px 10px;letter-spacing:.02em}
.btag.transition{background:#FDE7E3;color:#C43C2A} .btag.landscape{background:#E1ECFB;color:#2A5AA8}
.btag.ai-business{background:#EBE4FB;color:#5A3FB0} .btag.management{background:#DDF1EA;color:#1F7A59}

/* BLOCK CARDS */
.blocks{display:grid;grid-template-columns:repeat(4,1fr);gap:18px;margin-top:36px}
.block{background:#fff;border:1px solid var(--line);border-top:4px solid var(--grey);border-radius:18px;padding:24px 22px;
  cursor:pointer;transition:transform .15s ease,box-shadow .15s ease}
.block:hover{transform:translateY(-3px);box-shadow:0 14px 34px rgba(27,32,56,.10)}
.block[data-block="transition"]{border-top-color:var(--coral)}
.block[data-block="landscape"]{border-top-color:var(--blue)}
.block[data-block="ai-business"]{border-top-color:var(--violet)}
.block[data-block="management"]{border-top-color:var(--green)}
.block .n{font-family:var(--disp);font-weight:700;font-size:30px;color:var(--ice);line-height:.9}
.block h3{font-family:var(--disp);font-weight:500;font-size:17px;line-height:1.25;margin:12px 0 10px}
.block p{font-size:13.5px;color:var(--grey)}

/* GENERIC CARD GRID */
.grid{display:grid;grid-template-columns:repeat(3,1fr);gap:18px;margin-top:32px}
.grid.two{grid-template-columns:repeat(2,1fr)}
.card{background:#fff;border:1px solid var(--line);border-radius:16px;padding:20px 20px 16px;display:flex;flex-direction:column}
.card.hidden,.qitem.hidden,.irow.hidden,.block.dim{display:none}
.card .cid{font-size:11px;font-weight:600;color:var(--grey);letter-spacing:.06em;font-family:var(--disp)}
.card .top{display:flex;justify-content:space-between;align-items:center;gap:10px;margin-bottom:10px}
.card h4{font-family:var(--disp);font-weight:500;font-size:16px;line-height:1.28;margin-bottom:9px}
.card .type{font-size:11px;color:var(--grey);text-transform:uppercase;letter-spacing:.06em;margin-bottom:6px}
.card p{font-size:13.5px;color:var(--grey);margin-bottom:8px}
.card p.metric{font-size:12.5px;color:var(--ink);background:var(--panel);border-radius:9px;padding:8px 11px}
.card .foot{margin-top:auto;padding-top:11px;border-top:1px solid var(--line);display:flex;flex-wrap:wrap;gap:5px}
.src{font-size:10.5px;color:var(--grey);background:var(--panel);border-radius:6px;padding:2px 7px;cursor:help}
.kk{font-size:11.5px;color:var(--ink)}
.kk b{color:var(--coral);font-weight:600;text-transform:uppercase;letter-spacing:.05em;font-size:10.5px}
.subs{display:flex;flex-wrap:wrap;gap:5px;margin:4px 0 9px}
.subt{font-size:11px;color:var(--ink2);background:var(--panel);border:1px solid var(--line);border-radius:7px;padding:3px 8px}
.card.tech h4{font-size:17px}
.card.tech{border-top:3px solid var(--line)}
.card.tech[data-block="landscape"]{border-top-color:var(--blue)}
.card.tech[data-block="ai-business"]{border-top-color:var(--violet)}
.card.tech[data-block="transition"]{border-top-color:var(--coral)}
.card.tech[data-block="management"]{border-top-color:var(--green)}

/* INDUSTRIES TABLE */
.itable{margin-top:32px;border:1px solid var(--line);border-radius:16px;overflow:hidden;background:#fff}
.ihead,.irow{display:grid;grid-template-columns:1.1fr 2fr 2fr 2.2fr}
.ihead{background:var(--ink);color:#fff;font-size:12px;font-weight:600;letter-spacing:.04em}
.ihead>div{padding:12px 14px}
.irow{border-top:1px solid var(--line)}
.irow:nth-child(even){background:#FCFDFF}
.irow>div{padding:13px 14px;font-size:13px;border-left:1px solid var(--line)}
.irow>div:first-child{border-left:none;font-weight:600;color:var(--ink)}
.irow .c1{color:var(--grey)} .irow .c2{color:var(--grey)} .irow .c3{color:var(--ink)}
.ihead .h3c{color:#fff} .col3-accent{background:#FFF6F4}

/* QUESTIONS */
.qgrid{margin-top:28px;display:flex;flex-direction:column;gap:10px}
.qitem{background:#fff;border:1px solid var(--line);border-radius:13px;padding:15px 18px;display:flex;gap:14px;align-items:flex-start}
.qitem .qn{font-family:var(--disp);font-weight:700;font-size:13px;color:var(--ice);flex:none;width:34px}
.qitem .qtext{font-size:14.5px;color:var(--ink);flex:1}
.qitem .qmeta{display:flex;gap:6px;flex-wrap:wrap;margin-top:7px}
.pill{font-size:10.5px;font-weight:600;border-radius:999px;padding:2px 9px;background:var(--panel);color:var(--grey)}
.pill.ex{background:#FDE7E3;color:#C43C2A} .pill.sem{background:#E1ECFB;color:#2A5AA8} .pill.lec{background:#DDF1EA;color:#1F7A59}
.pill.adv{background:#EBE4FB;color:#5A3FB0}

/* HOW-TO */
.how{background:var(--panel)}
.how-grid{display:grid;grid-template-columns:repeat(2,1fr);gap:20px;margin-top:34px}
.how-card{background:#fff;border:1px solid var(--line);border-radius:16px;padding:24px}
.how-card .n{font-family:var(--disp);font-weight:700;font-size:13px;color:var(--coral);letter-spacing:.08em;margin-bottom:10px}
.how-card h3{font-family:var(--disp);font-weight:500;font-size:18px;margin-bottom:10px}
.how-card p{font-size:14px;color:var(--grey);margin-bottom:8px}
.how-card code{font-family:ui-monospace,Menlo,Consolas,monospace;font-size:12.5px;background:var(--panel);
  border:1px solid var(--line);border-radius:6px;padding:1px 6px;color:var(--ink2)}
.how-card ul{margin:6px 0 0 18px;font-size:14px;color:var(--grey)}
.how-card li{margin-bottom:5px}

/* SOURCES */
.srcs{margin-top:28px;display:grid;grid-template-columns:repeat(2,1fr);gap:12px}
.srcrow{background:#fff;border:1px solid var(--line);border-radius:12px;padding:14px 16px}
.srcrow .st{font-family:var(--disp);font-weight:500;font-size:14.5px;margin-bottom:5px}
.srcrow .sm{font-size:12px;color:var(--grey);display:flex;gap:12px;flex-wrap:wrap}
.srcrow .sm b{color:var(--coral);font-weight:600}

.empty{grid-column:1/-1;text-align:center;color:var(--grey);font-size:14px;padding:24px}
.note{font-size:13px;color:var(--grey);background:#FFF6F4;border:1px solid #FAD9D2;border-radius:12px;padding:14px 18px;margin-top:24px}
footer{background:var(--ink);color:var(--ice);padding:40px 0;font-size:13.5px}
footer a{color:#fff}

@media(max-width:900px){
  .blocks{grid-template-columns:repeat(2,1fr)} .grid,.grid.two{grid-template-columns:1fr}
  .how-grid,.srcs{grid-template-columns:1fr}
  .ihead,.irow{grid-template-columns:1fr}
  .ihead{display:none}
  .irow>div{border-left:none;border-top:1px solid var(--line)}
  .irow>div:first-child{border-top:none;font-size:15px}
  .irow>div::before{content:attr(data-l);display:block;font-size:10px;letter-spacing:.06em;text-transform:uppercase;color:var(--coral);font-weight:600;margin-bottom:3px}
  .irow>div:first-child::before{content:""}
}
</style>
</head>
<body>

<header class="hero">
  <div class="wrap">
    <div class="eyebrow">Мастерская «Технологии в экономике» · дисциплина</div>
    <h1>Технологии и <span class="accent">информационные системы</span> в экономике и финансах</h1>
    <p class="sub">Архитектура перспективных экономических моделей. Какое место технологии занимают в
    экономике. Индустриальная экономика считает, информационная анализирует, постинформационная —
    <b style="color:#fff">собирает</b>.</p>
    <div class="stat-row" id="stats"></div>
  </div>
</header>

<nav class="nav">
  <div class="wrap">
    <div class="nav-links">
      <a href="#how">Как работать</a>
      <a href="#blocks">Блоки</a>
      <a href="#topics">Темы</a>
      <a href="#technologies">Технологии</a>
      <a href="#concepts">Концепты</a>
      <a href="#methods">Методологии</a>
      <a href="#models">Модели бизнеса</a>
      <a href="#cases">Кейсы</a>
      <a href="#industries">Отрасли</a>
      <a href="#questions">Вопросы</a>
      <a href="#sources">Источники</a>
    </div>
    <div class="controls">
      <div class="chips" id="chips">
        <span class="chip on" data-block="all">Все блоки</span>
        <span class="chip" data-block="transition">Постинформационный переход</span>
        <span class="chip" data-block="landscape">Технологический ландшафт</span>
        <span class="chip" data-block="ai-business">ИИ и модели бизнеса</span>
        <span class="chip" data-block="management">Модели управления</span>
      </div>
      <div class="search"><input id="q" type="search" placeholder="Поиск по курсу…" autocomplete="off"></div>
    </div>
  </div>
</nav>

<section id="how" class="how">
  <div class="wrap">
    <div class="eyebrow">С чего начать</div>
    <h2>Как работать с каталогом</h2>
    <p class="lead">Каталог — «источник правды» курса (CSV-файлы в <code>catalog/</code>). Эта страница
    собрана из него автоматически. Всё размечено по 4 блокам; фильтр блоков и поиск вверху работают
    сразу по всем разделам.</p>
    <div class="how-grid">
      <div class="how-card"><div class="n">01 · СОБРАТЬ ЛЕКЦИЮ</div><h3>По блоку</h3>
        <p>Выберите блок наверху — страница покажет только его темы, концепты и методологии. В каталоге это
        фильтр по колонке <code>block</code> в <code>topics.csv</code>, <code>concepts.csv</code>, <code>methodologies.csv</code>.</p></div>
      <div class="how-card"><div class="n">02 · ПОДГОТОВИТЬ СЕМИНАР</div><h3>Кейс + концепты + вопросы</h3>
        <p>Возьмите кейс, связанные концепты (<code>related_concepts</code>) и вопросы того же блока из
        раздела «Вопросы». Модели бизнеса разбираются методом «трёх укладов».</p></div>
      <div class="how-card"><div class="n">03 · НАЙТИ ПЕРВОИСТОЧНИК</div><h3>По источнику</h3>
        <p>Бейджи <span class="src">s-…</span> на карточках — ссылки на презентации (<code>sources.csv</code>):
        наведите, чтобы увидеть название и дату дека. Цифры со слайдов — вторичны, проверяйте по первоисточнику.</p></div>
      <div class="how-card"><div class="n">04 · ДОПОЛНИТЬ КУРС</div><h3>Правка каталога</h3>
        <p>Добавьте строку в нужный CSV с новым <code>id</code>, проставьте <code>block</code> и
        <code>source_ids</code>, затем пересоберите страницу: <code>python site/build.py</code>.</p></div>
    </div>
  </div>
</section>

<section id="blocks">
  <div class="wrap">
    <div class="eyebrow">Структура</div>
    <h2>Четыре блока курса</h2>
    <p class="lead">Backbone дисциплины (по <b>program/governance.md</b>). Нажмите на блок, чтобы отфильтровать весь курс.</p>
    <div class="blocks" id="blocks-grid"></div>
  </div>
</section>

<section id="topics">
  <div class="wrap">
    <div class="eyebrow">Лекционные блоки</div>
    <h2>Темы <span class="cnt" id="c-topics"></span></h2>
    <div class="grid" id="g-topics"></div>
  </div>
</section>

<section id="technologies" style="background:var(--panel)">
  <div class="wrap">
    <div class="eyebrow">Что разбираем</div>
    <h2>Технологии <span class="cnt" id="c-technologies"></span></h2>
    <p class="lead">Ядро следующего уклада и смежные технологии, которые разбираются в курсе: искусственный
    интеллект, квантовые технологии, распределённые реестры (блокчейн) и другие. У каждой — субтехнологии
    и связанные кейсы.</p>
    <div class="grid" id="g-technologies"></div>
  </div>
</section>

<section id="concepts">
  <div class="wrap">
    <div class="eyebrow">Мыслительные инструменты</div>
    <h2>Концепты и модели-фреймворки <span class="cnt" id="c-concepts"></span></h2>
    <div class="grid" id="g-concepts"></div>
  </div>
</section>

<section id="methods">
  <div class="wrap">
    <div class="eyebrow">Как действовать</div>
    <h2>Методологии <span class="cnt" id="c-methods"></span></h2>
    <div class="grid two" id="g-methods"></div>
  </div>
</section>

<section id="models" style="background:var(--panel)">
  <div class="wrap">
    <div class="eyebrow">Разбор компаний</div>
    <h2>Модели бизнеса <span class="cnt" id="c-models"></span></h2>
    <p class="lead">Компании по трём укладам и «ключевому переходу». Метрики со слайдов — проверять по первоисточнику.</p>
    <div class="grid" id="g-models"></div>
  </div>
</section>

<section id="cases">
  <div class="wrap">
    <div class="eyebrow">Прикладное</div>
    <h2>Кейсы <span class="cnt" id="c-cases"></span></h2>
    <div class="grid" id="g-cases"></div>
  </div>
</section>

<section id="industries" style="background:var(--panel)">
  <div class="wrap">
    <div class="eyebrow">Тренажёр насмотренности</div>
    <h2>Матрица укладов по отраслям <span class="cnt" id="c-industries"></span></h2>
    <p class="lead">Как один и тот же переход выглядит в разных отраслях. Приём: взять отрасль, разложить по трём укладам, назвать следующий ход.</p>
    <div class="itable" id="t-industries"></div>
  </div>
</section>

<section id="questions">
  <div class="wrap">
    <div class="eyebrow">Спрашивается у студентов</div>
    <h2>Банк вопросов <span class="cnt" id="c-questions"></span></h2>
    <div class="qgrid" id="g-questions"></div>
  </div>
</section>

<section id="sources" style="background:var(--panel)">
  <div class="wrap">
    <div class="eyebrow">Провенанс</div>
    <h2>Источники <span class="cnt" id="c-sources"></span></h2>
    <p class="lead">Авторские презентации Д. Хан — первоисточник контента. Оригиналы приватны; в репозитории — структурированное извлечение.</p>
    <div class="srcs" id="g-sources"></div>
    <div class="note">Цифры (обороты, инвестиции, охваты, метрики проектов) взяты со слайдов и вторичны.
    Перед использованием в студенческих работах их нужно проверить по первоисточнику и оформить ссылку
    по правилам репозитория (<b>rules/sources-and-citation.md</b>).</div>
  </div>
</section>

<footer>
  <div class="wrap">
    Дисциплина «Технологии (ИС в экономике и финансах)» · Мастерская «Технологии в экономике», ЭФ СПбГУ.
    Страница собрана из каталога <b>disciplines/technologies-econ-fin/catalog/</b> — __GEN_DATE__.
    Правьте CSV и пересобирайте: <code>python site/build.py</code>.
  </div>
</footer>

<script>
const DATA = __DATA_JSON__;
const BLOCKS = {
  transition:{title:"Постинформационный переход", n:"01", desc:"Смена укладов; воронка·лейка·хлопушка; три уклада; матрица отраслей."},
  landscape:{title:"Технологический ландшафт", n:"02", desc:"Стек инфраструктуры; фронтирные технологии; кванты и DLT; оператор инфраструктуры."},
  "ai-business":{title:"ИИ и модели бизнеса", n:"03", desc:"ИИ и трансформация рынков; AI-native; кейсы компаний; стратегии генерации ценности."},
  management:{title:"Модели управления", n:"04", desc:"Главный архитектор; суперзадачи и суперкоманды; ролевая модель; powermap."}
};
const SRC = Object.fromEntries(DATA.sources.map(s=>[s.source_id, s]));
const CON = Object.fromEntries(DATA.concepts.map(c=>[c.concept_id, c]));
const CASE = Object.fromEntries(DATA.cases.map(c=>[c.case_id, c]));
let activeBlock="all", query="";

const esc = s => (s||"").replace(/[&<>"]/g,m=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[m]));
const btag = b => b?`<span class="btag ${b}"><span class="bd ${b}"></span>${BLOCKS[b]?BLOCKS[b].title:b}</span>`:"";
const srcBadges = ids => (ids||[]).map(id=>{
  const s=SRC[id]; const t=s?`${esc(s.title)} — ${s.date}`:id;
  return `<span class="src" title="${t}">${id}</span>`;
}).join("");

// stats
document.getElementById("stats").innerHTML = [
  ["topics","тем"],["technologies","технологий"],["concepts","концептов"],["methodologies","методологий"],
  ["businessModels","моделей бизнеса"],["cases","кейсов"],["questions","вопросов"]
].map(([k,l])=>`<div class="stat"><b>${DATA[k].length}</b><span>${l}</span></div>`).join("");

// blocks
document.getElementById("blocks-grid").innerHTML = Object.entries(BLOCKS).map(([k,b])=>
  `<div class="block" data-block="${k}" onclick="setBlock('${k}')"><div class="n">${b.n}</div>
   <h3>${b.title}</h3><p>${b.desc}</p></div>`).join("");

// topics
document.getElementById("g-topics").innerHTML = DATA.topics.map(t=>card(t.block,
  `${t.topic_id} ${t.title} ${t.summary} ${t.key_concepts}`,
  `<div class="top"><span class="cid">${t.topic_id}</span>${btag(t.block)}</div>
   <h4>${esc(t.title)}</h4><p>${esc(t.summary)}</p>
   ${t.key_concepts?`<p class="kk"><b>Ключевое:</b> ${esc(t.key_concepts)}</p>`:""}
   <div class="foot">${srcBadges(t.source_ids)}</div>`)).join("");

// technologies
document.getElementById("g-technologies").innerHTML = DATA.technologies.map(t=>{
  const subs=(t.subtechnologies||[]).map(s=>`<span class="subt">${esc(s)}</span>`).join("");
  const rc=(t.related_cases||[]).map(id=>{const c=CASE[id];return c?esc(c.title):id;}).join(" · ");
  return `<div class="card tech" data-block="${t.block||''}" data-text="${esc((t.tech_id+' '+t.name+' '+t.category+' '+t.summary+' '+(t.subtechnologies||[]).join(' ')).toLowerCase())}">
    <div class="top"><span class="cid">${esc(t.category)}</span>${btag(t.block)}</div>
    <h4>${esc(t.name)}</h4><p>${esc(t.summary)}</p>
    ${subs?`<div class="subs">${subs}</div>`:""}
    ${rc?`<p class="kk"><b>Кейсы:</b> ${rc}</p>`:""}
    <div class="foot">${srcBadges(t.source_ids)}</div></div>`;
}).join("");

// concepts
document.getElementById("g-concepts").innerHTML = DATA.concepts.map(c=>card(c.block,
  `${c.concept_id} ${c.title} ${c.summary} ${c.type}`,
  `<div class="top"><span class="cid">${c.concept_id}</span>${btag(c.block)}</div>
   <div class="type">${esc(c.type)}</div><h4>${esc(c.title)}</h4><p>${esc(c.summary)}</p>
   <div class="foot">${srcBadges(c.source_ids)}</div>`)).join("");

// methods
document.getElementById("g-methods").innerHTML = DATA.methodologies.map(m=>card(m.block,
  `${m.method_id} ${m.title} ${m.summary} ${m.application}`,
  `<div class="top"><span class="cid">${m.method_id}</span>${btag(m.block)}</div>
   <h4>${esc(m.title)}</h4><p>${esc(m.summary)}</p>
   ${m.application?`<p class="kk"><b>Применение:</b> ${esc(m.application)}</p>`:""}
   <div class="foot">${srcBadges(m.source_ids)}</div>`)).join("");

// business models
document.getElementById("g-models").innerHTML = DATA.businessModels.map(m=>card("ai-business",
  `${m.model_id} ${m.company} ${m.industry} ${m.transition_summary} ${m.key_metrics}`,
  `<div class="top"><span class="cid">${m.model_id}</span><span class="type">${esc(m.industry)}</span></div>
   <h4>${esc(m.company)}</h4><p class="kk"><b>Уровень:</b> ${esc(m.level)}</p>
   <p>${esc(m.transition_summary)}</p>
   ${m.key_metrics&&m.key_metrics!=="—"?`<p class="metric">${esc(m.key_metrics)}</p>`:""}
   <div class="foot">${srcBadges(m.source_ids)}</div>`)).join("");

// cases
document.getElementById("g-cases").innerHTML = DATA.cases.map(c=>{
  const rc=(c.related_concepts||[]).map(id=>CON[id]?esc(CON[id].title):id).join(" · ");
  return card(c.block, `${c.case_id} ${c.title} ${c.domain} ${c.summary} ${c.key_metrics}`,
  `<div class="top"><span class="cid">${c.case_id}</span>${btag(c.block)}</div>
   <div class="type">${esc(c.domain)}</div><h4>${esc(c.title)}</h4><p>${esc(c.summary)}</p>
   ${c.key_metrics?`<p class="metric">${esc(c.key_metrics)}</p>`:""}
   ${rc?`<p class="kk"><b>Концепты:</b> ${rc}</p>`:""}
   <div class="foot">${srcBadges(c.source_ids)}</div>`);
}).join("");

// industries
document.getElementById("t-industries").innerHTML =
  `<div class="ihead"><div>Отрасль</div><div>Индустриальный</div><div>Постиндустриальный</div><div class="h3c">Пост-ИИ</div></div>`+
  DATA.industries.map(i=>`<div class="irow" data-block="transition" data-text="${esc((i.industry+' '+i.industrial+' '+i.postindustrial+' '+i.post_ai).toLowerCase())}">
    <div>${esc(i.industry)}</div>
    <div class="c1" data-l="Индустриальный">${esc(i.industrial)}</div>
    <div class="c2" data-l="Постиндустриальный">${esc(i.postindustrial)}</div>
    <div class="c3 col3-accent" data-l="Пост-ИИ">${esc(i.post_ai)}</div></div>`).join("");

// questions
const QT={лекция:"lec",семинар:"sem",экзамен:"ex"};
document.getElementById("g-questions").innerHTML = DATA.questions.map(q=>{
  const t=`${q.question_id} ${q.question} ${q.type} ${q.level}`.toLowerCase();
  return `<div class="qitem" data-block="${q.block}" data-text="${esc(t)}">
    <div class="qn">${q.question_id.toUpperCase()}</div>
    <div class="qtext">${esc(q.question)}
      <div class="qmeta">${btag(q.block)}
        <span class="pill ${QT[q.type]||''}">${esc(q.type)}</span>
        <span class="pill ${q.level==='продвинутый'?'adv':''}">${esc(q.level)}</span>
        ${q.topic_id?`<span class="pill">${q.topic_id}</span>`:""}</div>
    </div></div>`;
}).join("");

// sources
document.getElementById("g-sources").innerHTML = DATA.sources.map(s=>
  `<div class="srcrow"><div class="st">${esc(s.title)}</div>
   <div class="sm"><span><b>${s.source_id}</b></span><span>${s.date}</span><span>${s.slides} слайдов</span>
   <span>${esc(s.blocks).replace(/;/g,', ')}</span></div></div>`).join("");

function card(block, text, inner){
  return `<div class="card" data-block="${block||''}" data-text="${esc(text.toLowerCase())}">${inner}</div>`;
}

// counts
function refreshCounts(){
  const map={topics:"c-topics",concepts:"c-concepts",methodologies:"c-methods",cases:"c-cases",questions:"c-questions",industries:"c-industries",sources:"c-sources"};
  document.getElementById("c-topics").textContent = vis("#g-topics .card");
  document.getElementById("c-technologies").textContent = vis("#g-technologies .card");
  document.getElementById("c-concepts").textContent = vis("#g-concepts .card");
  document.getElementById("c-methods").textContent = vis("#g-methods .card");
  document.getElementById("c-models").textContent = vis("#g-models .card");
  document.getElementById("c-cases").textContent = vis("#g-cases .card");
  document.getElementById("c-questions").textContent = vis("#g-questions .qitem");
  document.getElementById("c-industries").textContent = vis("#t-industries .irow");
  document.getElementById("c-sources").textContent = DATA.sources.length;
}
const vis = sel => "· "+document.querySelectorAll(sel+":not(.hidden)").length;

function apply(){
  const items=document.querySelectorAll(".card,.qitem,.irow");
  items.forEach(el=>{
    const b=el.getAttribute("data-block")||"";
    const txt=el.getAttribute("data-text")||"";
    const okB = activeBlock==="all" || b===activeBlock;
    const okQ = !query || txt.includes(query);
    el.classList.toggle("hidden", !(okB&&okQ));
  });
  // блоки: подсветить активный
  document.querySelectorAll(".block").forEach(el=>
    el.classList.toggle("dim", activeBlock!=="all" && el.getAttribute("data-block")!==activeBlock));
  // пустые секции
  document.querySelectorAll("section .grid, .qgrid").forEach(g=>{
    const has=g.querySelectorAll(".card:not(.hidden),.qitem:not(.hidden)").length;
    let e=g.querySelector(".empty");
    if(!has){ if(!e){e=document.createElement("div");e.className="empty";e.textContent="Ничего не найдено в этом блоке.";g.appendChild(e);} }
    else if(e){e.remove();}
  });
  refreshCounts();
}
function setBlock(b){
  activeBlock=(activeBlock===b)?"all":b;
  document.querySelectorAll(".chip").forEach(c=>c.classList.toggle("on", c.getAttribute("data-block")===activeBlock));
  if(activeBlock==="all") document.querySelector('.chip[data-block="all"]').classList.add("on");
  apply();
}
document.querySelectorAll(".chip").forEach(c=>c.addEventListener("click",()=>{
  const b=c.getAttribute("data-block"); activeBlock=b;
  document.querySelectorAll(".chip").forEach(x=>x.classList.toggle("on",x===c));
  apply();
}));
document.getElementById("q").addEventListener("input",e=>{query=e.target.value.trim().toLowerCase();apply();});
apply();
</script>
</body>
</html>"""

html = (HTML
        .replace("__DATA_JSON__", DATA_JSON)
        .replace("__GEN_DATE__", GEN_DATE))
with open(OUT, "w", encoding="utf-8") as fh:
    fh.write(html)
print("written", OUT, "counts:", counts)
