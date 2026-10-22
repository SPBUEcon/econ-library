# -*- coding: utf-8 -*-
"""Регистрация участника по одобренной заявке на вход.

Заявка приходит одним из двух путей, тело у них одинаковое (разделы «### Поле»): форма записи на
витрине воркстримов (program/site/workstreams_board.html, раздел «Записаться») или Issue Form
join-workstream.yml на GitHub.

Запускается workflow .github/workflows/join-registry.yml, когда шерпа или мастер ставит на заявку
метку approved. Скрипт:
1. разбирает тело issue (разделы «### Поле» формы);
2. проверяет, что одобривший — мастер, шерпа или владелец этого воркстрима по реестру
   (пока реестр пуст — владелец репозитория с правом admin);
3. дописывает строки в registry/participants.csv и registry/memberships.csv
   (колонки и словари — registry/README.md);
4. пишет текст Pull request и комментарий к заявке.

Строки только дописываются, существующие не меняются. Если человек уже есть в реестре (по нику),
новая строка в participants.csv не заводится.

Формат участия — по лестнице участия (stands/engagement.md) плюс стажировка и наставничество:
one-off, mini-track, team, internship, mentor. Роль обязательна только для team; для остальных
форматов пишется одна строка с пустой ролью (или по строке на роль, если роли выбраны). Команда
(team_id) подставляется только для team и только если у воркстрима в текущем семестре ровно одна
команда в статусе forming/active. В заявках без поля «Формат участия» (старая форма) формат — team.

Локальная проверка на примере (файлы реестра не трогаются):
    python registry/register-participant.py --body registry/examples/join-issue-body.txt \\
        --author ivanov --issue 1 --approver SPBUEcon --approver-permission admin --dry-run

Коды выхода: 0 — записано (или --dry-run); 2 — заявка не принята, причина в --comment-file.
"""
import argparse
import csv
import io
import re
import sys
from datetime import date
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[1]
REG = REPO / "registry"
WS = REPO / "workstreams"

PARTICIPANT_COLS = ["person_id", "github", "display_name", "org", "unit", "type", "status",
                    "first_semester", "note"]
MEMBERSHIP_COLS = ["membership_id", "person_id", "semester_id", "workstream_id", "team_id", "format", "role",
                   "profile", "date_from", "date_to", "exit_type", "sponsor_person_id", "entry", "note"]
# Формат участия: код → как называется в форме (лестница участия — stands/engagement.md).
FORMATS = {"one-off": "разовое задание на занятии", "mini-track": "мини-трек на 1–3 занятия",
           "team": "роль в команде на семестр", "internship": "стажировка у партнёра",
           "mentor": "наставник или эксперт"}
TEAM_ROLES = {"captain", "model-architect", "field-analyst", "tech-integrator", "partner-liaison"}
TYPES = {"student-spbu", "student-external", "teacher", "partner", "staff"}
APPROVER_ROLES_WS = {"sherpa", "workstream-owner"}
GITHUB_LOGIN = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9]|-(?=[A-Za-z0-9])){0,38}$")
CONTACT_LIKE = re.compile(r"@|https?://|t\.me/|\+?\d[\d\s()-]{6,}\d")
NO_RESPONSE = {"", "_no response_", "none"}

# Заголовки разделов формы (label в join-workstream.yml) → ключ.
FIELDS = {
    "Воркстрим": "workstream",
    "Формат участия": "format",
    "Желаемая роль": "role",
    "GitHub-ник участника": "github",
    "Кто вы": "type",
    "Вуз или организация": "org",
    "Направление, курс, группа": "unit",
}


class Refused(Exception):
    """Заявку нельзя внести автоматически; текст уходит комментарием в issue."""


# ---------------------------------------------------------------- разбор


def parse_body(body):
    """Тело Issue Form → {ключ: значение}. Форма рендерит поля как «### Label\\n\\nзначение»."""
    out, current, buf = {}, None, []
    for line in body.replace("\r\n", "\n").split("\n") + ["### "]:
        if line.startswith("### "):
            if current in FIELDS:
                out[FIELDS[current]] = "\n".join(buf).strip()
            current, buf = line[4:].strip(), []
        else:
            buf.append(line)
    return {k: ("" if v.strip().lower() in NO_RESPONSE else v) for k, v in out.items()}


