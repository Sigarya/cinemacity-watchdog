#!/usr/bin/env python3
"""Cinema City Flora: notify about *analogue* IMAX 70mm showtimes on Jan 6–13, 2027.

Uses Cinema City's public Quickbook schedule endpoint. No login or API key needed.
"""
import argparse
import json
import os
import sys
import time
from datetime import datetime, date, timedelta
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

BASE = "https://www.cinemacity.cz/cz/data-api-service/v1/quickbook/10101"
CINEMA_ID = "1052"  # Praha Flora
CINEMA_NAME = "Cinema City Flora (Prague)"
START_DAY = date(2027, 1, 6)
END_DAY = date(2027, 1, 13)
PRAGUE = ZoneInfo("Europe/Prague")
USER_AGENT = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")


def days_in_trip():
    current = START_DAY
    while current <= END_DAY:
        yield current
        current += timedelta(days=1)


def fetch_api(path):
    url = BASE + path
    last_error = None
    for attempt in range(3):
        try:
            req = Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
            with urlopen(req, timeout=20) as response:
                obj = json.load(response)
            if not isinstance(obj, dict) or not isinstance(obj.get("body"), dict):
                raise ValueError("Unexpected API response")
            return obj["body"]
        except (HTTPError, URLError, TimeoutError, ValueError, json.JSONDecodeError) as exc:
            last_error = exc
            if attempt < 2:
                time.sleep(2 ** attempt)
    raise RuntimeError(f"Cinema City request failed for {url}: {last_error}")


def fetch_day(day):
    return fetch_api(f"/film-events/in-cinema/{CINEMA_ID}/at-date/{day.isoformat()}?attr=&lang=cs_CZ")


def available_trip_days():
    # Only query dates the cinema has published. Unscheduled dates may 404.
    body = fetch_api(f"/dates/in-cinema/{CINEMA_ID}/until/{END_DAY.isoformat()}?attr=&lang=cs_CZ")
    dates = set(str(d)[:10] for d in (body.get("dates") or []))
    return [day for day in days_in_trip() if day.isoformat() in dates]


def is_analogue_imax70mm(event):
    auditorium = (event.get("auditorium") or "").lower()
    attrs = {str(a).lower() for a in (event.get("attributeIds") or [])}
    return "imax" in auditorium and "70-mm" in attrs


def parse_events(day, body):
    films = {str(f["id"]): f for f in body.get("films", []) if "id" in f}
    found = {}
    for event in body.get("events", []):
        if not is_analogue_imax70mm(event):
            continue
        iso = str(event.get("eventDateTime", ""))
        # Validate local calendar date; API endpoint is date-scoped but check anyway.
        if iso[:10] != day.isoformat():
            continue
        eid = str(event.get("id", ""))
        if not eid:
            continue
        film = films.get(str(event.get("filmId", "")), {})
        code = event.get("presentationCode") or eid
        found[eid] = {
            "id": eid,
            "film": film.get("name") or "Film (title unavailable)",
            "datetime": iso,
            "auditorium": event.get("auditorium") or "IMAX",
            "cinema": CINEMA_NAME,
            "soldOut": bool(event.get("soldOut")),
            "booking": f"https://tickets.cinemacity.cz/order/{code}",
        }
    return found


def collect():
    all_events = {}
    for day in available_trip_days():
        all_events.update(parse_events(day, fetch_day(day)))
        time.sleep(0.12)  # keep requests gentle
    return all_events


def read_state(path):
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data.get("events"), dict):
            raise ValueError("Invalid state format")
        return data
    except FileNotFoundError:
        return {"events": {}}


def write_state(path, state):
    path.parent.mkdir(parents=True, exist_ok=True)
    rendered = json.dumps(state, indent=2, ensure_ascii=False, sort_keys=True) + "\n"
    if not path.exists() or path.read_text(encoding="utf-8") != rendered:
        path.write_text(rendered, encoding="utf-8")


def notify_output(value):
    if path := os.environ.get("GITHUB_OUTPUT"):
        with open(path, "a", encoding="utf-8") as f:
            f.write(f"has_news={'true' if value else 'false'}\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state", default="state/seen.json")
    parser.add_argument("--report", default="report.md")
    parser.add_argument("--title", default="title.txt")
    parser.add_argument("--force-report", action="store_true")
    args = parser.parse_args()

    # Keep the GitHub workflow harmless after the user's trip ends.
    if datetime.now(PRAGUE).date() > END_DAY:
        print("Trip ended. Stop/disable this workflow in GitHub Actions.")
        notify_output(False)
        return 0

    current = collect()
    state_path = Path(args.state)
    state = read_state(state_path)
    old = state["events"]
    new = [v for k, v in current.items() if args.force_report or k not in old]
    new.sort(key=lambda v: (v["datetime"], v["film"]))

    # Keep all previously observed IDs so a briefly withdrawn event doesn't
    # cause duplicate new-event alerts after being relisted.
    merged = dict(old)
    merged.update(current)
    write_state(state_path, {"events": merged})

    if not new:
        print(f"Checked {len(current)} IMAX 70mm showtimes for Jan 6–13. No new screenings.")
        notify_output(False)
        return 0

    lines = ["### New genuine IMAX 70mm showtimes — Cinema City Flora", "",
             "**Dates watched:** January 6–13, 2027 · **Format:** analogue IMAX 70mm film", ""]
    for e in new:
        d = datetime.fromisoformat(e["datetime"])
        availability = " (currently marked sold out)" if e["soldOut"] else ""
        lines.append(f"- **{d:%a %d %b %Y, %H:%M}** — {e['film']}{availability} — "
                     f"[**Choose seats / buy tickets**]({e['booking']})")
    lines.extend(["", "The format is matched using both the IMAX auditorium and the `70-mm` screening attribute.",
                  "Verify the film format again on the ticket page before paying."])
    Path(args.report).write_text("\n".join(lines) + "\n", encoding="utf-8")
    Path(args.title).write_text(f"🎞️ Prague IMAX 70mm: {len(new)} new January screening(s) — tickets", encoding="utf-8")
    print(f"Found {len(new)} new screenings. Ticket links written to {args.report}.")
    notify_output(True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
