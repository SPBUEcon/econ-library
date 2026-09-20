# Сайт мастерской (статические страницы)

HTML-страницы мастерской «Технологии в экономике» (ЭФ СПбГУ). Статические файлы: открываются в
браузере, сборка не нужна.

| Файл | Что это |
|---|---|
| [`workstreams_board.html`](workstreams_board.html) | **Витрина воркстримов** — дашборд для студентов: все воркстримы, гейты G0–G5, статусы, «как включиться» |
| [`landing_tech_econ.html`](landing_tech_econ.html) | Лендинг курса — о мастерской, формате, воркстримах, партнёрстве |
| [`workstreams_architecture.html`](workstreams_architecture.html) | Схема архитектуры воркстрима |
| [`participants-and-access-onepager.html`](participants-and-access-onepager.html) | Одностраничник для встречи: участники, группы, роли и доступы (печать — A4 альбомная); полный текст — [`../participants-and-access.md`](../participants-and-access.md) |

## Как открыть витрину (дашборд)

> ⚠️ GitHub показывает `.html` как исходный код, а не как страницу. Чтобы увидеть витрину как
> сайт, используйте один из способов ниже.

### 1. GitHub Pages — постоянная ссылка (рекомендуется)

Настраивается один раз владельцем репозитория: `Settings → Pages → Source: Deploy from a branch
→ Branch: main, папка / (root) → Save`. Через ~1 минуту витрина доступна по адресу:

```
https://spbuecon.github.io/econ-library/program/site/workstreams_board.html
```

Внутренние ссылки витрины («Войти →», заявка на вход и т. д.) ведут на github.com, поэтому
работают и на Pages, и при локальном просмотре.

### 2. Markdown-доска — работает сразу, без настройки

Если Pages ещё не включён, тот же статус доступен в markdown-доске (рендерится прямо на GitHub):

```
https://github.com/SPBUEcon/econ-library/blob/main/workstreams/board.md
```

### 3. htmlpreview — быстрый просмотр без публикации

```
https://htmlpreview.github.io/?https://github.com/SPBUEcon/econ-library/blob/main/program/site/workstreams_board.html
```

Открывается сразу; внешние шрифты могут подгружаться медленнее.

### 4. Локально

Скачать / склонировать репозиторий и открыть файл в браузере (двойным кликом или через локальный
сервер, например `python -m http.server` из корня репозитория).

## Кто обновляет

Витрину и доску держит в актуальном состоянии воркстрим
[«Среда управления»](../../workstreams/management-environment/). Изменения — через Pull request.
Данные — из карточек воркстримов ([карта](../../workstreams/README.md)); при расхождении со
статусом воркстрима правьте карточку и витрину вместе.

## Связанное

- Карта воркстримов — [`../../workstreams/README.md`](../../workstreams/README.md).
- Доска «воркстрим × гейт» — [`../../workstreams/board.md`](../../workstreams/board.md).
- Как включиться в воркстрим — [`../../guides/how-to-join.md`](../../guides/how-to-join.md).
