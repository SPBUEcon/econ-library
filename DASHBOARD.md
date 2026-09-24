# 🧭 Дашборд Мастерской «Технологии в экономике»

> Единая точка входа во всю активность мастерской: основные сущности, ссылки и базовые статусы.
> ЭФ СПбГУ · осень 2026.
>
> **Красивая витрина (HTML):** [`program/site/dashboard.html`](program/site/dashboard.html).
> **Обновлено:** 2026-09-24.
>
> **Правило актуализации:** дашборд — сводка-дайджест, а не первоисточник. При расхождении прав
> первоисточник (карточка воркстрима / [доска](workstreams/board.md) / [реестр](registry/README.md)).
> Правки — через Pull request.

## Карта разделов

1. [Обзор и статусы](#1-обзор-и-статусы) · 2. [Ключевые ресурсы и сервисы](#2-ключевые-ресурсы-и-сервисы) ·
3. [Воркстримы](#3-воркстримы) · 4. [Партнёры](#4-партнёры) ·
5. [Дисциплины и учебные материалы](#5-дисциплины-и-учебные-материалы) · 6. [Треки: группы × семестры](#6-треки-группы--семестры)

---

## 1. Обзор и статусы

Не курс, а **мастерская**: команды в воркстримах собирают живые модели бизнеса, рынка и территории
вместе с реальными партнёрами. **Воркстрим** — единица управления (живёт дольше семестра);
**семестр = один ход**, размеченный гейтами **G0→G5**.

**Текущий ход — осень 2026 (`2026-fall`).** Первое занятие 17.09.2026 (G0), сборка команд 24.09 (G1).

| Гейт | Дата (Экономика, 3 к., четверги) | Что происходит |
|---|---|---|
| G0 — Рамка | 17.09.2026 | Вход в ландшафт, сборка воркстримов, суперзадачи и ставки |
| G1 — Команда | 24.09.2026 | Формирование команд, роли, наследство, методология |
| → G2 | 01.10.2026 | Постановка задачи, данные, архитектура модели |
| G2 — Архитектура | 08.10.2026 | Защита концепции живой модели |
| G3 — Поле | 15.10.2026 | Проверка модели реальной средой |
| G4 — Результат / демо | 22.10.2026 | Промежуточная защита проектов |
| Событие | 12–13.11.2026 | Хайпарк.Форум (воркстрим №6) |

> Курс ИСЭ (Бизнес-информатика, 4 к.) идёт параллельно (старт 18.09.2026), даты у команд свои.

**Контакты и роли.** Мастер — Д. Хан. Партнёры-связные — в разделе [Партнёры](#4-партнёры)
(один связной на партнёра). Роли команды/воркстрима/партнёра — [`roles/README.md`](roles/README.md).

**Базовые документы:** [концепт](program/concept.md) · [модель управления](program/governance.md) ·
[гейты G0–G5](program/gates.md) · [календарь](program/calendar.md) ·
[открытые вопросы](program/open-questions.md) · [как включиться](guides/how-to-join.md).

---

## 2. Ключевые ресурсы и сервисы

Выложенные страницы (работают по `file://` без сервера), каталоги и репозиторий.

| Ресурс | Что | Тип | Ссылка |
|---|---|---|---|
| Дашборд (HTML) | Эта сводка в виде витрины | Витрина | [`program/site/dashboard.html`](program/site/dashboard.html) |
| Витрина воркстримов | Наглядный каталог воркстримов для студентов | Витрина | [`program/site/workstreams_board.html`](program/site/workstreams_board.html) |
| Архитектура воркстримов | Как устроены слои и гейты | Витрина | [`program/site/workstreams_architecture.html`](program/site/workstreams_architecture.html) |
| Лендинг курса | Вводная страница мастерской | Витрина | [`program/site/landing_tech_econ.html`](program/site/landing_tech_econ.html) |
| Участники и доступы | Одностраничник по участию и доступам | Витрина | [`program/site/participants-and-access-onepager.html`](program/site/participants-and-access-onepager.html) |
| Курс дисциплины (HTML) | Темы, концепты, методологии, кейсы, вопросы + поиск | Приложение | [`disciplines/technologies-econ-fin/site/course.html`](disciplines/technologies-econ-fin/site/course.html) |
| Каталог дисциплины (CSV) | «Источник правды» контента дисциплины | Каталог | [`disciplines/technologies-econ-fin/catalog/`](disciplines/technologies-econ-fin/catalog/) |
| Репозиторий `econ-library` | Среда управления мастерской (этот репозиторий) | Репо | [`README.md`](README.md) |

> HTML-витрины собираются вручную / скриптом и держатся в синхроне с markdown-первоисточниками.
> Курс дисциплины пересобирается из каталога: `python disciplines/technologies-econ-fin/site/build.py`.

**Публичные ссылки (GitHub Pages).** Витрины доступны публично:

- 🧭 **Дашборд (главная)** — `https://spbuecon.github.io/econ-library/`
- Витрина воркстримов — `https://spbuecon.github.io/econ-library/program/site/workstreams_board.html`
- Курс дисциплины — `https://spbuecon.github.io/econ-library/disciplines/technologies-econ-fin/site/course.html`

> Дашборд — это корневой `index.html`; `program/site/dashboard.html` оставлен редиректом на главную.

> Markdown-хаб публичен и без Pages — на github.com: этот файл
> [`DASHBOARD.md`](https://github.com/SPBUEcon/econ-library/blob/main/DASHBOARD.md). Ссылки витрин на
> `.md`/папки ведут на github.com (Pages их не рендерит).

---

## 3. Воркстримы

Дайджест [доски «воркстрим × гейт»](workstreams/board.md). Полная карта — [`workstreams/README.md`](workstreams/README.md).

**Оперативные и сквозные (вход открыт):**

| # | Воркстрим | Уровень | Гейт | Партнёр / куратор | Статус | Папка |
|---|---|---|---|---|---|---|
| 1 | Страхование | A · семестр | G0→G4 | Ингосстрах | G0 — рамка | [`insurance/`](workstreams/insurance/) |
| 2 | Геоаналитика спортинфраструктуры | A · семестр | G0→G3 | Спорткомитет СПб / Геоинтеллект | G0 — рамка (hot) | [`sport-geo/`](workstreams/sport-geo/) |
| 3 | Вовлечение и коммуникация в спорте | A · семестр | G0→G3 | Спорткомитет СПб | G0 — рамка (hot) | [`sport-engagement/`](workstreams/sport-engagement/) |
| 4 | Фиджитал-спорт | A · семестр | G0→G2–3 | Федерация фиджитал-спорта СПб | G0 — рамка | [`phygital-sport/`](workstreams/phygital-sport/) |
| 5 | ИИ, цифровые двойники | Сквозной | сквозной | ИИтех (veai) | G0 — рамка | [`ai-environment/`](workstreams/ai-environment/) |
| 6 | Технологии и производство / венчур | A/B · семестр→год | G0→G1 | ИТМО Хайпарк | G0 — рамка | [`venture-tech/`](workstreams/venture-tech/) |
| 7 | Экология — Биеннале карт | Событие | событие | Геоинтеллект | Событие · рамка | [`cartography-biennale/`](workstreams/cartography-biennale/) |
| 13 | Среда управления | Сквозной · зонтик | G1→G3 | Мастерская (Хан) / В. В. Иванова | Активный | [`management-environment/`](workstreams/management-environment/) |

**Флагманы и переговоры (вход фрагментами):**

| # | Воркстрим | Уровень | Гейт | Куратор | Статус | Где |
|---|---|---|---|---|---|---|
| 8 | Кибер-фиджитал арена | B · флагман | G0–G2 | М. Мастин (Хайпарк) | Идея | [`flagships.md`](workstreams/flagships.md) |
| 9 | Международный технологический центр | B · флагман | G0–G2 | М. Мастин, И. Артемова | Идея | [`flagships.md`](workstreams/flagships.md) |
| 10 | Сеть фиджитал дайвинг-центров | B · флагман | G0–G2 | А. Спелов (Федерация) | Идея | [`flagships.md`](workstreams/flagships.md) |
| 11 | Новый интеллектуальный центр | B · зонтик | G0 | Хан | Идея | [`flagships.md`](workstreams/flagships.md) |
| 12 | Аскона (прото) | Прото | → G0 | АсконаLive / Д. Хан | Прото · в переговорах | [`askona-live/`](workstreams/askona-live/) |

> **Итого:** воркстримов — 12 (+ инфраструктурный №13); флагманов (B) — 4.
> Легенда гейтов и статусов — на [доске](workstreams/board.md) и в [гейтах](program/gates.md).

---

## 4. Партнёры

Партнёр — носитель суперзадачи с реальной ставкой. Реестр — [`partners/README.md`](partners/README.md);
вузы-партнёры — [`partners/universities.md`](partners/universities.md).

| Партнёр | Роль | Воркстрим(ы) | Связной |
|---|---|---|---|
| Ингосстрах | Владелец + Эксперт | [Страхование](workstreams/insurance/) | Г. Владельщикова |
| Спорткомитет СПб | Владелец | [Геоаналитика](workstreams/sport-geo/), [Вовлечение](workstreams/sport-engagement/) | А. Шантырь, И. Сологуб |
| Геоинтеллект | Шерпа-технолог · Эксперт | [Геоаналитика](workstreams/sport-geo/), [Биеннале карт](workstreams/cartography-biennale/) | Д. Структов |
| Федерация фиджитал-спорта СПб | Владелец + Эксперт | [Фиджитал-спорт](workstreams/phygital-sport/), флагман дайвинг-центров | А. Спелов |
| ИИтех (veai) | Эксперт (среда) | [ИИ / цифровые двойники](workstreams/ai-environment/) | М. Костицин |
| ИТМО Хайпарк | Эксперт + Владелец флагмана | [Венчур](workstreams/venture-tech/), флагманы | М. Мастин |
| Ирен Артемова | Владелец флагмана | [Международный техноцентр](workstreams/flagships.md) | — |
| АсконаLive | уточнить (в переговорах) | [Аскона (прото)](workstreams/askona-live/) | Н. Мандавиа, А. Ларионов |

Папки партнёров с постоянным потоком работы: [`ingosstrakh/`](partners/ingosstrakh/),
[`komsport-spb/`](partners/komsport-spb/).

---

## 5. Дисциплины и учебные материалы

Кросс-семестровые базы знаний дисциплин — [`disciplines/README.md`](disciplines/README.md).
Материалы по курсам/семестрам вуза — [`courses/README.md`](courses/README.md).

**[Технологии (информационные системы в экономике и финансах)](disciplines/technologies-econ-fin/README.md)** — ведёт Д. Хан.
Четыре блока: постинформационный переход · технологический ландшафт · ИИ и модели бизнеса · модели управления.

Каталог (CSV — «источник правды», [`catalog/`](disciplines/technologies-econ-fin/catalog/)):

| Что | Строк | Файл |
|---|---|---|
| Темы / лекционные блоки | 28 | [`topics.csv`](disciplines/technologies-econ-fin/catalog/topics.csv) |
| **Банк вопросов студентам** (вопросы / билеты) | 24 | [`questions.csv`](disciplines/technologies-econ-fin/catalog/questions.csv) |
| Концепты и модели-фреймворки | 34 | [`concepts.csv`](disciplines/technologies-econ-fin/catalog/concepts.csv) |
| Методологии | 13 | [`methodologies.csv`](disciplines/technologies-econ-fin/catalog/methodologies.csv) |
| Модели бизнеса (кейсы компаний) | 13 | [`business-models.csv`](disciplines/technologies-econ-fin/catalog/business-models.csv) |
| Прикладные и инфраструктурные кейсы | 10 | [`cases.csv`](disciplines/technologies-econ-fin/catalog/cases.csv) |
| Технологии | 10 | [`technologies.csv`](disciplines/technologies-econ-fin/catalog/technologies.csv) |
| Матрица укладов по отраслям | 15 | [`industries.csv`](disciplines/technologies-econ-fin/catalog/industries.csv) |
| Источники (презентации) | 14 | [`sources.csv`](disciplines/technologies-econ-fin/catalog/sources.csv) |

**Курс в HTML** (фильтр по блокам + поиск): [`site/course.html`](disciplines/technologies-econ-fin/site/course.html).
**Опорные заметки:** [`notes/`](disciplines/technologies-econ-fin/notes/).

---

## 6. Треки: группы × семестры

Формальные академические треки — где и кому читается дисциплина. Полная модель и данные —
[`tracks/README.md`](tracks/README.md).

| Трек | Поток | Дисциплина | Питает воркстримы | Прогон |
|---|---|---|---|---|
| [`econ-3`](tracks/econ-3/README.md) | Экономика, 3 курс (неск. групп) | Технологии (ИСЭиФ) | [`insurance`](workstreams/insurance/), [`phygital-sport`](workstreams/phygital-sport/) | [осень 2026](tracks/econ-3/2026-fall/README.md) — идёт |
| [`bi-4`](tracks/bi-4/README.md) | Бизнес-информатика (ИСЭ), 4 курс (2 группы) | Технологии (ИСЭиФ) | [`sport-geo`](workstreams/sport-geo/), [`sport-engagement`](workstreams/sport-engagement/) | [осень 2026](tracks/bi-4/2026-fall/README.md) — идёт |

В прогоне: план и контент проведённых занятий (`sessions.md`), темы докладов (`talks.md`),
отчётность (`reports/`). Пофамильная посещаемость/оценки — в вузовской ведомости, не здесь
(приватность, [`registry/README.md`](registry/README.md)).

**Рабочий контур (кто в каких командах/ролях):** реестр — [`registry/README.md`](registry/README.md)
(проект структуры, согласуется к G1 24.09.2026; реальных записей пока нет).
