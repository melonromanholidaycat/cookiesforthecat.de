#!/usr/bin/env python3
"""Pull the gig dates from the shared Google calendar into the pages.

The calendar is the source of truth for upcoming gigs. Whoever adds, edits or
deletes an event changes the website; nothing else is required of them.

What this touches:

    termine/index.html              the block between the GIGS markers
    vergangene-termine/index.html   the block between the ARCHIVE markers
    index.html                      the next gig on the home page
    daten/termine.json              upcoming gigs as of the last sync
    daten/archiv.json               history, only ever appended to

Everything outside the markers is left alone. The committed HTML stays exactly
what gets served; there is no build step.

Note on language: everything here is English except the data keys (datum, ort,
adresse, ...). The files in daten/ are the fallback a German-speaking
maintainer edits by hand if the calendar ever goes away, so the field names are
in their language. See AGENTS.md.

Usage:
    CALENDAR_ICS_URL=... python3 skripte/termine.py
    CALENDAR_ICS_FILE=fixture.ics python3 skripte/termine.py --dry-run
"""

from __future__ import annotations

import argparse
import json
import html
import os
import re
import sys
import urllib.request
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from icalendar import Calendar

ROOT = Path(__file__).resolve().parent.parent
ZONE = ZoneInfo("Europe/Berlin")

# Hardcoded rather than taken from the locale: a CI container's language
# settings are not something to rely on.
WEEKDAYS = ["Montag", "Dienstag", "Mittwoch", "Donnerstag",
            "Freitag", "Samstag", "Sonntag"]

# A description line holding nothing but a URL becomes the link on the venue
# name. A line reading "privat" makes the entry anonymous.
URL_ONLY = re.compile(r"^https?://\S+$")
PRIVATE = re.compile(r"^privat\.?$", re.IGNORECASE)


class Abort(Exception):
    """Something is wrong — better to write nothing than something wrong."""


# --------------------------------------------------------------- Calendar

def read_feed(url: str | None, file: str | None) -> bytes:
    if file:
        return Path(file).read_bytes()
    if not url:
        raise Abort("Neither CALENDAR_ICS_URL nor CALENDAR_ICS_FILE is set.")
    try:
        with urllib.request.urlopen(url, timeout=60) as response:
            return response.read()
    except Exception as error:                       # noqa: BLE001
        raise Abort(f"Calendar unreachable: {error}") from error


def split_description(text: str) -> tuple[list[str], str | None, bool]:
    """Paragraphs, venue link, private flag."""
    paragraphs, link, private = [], None, False
    for line in (text or "").replace("\r\n", "\n").split("\n"):
        line = line.strip()
        if not line:
            continue
        if PRIVATE.match(line):
            private = True
        elif URL_ONLY.match(line) and link is None:
            link = line
        else:
            paragraphs.append(line)
    return paragraphs, link, private


def read_events(raw: bytes) -> list[dict]:
    try:
        calendar = Calendar.from_ical(raw)
    except Exception as error:                       # noqa: BLE001
        raise Abort(f"Calendar is not readable: {error}") from error

    gigs, recurring = [], []

    for event in calendar.walk("VEVENT"):
        if str(event.get("STATUS", "")).upper() == "CANCELLED":
            continue
        if event.get("RRULE"):
            recurring.append(str(event.get("SUMMARY", "?")))
            continue

        start = event.get("DTSTART")
        if start is None:
            continue
        value = start.dt

        if isinstance(value, datetime):
            # Google sends a timezone; without one, read it as local time.
            value = value.astimezone(ZONE) if value.tzinfo else value.replace(tzinfo=ZONE)
            day, time_of_day = value.date(), f"{value.hour}.{value.minute:02d} Uhr"
        else:
            # All-day: show no time. If the time simply isn't settled yet that
            # belongs in the description, where it can say so in words.
            day, time_of_day = value, None

        paragraphs, link, private = split_description(
            str(event.get("DESCRIPTION", "")))
        venue = str(event.get("SUMMARY", "")).strip()
        address = str(event.get("LOCATION", "")).strip()

        gigs.append({
            "datum": day.isoformat(),
            "zeit": None if private else time_of_day,
            "ort": "private Veranstaltung" if private else (venue or None),
            "ort_link": None if private else link,
            "adresse": None if private else (address or None),
            "text": [] if private else paragraphs,
            "privat": private,
        })

    if recurring:
        print(f"  Note: skipped {len(recurring)} recurring event(s): "
              + ", ".join(recurring), file=sys.stderr)

    gigs.sort(key=lambda g: (g["datum"], g["zeit"] or ""))
    return gigs


# ------------------------------------------------------------- Rendering

def esc(text: str) -> str:
    return html.escape(text, quote=False)


def long_date(iso: str, time_of_day: str | None) -> str:
    day = date.fromisoformat(iso)
    text = f"{WEEKDAYS[day.weekday()]}, {day:%d.%m.%Y}"
    return f"{text} · {time_of_day}" if time_of_day else text


def gig_lines(gig: dict) -> str:
    venue = esc(gig["ort"]) if gig["ort"] else ""
    if gig.get("ort_link"):
        venue = (f'<a href="{gig["ort_link"]}" rel="noopener" target="_blank">'
                 f"{venue}</a>")
    lines = [
        '  <li class="gig">',
        f'    <p class="gig-date"><time datetime="{gig["datum"]}">'
        f'{esc(long_date(gig["datum"], gig["zeit"]))}</time></p>',
    ]
    if gig["ort"]:
        lines.append(f'    <p class="gig-venue">{venue}</p>')
    if gig.get("adresse"):
        lines.append(f'    <p class="gig-address">{esc(gig["adresse"])}</p>')
    for paragraph in gig.get("text", []):
        lines.append(f'    <p class="gig-note">{esc(paragraph)}</p>')
    lines.append("  </li>")
    return "\n".join(lines)