def code_in_parens(text):
    return re.findall(r"\(([a-z][a-z-]*)\)", text)


def one_line(text, field):
    value = " ".join(text.split())
    if CONTACT_LIKE.search(value):
        raise Refused(f"В поле «{field}» похоже на контакт (email, ссылка, телефон). Репозиторий публичный — "
                      "уберите контакт из заявки и снова поставьте метку `approved`.")
    if len(value) > 100:
        raise Refused(f"Поле «{field}» длиннее 100 символов — сократите и снова поставьте метку `approved`.")
    return value


# ---------------------------------------------------------------- реестр


def read_csv(name, cols):
    path = REG / name
    with path.open(encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames != cols:
            raise SystemExit(f"registry/{name}: колонки {reader.fieldnames} не совпадают с ожидаемыми {cols}")
        return list(reader)


def append_csv(name, cols, rows):
    path = REG / name
    raw = path.read_bytes()
    eol = "\r\n" if b"\r\n" in raw else "\n"
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=cols, lineterminator=eol)
    writer.writerows(rows)
    prefix = "" if raw.endswith(b"\n") or not raw else eol
    with path.open("a", encoding="utf-8", newline="") as f:
        f.write(prefix + buf.getvalue())


def next_id(rows, key, prefix, width):
    nums = [int(r[key][len(prefix):]) for r in rows if re.fullmatch(prefix + r"\d+", r[key] or "")]
    return f"{prefix}{(max(nums) + 1 if nums else 1):0{width}d}"


def workstream_ids():
    ids = {d.name for d in WS.iterdir() if (d / "workstream.yml").exists() and not d.name.startswith("_")}
    flagships = WS / "flagships.yml"
    if flagships.exists():
        ids |= {e["id"] for e in yaml.safe_load(flagships.read_text(encoding="utf-8")) or [] if e.get("id")}
    return ids


def current_semester(today):
    rows = read_csv("semesters.csv", ["semester_id", "title", "date_start", "date_end", "note"])
    started = [r for r in rows if r["date_start"] and r["date_start"] <= today.isoformat()]
    live = [r for r in started if not r["date_end"] or r["date_end"] >= today.isoformat()]
    pick = live or started
    if not pick:
        raise Refused(f"В registry/semesters.csv нет семестра, начавшегося к {today.isoformat()}.")
    return max(pick, key=lambda r: r["date_start"])["semester_id"]


def find_person(people, login):
    return next((p for p in people if p["github"].lower() == login.lower()), None)


def approver_allowed(people, members, approver, permission, ws):
    """Одобрить может мастер, шерпа или владелец этого воркстрима (действующее назначение)."""
    p = find_person(people, approver)
    if p:
        for m in members:
            if m["person_id"] != p["person_id"] or m["date_to"]:
                continue
            if m["role"] == "master" or (m["role"] in APPROVER_ROLES_WS and m["workstream_id"] == ws):
                return p, f"{m['role']} ({p['person_id']})"
    if permission == "admin":
        return p, "владелец репозитория (admin) — пока в реестре нет мастера/шерпы с этим ником"
    return p, None


# ---------------------------------------------------------------- регистрация


