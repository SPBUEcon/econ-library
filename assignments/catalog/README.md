# Каталог заданий — справочники и архив

Исходные данные слоя заданий (CSV). Формат как во всём репозитории
([`../../rules/data-collection.md`](../../rules/data-collection.md)): UTF-8, разделитель — запятая,
первая строка — названия столбцов, значения с запятой — в двойных кавычках, списки в ячейке — через `;`.
Модель слоя — [`../README.md`](../README.md).

## Сквозные ключи

- **`*_id`** — устойчивые идентификаторы, при правках не переиспользуются.
- **`discipline`** — папка дисциплины в [`../../disciplines/`](../../disciplines/README.md).
- **`block`** — блок дисциплины (`transition` · `landscape` · `ai-business` · `management`).
- Пулы параметров ссылаются на каталог дисциплины: `company ← business-models.csv`,
  `industry ← industries.csv`, `tech ← technologies.csv`.

## `types.csv` — типы заданий

| Колонка | Что |
|---|---|
| `type_id` | `ty-report`, `ty-app`, … |
| `title`, `description` | Название и суть |
| `result_form` | Форма результата короткого горизонта (governance § 1) |
| `typical_scale` | `индивид` / `команда` |
| `typical_duration` | Типичная длительность в занятиях |

## `skills.csv` — проверяемые навыки

| Колонка | Что |
|---|---|
| `skill_id` | `sk-search`, `sk-bet`, … |
| `title`, `what_it_is` | Название и суть навыка |
| `evidence` | Что должно быть видно в результате, чтобы навык засчитать |
| `related_role` | Роль команды ([`../../roles/README.md`](../../roles/README.md)), для которой навык профильный |

## `mechanics.csv` — механики

| Колонка | Что |
|---|---|
| `mechanic_id` | `mx-param`, `mx-relay`, … |
| `title`, `how` | Название и как работает |
| `when_to_use` | Когда применять |
| `skills` | Навыки, которые механика проверяет сама по себе |
| `governance_link` | Связь с разделом [`../../program/governance.md`](../../program/governance.md) |

## `templates.csv` — архив шаблонов

| Колонка | Что |
|---|---|
| `template_id` | `tpl01…` — общие шаблоны; `<досье>-NN` (`rb-01`) — задания, привязанные к досье |
| `title` | Название |
| `kind` | `fixed` (конкретное) · `param` (параметрическое) · `relay` (эстафетное) |
| `parent_template` | Общий шаблон, от которого наследуется задание досье |
| `type_id`, `mechanic_ids`, `skill_ids` | Ссылки на справочники |
| `discipline`, `block` | Дисциплина и блок |
| `scale`, `duration` | Масштаб и длительность |
| `parameters` | Пул параметров для `param` (откуда берутся варианты) |
| `dossier_id` | Досье для `relay` (папка в [`../dossiers/`](../dossiers/README.md)) |
| `entry_stage` | Стадия досье, на которой задание выдаётся (`зерно` · `каркас` · `модель` · `кейс` · `устарело` · `любая`) |
| `brief` | Формулировка задания |
| `deliverable` | Что сдаётся |
| `acceptance` | Критерии приёмки |
| `related_questions` | Вопросы из банка дисциплины (`questions.csv`) |
| `status` | `черновик` · `активно` · `архив` |
| `file` | Развёрнутый текст (если есть) |

## `issues.csv` — журнал выдач

| Колонка | Что |
|---|---|
| `issue_id` | `<semester_id>-<track>-NNN`, например `2026-fall-econ-3-001` |
| `template_id` | Шаблон |
| `semester_id`, `track`, `group` | Семестр, трек, номер учебной группы (не персональные данные) |
| `assignee` | Ник или `team_id` из [реестра](../../registry/README.md). **Без ФИО** |
| `params` | Разрешённые параметры: `company=bm07` |
| `dossier_version` | Версия досье на момент выдачи (`red-bull@v0`) |
| `issued`, `due` | Даты `ГГГГ-ММ-ДД` |
| `status` | `выдано` · `сдано` · `принято` · `доработка` · `снято` |
| `result_link` | Ссылка на PR или файл результата |
| `note` | Комментарий. **Оценки сюда не пишутся** |

## `bets.csv` — реестр ставок

| Колонка | Что |
|---|---|
| `bet_id` | `bet-NNN` |
| `issue_id`, `dossier_id` | Выдача и досье |
| `author` | Ник или `team_id` |
| `statement` | Что произойдёт |
| `check_criterion` | По какому признаку проверить |
| `confidence_pct` | Уверенность автора, 0–100 |
| `made`, `resolve_by` | Дата ставки и дата разрешения |
| `resolved_by` | Кто разрешил (ник) |
| `outcome` | `сбылось` · `не сбылось` · `частично` · `не проверяемо` |
| `resolution_link` | Источник исхода |

## Проверка целостности

```bash
python -c "import csv,glob; [print(f, [i for i,r in enumerate(rows) if len(r)!=len(rows[0])]) for f in glob.glob('assignments/**/*.csv', recursive=True) for rows in [list(csv.reader(open(f, encoding='utf-8')))]]"
```

Пустой список у каждого файла означает, что число колонок совпадает во всех строках.
