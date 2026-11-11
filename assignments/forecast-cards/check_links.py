"""Проверяет ссылки реестра карточек прогнозов (registry.csv) и записывает результат.

Для каждой карточки открывает url (с переходами по редиректам) и заполняет:
- last_checked — дата проверки, ГГГГ-ММ-ДД;
- link_status — ok · moved (открылась, но по другому адресу) · not_found (404) · error:<код или причина>;
- final_url — адрес, на котором ссылка открылась, если он отличается от url.

Ссылки не переписываются: если карточка переехала, это видно по moved и final_url, а новую ссылку
вносит автор или куратор (Issue или PR в registry.csv), старая уходит в note.

Ограничение: GitVerse и SourceCraft — одностраничные приложения и могут отвечать 200 даже на
несуществующий репозиторий. Для них ok значит «сайт ответил», а не «карточка точно на месте».
Источники внутри карточек скрипт не проверяет — это делает автор при обновлении (поле sources_checked).

    python assignments/forecast-cards/check_links.py          # проверить и записать в registry.csv
    python assignments/forecast-cards/check_links.py --dry    # только показать
"""
import csv
import datetime as dt
import sys
import urllib.error
import urllib.request
from pathlib import Path

REG = Path(__file__).resolve().parent / "registry.csv"
UA = "Mozilla/5.0 (econ-library forecast-cards link check)"


def norm(u):
    return u.rstrip("/").removesuffix(".git").lower()


def check(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            final = r.geturl()
            return ("ok" if norm(final) == norm(url) else "moved"), final
    except urllib.error.HTTPError as e:
        return ("not_found" if e.code == 404 else f"error:{e.code}"), ""
    except Exception as e:  # сеть, таймаут, DNS
        return f"error:{type(e).__name__}", ""


def main():
    dry = "--dry" in sys.argv
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    raw = REG.read_text(encoding="utf-8")
    nl = "\r\n" if "\r\n" in raw else "\n"
    with open(REG, encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        fields, rows = reader.fieldnames, list(reader)
    today = dt.date.today().isoformat()
    for r in rows:
        status, final = check(r["url"])
        r["last_checked"], r["link_status"] = today, status
        r["final_url"] = final if status == "moved" else ""
        print(f'{r["card_id"]}  {status:<12} {r["url"]}' + (f"  → {final}" if status == "moved" else ""))
    if not dry:
        with open(REG, "w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=fields, lineterminator=nl)
            w.writeheader()
            w.writerows(rows)
        print("written", REG)


if __name__ == "__main__":
    main()