def register(body, author, issue, approver, permission, today):
    fields = parse_body(body)
    warnings = []

    ws_codes = re.findall(r"^\s*([a-z0-9][a-z0-9-]*)\s+—", fields.get("workstream", ""))
    ws = ws_codes[0] if ws_codes else ""
    if ws not in workstream_ids():
        raise Refused(f"Не нашёл воркстрим «{fields.get('workstream', '')}» среди паспортов workstream.yml.")

    if "format" in fields:
        formats = [c for c in code_in_parens(fields["format"]) if c in FORMATS]
        if len(formats) != 1:
            raise Refused(f"Не распознал поле «Формат участия»: «{fields['format']}».")
        fmt = formats[0]
    else:
        fmt = "team"                                   # заявка по старой форме, без формата
    roles = [c for c in code_in_parens(fields.get("role", "")) if c in TEAM_ROLES]
    if fmt == "team" and not roles:
        raise Refused("Роль не выбрана («пока не уверен(а)»). Договоритесь с участником о роли, "
                      "отредактируйте поле «Желаемая роль» в заявке и снова поставьте метку `approved`.")

    types = [c for c in code_in_parens(fields.get("type", "")) if c in TYPES]
    if len(types) != 1:
        raise Refused(f"Не распознал поле «Кто вы»: «{fields.get('type', '')}».")
    ptype = types[0]

    login = (fields.get("github") or author).strip().lstrip("@")
    if not GITHUB_LOGIN.match(login):
        raise Refused(f"«{login}» не похоже на GitHub-ник.")
    org = one_line(fields.get("org", ""), "Вуз или организация")
    unit = one_line(fields.get("unit", ""), "Направление, курс, группа")
    if not org or not unit:
        raise Refused("Не заполнены вуз/организация или курс/группа.")

    people = read_csv("participants.csv", PARTICIPANT_COLS)
    members = read_csv("memberships.csv", MEMBERSHIP_COLS)
    teams = read_csv("teams.csv", ["team_id", "workstream_id", "semester_id", "title", "captain_person_id",
                                   "sherpa_person_id", "stand_id", "status", "origin", "note"])

    approver_person, approver_as = approver_allowed(people, members, approver, permission, ws)
    if not approver_as:
        raise Refused(f"@{approver} не найден(а) в реестре как мастер или шерпа/владелец воркстрима `{ws}` "
                      "(действующее назначение в registry/memberships.csv). Метку `approved` ставит шерпа "
                      "этого воркстрима или мастер.")
    sponsor = approver_person["person_id"] if approver_person else ""

    semester = current_semester(today)
    new_people = []
    person = find_person(people, login)
    if person:
        warnings.append(f"`{login}` уже есть в реестре как `{person['person_id']}` — новая строка в "
                        "participants.csv не заводится; вуз и курс из заявки не переносятся.")
        pid = person["person_id"]
    else:
        pid = next_id(people, "person_id", "p", 3)
        new_people.append({"person_id": pid, "github": login, "display_name": login, "org": org, "unit": unit,
                           "type": ptype, "status": "active", "first_semester": semester,
                           "note": f"заявка #{issue}"})

    live_teams = [t for t in teams if t["workstream_id"] == ws and t["semester_id"] == semester
                  and t["status"] in ("forming", "active")]
    team_id = live_teams[0]["team_id"] if fmt == "team" and len(live_teams) == 1 else ""
    if fmt == "team" and not team_id:
        warnings.append(f"Команда не назначена: у `{ws}` в `{semester}` "
                        f"{'нет команды' if not live_teams else 'несколько команд'} в статусе forming/active. "
                        "Перед слиянием впишите `team_id` (роли команды без `team_id` читаются как роли "
                        "уровня воркстрима) или заведите команду в teams.csv.")

    new_members, mid_rows = [], list(members)
    for role in roles or [""]:
        dup = [m for m in members if m["person_id"] == pid and m["semester_id"] == semester
               and m["workstream_id"] == ws and m["format"] == fmt and m["role"] == role and not m["date_to"]]
        if dup:
            warnings.append(f"Участие `{fmt}`{f' в роли `{role}`' if role else ''} уже действует "
                            f"({dup[0]['membership_id']}) — пропущено.")
            continue
        row = {c: "" for c in MEMBERSHIP_COLS}
        row.update(membership_id=next_id(mid_rows, "membership_id", "m", 4), person_id=pid, semester_id=semester,
                   workstream_id=ws, team_id=team_id, format=fmt, role=role, date_from=today.isoformat(),
                   sponsor_person_id=sponsor, entry="request", note=f"заявка #{issue}")
        new_members.append(row)
        mid_rows.append(row)
    if not new_members:
        raise Refused(f"`{login}` уже записан(а) в `{ws}` на `{semester}` в этом формате участия и во всех "
                      "выбранных ролях — добавлять нечего.")
    if ptype == "student-external" and not sponsor:
        warnings.append("Внешний участник без `sponsor_person_id`: одобривший не найден в participants.csv. "
                        "По правилам целостности спонсор-шерпа обязателен — впишите его перед слиянием.")
    if not sponsor and ptype != "student-external":
        warnings.append("`sponsor_person_id` пуст: одобривший не найден в participants.csv.")

    return {"login": login, "pid": pid, "ws": ws, "fmt": fmt, "semester": semester, "approver_as": approver_as,
            "people": new_people, "members": new_members, "warnings": warnings}