def render_gigs(gigs: list[dict]) -> str:
    if not gigs:
        return ('  <p class="content">Zurzeit stehen keine Termine fest. '
                "Schau bald wieder vorbei.</p>")
    return ('  <ul class="gigs content">\n'
            + "\n".join(gig_lines(g) for g in gigs)
            + "\n  </ul>")


def render_archive(entries: list[dict]) -> str:
    """Newest first, one heading per year."""
    ordered = sorted(entries, key=lambda e: e["datum"], reverse=True)
    blocks, year, open_year = [], None, []
    for entry in ordered:
        y = entry["datum"][:4]
        if y != year:
            if open_year:
                blocks.append((year, open_year))
            year, open_year = y, []
        day = date.fromisoformat(entry["datum"])
        open_year.append(f'      <li><time datetime="{entry["datum"]}">'
                         f'{day:%d.%m.%Y}</time> {esc(entry["text"])}</li>')
    if open_year:
        blocks.append((year, open_year))
    return "\n\n".join(
        f'  <section class="content">\n    <h2 class="archive-year">{y}</h2>\n'
        f'    <ul class="archive">\n' + "\n".join(lines) + "\n    </ul>\n  </section>"
        for y, lines in blocks
    )


def render_next(gigs: list[dict]) -> str:
    if not gigs:
        return ('  <p class="centred next-gig"><a href="termine/">Alle Termine '
                "ansehen &rarr;</a></p>")
    nxt = gigs[0]
    where = "" if nxt["privat"] else f' &middot; {esc(nxt["ort"])}' if nxt["ort"] else ""
    return ('  <p class="centred next-gig"><a href="termine/">Nächster Auftritt: '
            f'{esc(long_date(nxt["datum"], nxt["zeit"]))}{where} &rarr;</a></p>')


# ----------------------------------------------------------------- Files

def splice(path: Path, marker: str, content: str) -> bool:
    text = path.read_text(encoding="utf-8")
    pattern = re.compile(
        rf"(<!-- {marker}:START.*?-->\n)(.*?)(\n  <!-- {marker}:END -->)", re.S)
    if not pattern.search(text):
        raise Abort(f"Marker {marker} missing in {path}")
    updated = pattern.sub(lambda m: m.group(1) + content + m.group(3), text)
    if updated == text:
        return False
    path.write_text(updated, encoding="utf-8")
    return True


def write_json(path: Path, data) -> None:
    with path.open("w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2)
        fh.write("\n")


# ------------------------------------------------------------------- Run

def archive_text(gig: dict) -> str:
    """One archive line: 'Venue, Town' or 'private Veranstaltung'."""
    if gig["privat"]:
        return "private Veranstaltung"
    town = ""
    if gig.get("adresse"):
        last = gig["adresse"].split("·")[-1].strip()
        town = re.sub(r"^\d{5}\s*", "", last)
    return f"{gig['ort']}, {town}" if gig["ort"] and town else (gig["ort"] or "Auftritt")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true",
                        help="show the result, write nothing")
    options = parser.parse_args()

    today = datetime.now(ZONE).date()
    gigs_file = ROOT / "daten/termine.json"
    archive_file = ROOT / "daten/archiv.json"

    previous = json.loads(gigs_file.read_text(encoding="utf-8"))
    archive = json.loads(archive_file.read_text(encoding="utf-8"))

    raw = read_feed(os.environ.get("CALENDAR_ICS_URL"),
                    os.environ.get("CALENDAR_ICS_FILE"))
    from_calendar = read_events(raw)

    # An empty calendar when we already hold gigs is almost always a fault at
    # the other end, so do nothing rather than wipe the list.
    if not from_calendar and previous:
        raise Abort(f"Calendar returned 0 events, previously there were "
                    f"{len(previous)}. Nothing written.")

    upcoming = [g for g in from_calendar if g["datum"] >= today.isoformat()]

    # Archive from calendar and last snapshot together, so a gig still lands in
    # the archive even if its event was deleted after the date passed.
    known = {(e["datum"], e["text"]) for e in archive}
    added = 0
    for gig in from_calendar + previous:
        if gig["datum"] >= today.isoformat():
            continue
        entry = {"datum": gig["datum"], "text": archive_text(gig)}
        if (entry["datum"], entry["text"]) not in known:
            archive.append(entry)
            known.add((entry["datum"], entry["text"]))
            added += 1

    print(f"  {len(upcoming)} upcoming gigs, {added} newly archived "
          f"({len(archive)} total)")

    if options.dry_run:
        print(render_gigs(upcoming))
        return 0

    changed = [
        splice(ROOT / "termine/index.html", "GIGS", render_gigs(upcoming)),
        splice(ROOT / "vergangene-termine/index.html", "ARCHIVE",
               render_archive(archive)),
        splice(ROOT / "index.html", "NEXT", render_next(upcoming)),
    ]
    write_json(gigs_file, upcoming)
    write_json(archive_file, sorted(archive, key=lambda e: e["datum"], reverse=True))

    print("  pages changed" if any(changed) else "  pages unchanged")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Abort as error:
        print(f"Abort: {error}", file=sys.stderr)
        sys.exit(1)
