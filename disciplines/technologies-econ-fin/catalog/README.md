# Каталог дисциплины — исходные данные

Это **исходные данные (CSV)**, по которым группируется контент дисциплины: темы, концепты,
методологии, модели бизнеса, кейсы, отрасли, вопросы. Каталог — «источник правды»; лекции, семинары
и задания собираются из него как представления (тот же принцип, что у [`../../../registry/`](../../../registry/README.md)).

Формат — как во всём репозитории ([`../../../rules/data-collection.md`](../../../rules/data-collection.md)):
CSV, UTF-8, разделитель — запятая, первая строка — названия столбцов, значения с запятой — в двойных
кавычках. Списки внутри одной ячейки разделяются `;`.

> **Excel** может показать кириллицу кракозябрами при двойном клике. Открывайте через
> «Данные → Получить данные → Из текстового/CSV-файла», кодировка UTF-8.

## Сквозные ключи

- **`block`** — блок дисциплины (см. [`../README.md`](../README.md)): `transition` ·
  `landscape` · `ai-business` · `management`. Даёт группировку и сшивку с
  [`program/governance.md`](../../../program/governance.md).
- **`source_ids`** — ссылки на [`sources.csv`](sources.csv) (провенанс каждой строки).
- **`*_id`** — устойчивые идентификаторы; на них ссылаются другие файлы (`related_concepts`,
  `topic_id` и т.д.). При правках id не переиспользуются.

## Файлы и колонки

### `topics.csv` — темы / лекционные блоки
| Колонка | Что |
|---|---|
| `topic_id` | `t01`, `t02`, … |
| `block` | Блок дисциплины |
| `title` | Название темы |
| `summary` | Краткое содержание |
| `key_concepts` | Ключевые концепты (текст; см. `concepts.csv`) |
| `source_ids` | Источники (`sources.csv`) |

### `technologies.csv` — технологии, которые разбираются
| Колонка | Что |
|---|---|
| `tech_id` | `tech-ai`, `tech-quantum`, `tech-dlt`, … |
| `name` | Название технологии |
| `category` | Группа (Интеллект / Квантовые / Транзакции / Связь / …) |
| `block` | Блок дисциплины |
| `summary` | Суть и роль в курсе |
| `subtechnologies` | Субтехнологии (список через `;`) |
| `related_cases` | Ссылки на `cases.csv` |
| `source_ids` | Источники |

### `concepts.csv` — концепты и мыслительные модели-фреймворки
| Колонка | Что |
|---|---|
| `concept_id` | `c01`, … |
| `title` | Название концепта |
| `type` | `фреймворк` / `модель` / `принцип` / `схема` |
| `block`, `summary`, `source_ids` | Блок, суть, источники |

### `methodologies.csv` — методологии
| Колонка | Что |
|---|---|
| `method_id` | `m01`, … |
| `title`, `block`, `summary` | Название, блок, суть |
| `application` | Где и как применяется |
| `source_ids` | Источники |

### `business-models.csv` — кейсы компаний (модели бизнеса)
| Колонка | Что |
|---|---|
| `model_id` | `bm01`, … |
| `company`, `industry` | Компания, отрасль |
| `level` | Целевой уровень/переход (уклад) |
| `transition_summary` | Суть трансформации и «ключевого перехода» |
| `key_metrics` | Метрики **со слайдов** — вторичны, проверять по первоисточнику |
| `source_ids` | Источники |

### `cases.csv` — прикладные и инфраструктурные кейсы
| Колонка | Что |
|---|---|
| `case_id` | `ca01`, … |
| `title`, `domain`, `block`, `summary` | Название, домен, блок, суть |
| `key_metrics` | Метрики со слайдов (проверять) |
| `related_concepts` | Ссылки на `concepts.csv` |
| `source_ids` | Источники |

### `industries.csv` — матрица укладов по отраслям
| Колонка | Что |
|---|---|
| `industry_id` | `ind01`, … |
| `industry` | Отрасль |
| `industrial` / `postindustrial` / `post_ai` | Как отрасль выглядит в каждом укладе |
| `source_ids` | Источники |

### `questions.csv` — банк вопросов студентам
| Колонка | Что |
|---|---|
| `question_id` | `q01`, … |
| `block`, `topic_id` | Блок и тема (`topics.csv`) |
| `question` | Формулировка |
| `type` | `лекция` / `семинар` / `экзамен` |
| `level` | `базовый` / `продвинутый` |

### `sources.csv` — презентации-первоисточники (провенанс)
| Колонка | Что |
|---|---|
| `source_id` | `s-...` |
| `file` | Имя файла презентации |
| `title` | Заголовок дека |
| `date` | Дата версии (`ГГГГ-ММ-ДД`) |
| `slides` | Число слайдов |
| `blocks` | Какие блоки покрывает |
| `note` | Провенанс, особенности |

Оригиналы презентаций — **приватные деки Д. Хан**, в публичный репозиторий не копируются (личные,
персональные данные, ~320 МБ). В каталоге хранятся только структурированные извлечения (текст извлечён
2026-09-24, python-pptx). **Доступ к оригиналам — по запросу** у владельца дисциплины; локально их
держат в `source-private/` (в `.gitignore`). Подробнее — [`../README.md`](../README.md), раздел
«Провенанс и оговорки».

## Проверка целостности

```bash
python - <<'PY'
import csv, glob, os
base="disciplines/technologies-econ-fin/catalog"
d={os.path.splitext(os.path.basename(f))[0]: list(csv.DictReader(open(f,encoding="utf-8")))
   for f in glob.glob(base+"/*.csv")}
src={r["source_id"] for r in d["sources"]}
con={r["concept_id"] for r in d["concepts"]}
top={r["topic_id"] for r in d["topics"]}
cas={r["case_id"] for r in d["cases"]}
def chk(name,col,valid):
    for r in d[name]:
        for t in (r.get(col) or "").split(";"):
            t=t.strip()
            if t and t not in valid: print("BAD",name,col,t)
for n in ["topics","technologies","concepts","methodologies","business-models","cases","industries"]:
    chk(n,"source_ids",src)
chk("cases","related_concepts",con)
chk("technologies","related_cases",cas)
for r in d["questions"]:
    if r["topic_id"] and r["topic_id"] not in top: print("BAD questions topic_id",r["topic_id"])
print("done")
PY
```