def csv_block(cols, rows):
    buf = io.StringIO()
    csv.DictWriter(buf, fieldnames=cols, lineterminator="\n").writerows(rows)
    return buf.getvalue()


def pr_body(r, issue, approver):
    lines = [f"Регистрация по заявке #{issue}: `{r['login']}` → `{r['ws']}`, {r['semester']}, формат участия — "
             f"{FORMATS[r['fmt']]} (`{r['fmt']}`).", "",
             f"Одобрил(а): @{approver} — {r['approver_as']}.", ""]
    if r["people"]:
        lines += ["**registry/participants.csv**", "", "```csv", csv_block(PARTICIPANT_COLS, r["people"]).rstrip(),
                  "```", ""]
    lines += ["**registry/memberships.csv**", "", "```csv", csv_block(MEMBERSHIP_COLS, r["members"]).rstrip(),
              "```", ""]
    if r["warnings"]:
        lines += ["### Проверить перед слиянием", ""] + [f"- ⚠️ {w}" for w in r["warnings"]] + [""]
    lines += ["### Чек-лист шерпы", "",
              "- [ ] Воркстрим, формат участия и роль согласованы с участником",
              "- [ ] Для команды — `team_id` и `profile` по сборке команды",
              "- [ ] Контакты и ФИО внесены в закрытую таблицу (ключ — `person_id`), **не сюда**",
              "- [ ] Участник приглашён в репозиторий воркстрима",
              "",
              f"Closes #{issue}",
              "",
              "_PR открыт автоматически workflow `join-registry.yml`. Если он конфликтует с другим "
              "регистрационным PR — слейте тот, затем снимите и снова поставьте метку `approved` на заявке: "
              "ветка пересоберётся от свежего `main`._"]
    return "\n".join(lines) + "\n"


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--body", required=True, help="файл с телом issue")
    ap.add_argument("--author", required=True, help="ник автора issue")
    ap.add_argument("--issue", required=True, help="номер issue")
    ap.add_argument("--approver", required=True, help="ник поставившего метку approved")
    ap.add_argument("--approver-permission", default="", help="право одобрившего в репозитории (admin, write, …)")
    ap.add_argument("--date", help="дата одобрения ГГГГ-ММ-ДД (по умолчанию сегодня)")
    ap.add_argument("--pr-body-file", help="куда записать текст Pull request")
    ap.add_argument("--comment-file", help="куда записать причину отказа (комментарий к заявке)")
    ap.add_argument("--dry-run", action="store_true", help="не трогать CSV, только показать строки")
    a = ap.parse_args()
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")

    today = date.fromisoformat(a.date) if a.date else date.today()
    body = Path(a.body).read_text(encoding="utf-8")
    try:
        r = register(body, a.author, a.issue, a.approver, a.approver_permission, today)
    except Refused as exc:
        msg = (f"🤖 Автоматическая регистрация не выполнена.\n\n{exc}\n\n"
               "Правила реестра — registry/README.md.")
        if a.comment_file:
            Path(a.comment_file).write_text(msg + "\n", encoding="utf-8")
        print(msg, file=sys.stderr)
        sys.exit(2)

    text = pr_body(r, a.issue, a.approver)
    if a.pr_body_file:
        Path(a.pr_body_file).write_text(text, encoding="utf-8")
    if a.dry_run:
        print(text)
        return
    if r["people"]:
        append_csv("participants.csv", PARTICIPANT_COLS, r["people"])
    append_csv("memberships.csv", MEMBERSHIP_COLS, r["members"])
    print(f"записано: {r['pid']} ({r['login']}) → {r['ws']}, формат {r['fmt']}, строк в memberships: {len(r['members'])}")


if __name__ == "__main__":
    main()
