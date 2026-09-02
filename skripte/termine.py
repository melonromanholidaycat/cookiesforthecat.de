#!/usr/bin/env python3
"""Pull the gig dates from the shared Google calendar into the pages.

The calendar is the source of truth for upcoming gigs. Whoever adds, edits or
deletes an event changes the website; nothing else is required of them.

What this touches:

    termine/index.html              the GIGS block and the EVENTS markup
    vergangene-termine/index.html   the block between the ARCHIVE markers
    jahresuebersicht/index.html     the printable list of this year's gigs
    index.html                      the next gig on the home page
    termine/kalender.ics            the feed people subscribe to
    termine/kalender/*.ics          one file per gig, for a single download
    daten/termine.json              upcoming gigs as of the last sync
    daten/archiv.json               history, only ever appended to
    sitemap.xml                     lastmod on the pages this touches

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
import unicodedata
import urllib.request
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from dateutil.rrule import rrulestr
from icalendar import Calendar, Event

ROOT = Path(__file__).resolve().parent.parent
ZONE = ZoneInfo("Europe/Berlin")
DOMAIN = "cookiesforthecat.de"

SITE = "https://www.cookiesforthecat.de"
FEED = ROOT / "termine/kalender.ics"
SINGLES = ROOT / "termine/kalender"

# A fixed block: daten/README.md promises the band that their end times are
# never published.
LENGTH = timedelta(hours=2)

# How far a repeating gig is written out, and how many dates one series may
# contribute. Without the second limit a weekly residency would bury every
# one-off gig on the page. Single events are not affected by either.
HORIZON = timedelta(days=180)
MOST = 12

# Hardcoded rather than taken from the locale: a CI container's language
# settings are not something to rely on.
WEEKDAYS = ["Montag", "Dienstag", "Mittwoch", "Donnerstag",
            "Freitag", "Samstag", "Sonntag"]
MONTHS = ["Januar", "Februar", "März", "April", "Mai", "Juni", "Juli",
          "August", "September", "Oktober", "November", "Dezember"]

# A description line holding nothing but a URL becomes the link on the venue
# name. A line reading "privat" makes the entry anonymous.
URL_ONLY = re.compile(r"^https?://\S+$")
PRIVATE = re.compile(r"^privat\.?$", re.IGNORECASE)

# Google stores a description as HTML once it has been edited in the web UI.
ANCHOR = re.compile(r"<a\b[^>]*?href=\"([^\"]+)\"[^>]*>(.*?)</a>", re.I | re.S)
LINE_BREAK = re.compile(r"<br\s*/?>|</p>|</div>|</li>", re.I)
TAG = re.compile(r"<[^>]+>")


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


def as_text(description: str) -> str:
    """Google's description is HTML as soon as someone edits it in the web UI.

    An anchor collapses to its address when that is all it says, so the
    URL-on-its-own-line rule keeps working; otherwise the label keeps the
    address after it, rather than losing the link.
    """
    def anchor(match):
        url, label = match.group(1), TAG.sub("", match.group(2)).strip()
        return url if label in ("", url) else f"{label} ({url})"

    text = description
    if "<" in text:
        text = ANCHOR.sub(anchor, text)
        text = LINE_BREAK.sub("\n", text)
        text = TAG.sub("", text)
    # Entities turn up without tags too, so this runs either way.
    return html.unescape(text).replace("\xa0", " ")


def split_description(text: str) -> tuple[list[str], str | None, bool]:
    """Paragraphs, venue link, private flag."""
    paragraphs, link, private = [], None, False
    for line in as_text(text or "").replace("\r\n", "\n").split("\n"):
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


def stamp(value: date | datetime) -> str:
    """One comparable form for a date or a datetime, whatever its timezone."""
    if isinstance(value, datetime):
        moment = value.astimezone(ZONE) if value.tzinfo else value.replace(tzinfo=ZONE)
        return moment.date().isoformat()
    return value.isoformat()


def starts(event, moved: set) -> list:
    """Every date this event happens on, in the window we publish.

    A single event yields one. A repeating one is written out until the
    horizon, minus the dates that were deleted or edited out of the series.
    """
    value = event["DTSTART"].dt
    if not event.get("RRULE"):
        return [value]

    uid = str(event.get("UID", ""))
    whole_day = not isinstance(value, datetime)
    first = datetime.combine(value, time.min) if whole_day else value.replace(tzinfo=None)

    rule = rrulestr(event["RRULE"].to_ical().decode(), dtstart=first)
    skip = {stamp(d.dt if hasattr(d, "dt") else d) for d in exdates(event)}
    end = datetime.now(ZONE).date() + HORIZON

    out = []
    for moment in rule:
        if moment.date() > end or len(out) >= MOST:
            break
        if stamp(moment) in skip or (uid, stamp(moment)) in moved:
            continue
        out.append(moment.date() if whole_day
                   else moment.replace(tzinfo=value.tzinfo or ZONE))
    return out


def exdates(event) -> list:
    """EXDATE arrives as one property or several, each holding one or more."""
    raw = event.get("EXDATE")
    if raw is None:
        return []
    groups = raw if isinstance(raw, list) else [raw]
    return [d for group in groups for d in getattr(group, "dts", [])]


def one_gig(event, value) -> dict:
    if isinstance(value, datetime):
        # Google sends a timezone; without one, read it as local time.
        value = value.astimezone(ZONE) if value.tzinfo else value.replace(tzinfo=ZONE)
        # Machine-readable; the page formats it when rendering.
        day, time_of_day = value.date(), f"{value.hour:02d}:{value.minute:02d}"
    else:
        # All-day: no time. An unsettled time belongs in the description.
        day, time_of_day = value, None

    paragraphs, link, private = split_description(
        str(event.get("DESCRIPTION", "")))
    # as_text here too: a venue called "Fisch & Bier" arrives as an entity.
    venue = as_text(str(event.get("SUMMARY", ""))).strip()
    address = as_text(str(event.get("LOCATION", ""))).strip()

    return {
        "datum": day.isoformat(),
        "zeit": None if private else time_of_day,
        "ort": "private Veranstaltung" if private else (venue or None),
        "ort_link": None if private else link,
        "adresse": None if private else (address or None),
        "text": [] if private else paragraphs,
        "privat": private,
    }


def read_events(raw: bytes) -> list[dict]:
    try:
        calendar = Calendar.from_ical(raw)
    except Exception as error:                       # noqa: BLE001
        raise Abort(f"Calendar is not readable: {error}") from error

    gigs = []
    # An edited or deleted single date of a series arrives as its own VEVENT
    # carrying RECURRENCE-ID. The series must not also produce that date.
    moved = {(str(e.get("UID", "")), stamp(e["RECURRENCE-ID"].dt))
             for e in calendar.walk("VEVENT") if e.get("RECURRENCE-ID")}

    for event in calendar.walk("VEVENT"):
        if str(event.get("STATUS", "")).upper() == "CANCELLED":
            continue
        if event.get("DTSTART") is None:
            continue
        for value in starts(event, moved):
            gigs.append(one_gig(event, value))

    gigs.sort(key=lambda g: (g["datum"], g["zeit"] or ""))
    return gigs


# ------------------------------------------------------------- Rendering

def esc(text: str) -> str:
    return html.escape(text, quote=False)


def clock(time_of_day: str) -> str:
    """19:00 becomes 19:00 Uhr — colon and padded hour, as DIN 5008 has it."""
    return f"{time_of_day} Uhr"


def long_date(iso: str, time_of_day: str | None) -> str:
    day = date.fromisoformat(iso)
    text = f"{WEEKDAYS[day.weekday()]}, {day:%d.%m.%Y}"
    return f"{text} · {clock(time_of_day)}" if time_of_day else text


def gig_lines(gig: dict, name: str) -> str:
    venue = esc(gig["ort"]) if gig["ort"] else ""
    if gig.get("ort_link"):
        venue = (f'<a href="{gig["ort_link"]}" rel="noopener" target="_blank">'
                 f"{venue}</a>")
    lines = [
        '    <li class="gig">',
        f'      <p class="gig-date"><time datetime="{gig["datum"]}">'
        f'{esc(long_date(gig["datum"], gig["zeit"]))}</time></p>',
    ]
    if gig["ort"]:
        lines.append(f'      <p class="gig-venue">{venue}</p>')
    if gig.get("adresse"):
        lines.append(f'      <p class="gig-address">{esc(gig["adresse"])}</p>')
    for paragraph in gig.get("text", []):
        lines.append(f'      <p class="gig-note">{esc(paragraph)}</p>')
    # A private entry is a date and nothing else, so there is nothing to add.
    if not gig["privat"]:
        lines.append(f'      <p class="gig-add"><a href="kalender/{name}.ics">'
                     "Zum Kalender hinzufügen</a></p>")
    lines.append("    </li>")
    return "\n".join(lines)


def render_gigs(gigs: list[dict], names: list[str]) -> str:
    if not gigs:
        return ('  <p class="content">Zurzeit stehen keine Termine fest. '
                "Schau bald wieder vorbei.</p>")
    return ('  <ul class="gigs content">\n'
            + "\n".join(gig_lines(g, n) for g, n in zip(gigs, names))
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


def year_place(entry: dict) -> tuple[str, str | None]:
    """The venue name that goes in bold, and the address line after it.

    A calendar gig carries both. So does an archive entry written from 2026
    on; older ones hold only "Venue, Town", which splits at the last comma.
    """
    if entry.get("ort"):
        return entry["ort"], entry.get("adresse")
    text = entry.get("text") or "Auftritt"
    name, _, town = text.rpartition(", ")
    return (name, town) if name else (text, None)


def year_rows(archive: list[dict], upcoming: list[dict],
              year: int) -> list[tuple]:
    """Every gig of one year, oldest first: date, time, venue, address.

    Played ones come from the archive, coming ones from the calendar. The two
    cannot overlap: a date is in exactly one of them.
    """
    prefix = f"{year}-"
    rows = [(e["datum"], e.get("zeit"), *year_place(e))
            for e in archive if e["datum"].startswith(prefix)]
    rows += [(g["datum"], g["zeit"], *year_place(g))
             for g in upcoming if g["datum"].startswith(prefix)]
    rows.sort(key=lambda row: (row[0], row[1] or ""))
    return rows


def render_year(archive: list[dict], upcoming: list[dict], year: int) -> str:
    """The year on one page, laid out like the document the band handed out:
    a month heading, then two lines per gig — when, then where in bold."""
    rows = year_rows(archive, upcoming, year)
    if not rows:
        return ('  <p class="content">Für dieses Jahr stehen noch keine '
                "Termine fest.</p>")
    blocks, month, items = [], None, []
    for datum, zeit, name, address in rows:
        day = date.fromisoformat(datum)
        if day.month != month:
            if items:
                blocks.append((month, items))
            month, items = day.month, []
        where = f"<strong>{esc(name)}</strong>"
        if address:
            where += f" &middot; {esc(address)}"
        items.append(
            "      <li>\n"
            f'        <p class="year-when"><time datetime="{datum}">'
            f"{esc(long_date(datum, zeit))}</time></p>\n"
            f'        <p class="year-where">{where}</p>\n'
            "      </li>")
    blocks.append((month, items))
    return "\n\n".join(
        f'  <section class="content">\n'
        f'    <h2 class="year-month">{MONTHS[m - 1]} {year}</h2>\n'
        f'    <ul class="year-list">\n' + "\n".join(its)
        + "\n    </ul>\n  </section>"
        for m, its in blocks
    )


def render_next(gigs: list[dict]) -> str:
    if not gigs:
        return ('  <p class="centred"><a href="termine/">Alle Termine '
                "ansehen &rarr;</a></p>")
    nxt = gigs[0]
    where = "" if nxt["privat"] else f' &middot; {esc(nxt["ort"])}' if nxt["ort"] else ""
    return ('  <p class="centred"><a href="termine/">Nächster Auftritt: '
            f'{esc(long_date(nxt["datum"], nxt["zeit"]))}{where} &rarr;</a></p>')


def place(gig: dict) -> dict:
    """Venue and address for schema.org. The address is one string on the page,
    so split it where it parses and fall back to plain text where it does not."""
    spot = {"@type": "Place", "name": gig["ort"] or "Auftritt"}
    if gig.get("ort_link"):
        spot["url"] = gig["ort_link"]
    address = gig.get("adresse")
    if not address:
        return spot
    parts = [p.strip() for p in address.split("·") if p.strip()]
    town = re.match(r"^(\d{5})\s+(.+)$", parts[-1]) if parts else None
    if town:
        spot["address"] = {
            "@type": "PostalAddress",
            "postalCode": town.group(1),
            "addressLocality": town.group(2),
            "addressCountry": "DE",
        }
        if parts[:-1]:
            spot["address"]["streetAddress"] = ", ".join(parts[:-1])
    else:
        spot["address"] = address
    return spot


def render_events(gigs: list[dict]) -> str:
    """schema.org events, so search engines and assistants can read the gigs.

    Private bookings are left out: a date with no venue is nothing to publish.
    """
    band = {"@type": "MusicGroup", "name": "Cookies For The Cat", "url": f"{SITE}/"}
    events = []
    for gig in gigs:
        if gig["privat"]:
            continue
        day = date.fromisoformat(gig["datum"])
        start = gig["datum"]
        if gig["zeit"]:
            hour, minute = (int(part) for part in gig["zeit"].split(":"))
            start = datetime(day.year, day.month, day.day, hour, minute,
                             tzinfo=ZONE).isoformat()
        events.append({
            "@context": "https://schema.org",
            "@type": "MusicEvent",
            "name": f"Cookies For The Cat – {gig['ort']}",
            "startDate": start,
            "eventStatus": "https://schema.org/EventScheduled",
            "eventAttendanceMode": "https://schema.org/OfflineEventAttendanceMode",
            "location": place(gig),
            "performer": band,
            "image": f"{SITE}/assets/img/share.jpg",
            "url": f"{SITE}/termine/",
            **({"description": " ".join(gig["text"])} if gig.get("text") else {}),
        })
    if not events:
        return ""
    # Escaped so a description containing </script> cannot end the block early.
    body = json.dumps(events, ensure_ascii=False, indent=2).replace("<", "\\u003C")
    return ('  <script type="application/ld+json">\n'
            + "\n".join("  " + line for line in body.split("\n"))
            + "\n  </script>")


# -------------------------------------------------------- Calendar files

TRANSLITERATE = str.maketrans({"ä": "ae", "ö": "oe", "ü": "ue", "ß": "ss",
                               "Ä": "ae", "Ö": "oe", "Ü": "ue"})


def slug(text: str) -> str:
    """Aventura Bremen -> aventura-bremen. File names and UIDs stay readable."""
    folded = unicodedata.normalize("NFKD", text.translate(TRANSLITERATE))
    ascii_only = folded.encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", ascii_only.lower()).strip("-")[:60].strip("-")


def file_names(gigs: list[dict]) -> list[str]:
    """One name per gig, for both its file and its UID.

    Derived from the gig, not from the calendar's event id, so the files still
    work if daten/termine.json is ever maintained by hand.
    """
    used, names = set(), []
    for gig in gigs:
        stem = f"{gig['datum']}-{slug(gig['ort'] or '') or 'auftritt'}"
        name, count = stem, 1
        while name in used:            # two gigs, one day, same venue name
            count += 1
            name = f"{stem}-{count}"
        used.add(name)
        names.append(name)
    return names


def moment(gig: dict) -> date | datetime:
    """All-day gigs stay dates. Timed ones become UTC, so the file carries no
    VTIMEZONE block and every app still shows the right local time."""
    day = date.fromisoformat(gig["datum"])
    if not gig["zeit"]:
        return day
    hour, minute = (int(part) for part in gig["zeit"].split(":"))
    return datetime(day.year, day.month, day.day, hour, minute,
                    tzinfo=ZONE).astimezone(timezone.utc)


def vevent(gig: dict, name: str, standalone: bool) -> Event:
    """One VEVENT. `standalone` names the band in the summary, for the
    single downloads that land in a calendar full of other things."""
    entry = Event()
    venue = gig["ort"] or "Auftritt"
    entry.add("SUMMARY", f"Cookies For The Cat · {venue}" if standalone else venue)

    start = moment(gig)
    entry.add("DTSTART", start)
    entry.add("DTEND", start + (LENGTH if isinstance(start, datetime)
                                else timedelta(days=1)))
    # The gig's date, not the time of the run: a real timestamp would rewrite
    # every file every hour.
    entry.add("DTSTAMP", datetime.fromisoformat(gig["datum"]).replace(
        tzinfo=timezone.utc))
    entry.add("UID", f"{name}@{DOMAIN}")

    if gig.get("adresse"):
        # A comma, so a calendar app can find the place on a map.
        entry.add("LOCATION", gig["adresse"].replace(" · ", ", "))
    body = list(gig.get("text", []))
    if gig.get("ort_link"):
        entry.add("URL", gig["ort_link"])
        body.append(gig["ort_link"])
    if body:
        entry.add("DESCRIPTION", "\n\n".join(body))
    return entry


def calendar_file(events: list[Event], subscribable: bool = False) -> bytes:
    cal = Calendar()
    cal.add("PRODID", f"-//Cookies For The Cat//{DOMAIN}//DE")
    cal.add("VERSION", "2.0")
    cal.add("CALSCALE", "GREGORIAN")
    cal.add("METHOD", "PUBLISH")
    if subscribable:
        cal.add("X-WR-CALNAME", "Cookies For The Cat")
        cal.add("X-WR-TIMEZONE", "Europe/Berlin")
        # Two spellings of the same thing: Apple, Google and Outlook.
        cal.add("REFRESH-INTERVAL", timedelta(hours=12),
                parameters={"VALUE": "DURATION"})
        cal.add("X-PUBLISHED-TTL", "PT12H")
    for entry in events:
        cal.add_component(entry)
    return cal.to_ical()


def write_bytes(path: Path, data: bytes) -> bool:
    if path.exists() and path.read_bytes() == data:
        return False
    path.write_bytes(data)
    return True


def write_calendars(gigs: list[dict], names: list[str]) -> bool:
    """The feed, and one file per public gig.

    termine/kalender/ belongs to this script: anything not in the current run
    is deleted, so a cancelled gig cannot leave a file behind for someone to
    download.
    """
    SINGLES.mkdir(parents=True, exist_ok=True)

    feed = [vevent(g, n, standalone=False) for g, n in zip(gigs, names)]
    changed = write_bytes(FEED, calendar_file(feed, subscribable=True))

    singles = {f"{n}.ics": calendar_file([vevent(g, n, standalone=True)])
               for g, n in zip(gigs, names) if not g["privat"]}
    for path in sorted(SINGLES.glob("*.ics")):
        if path.name not in singles:
            path.unlink()
            changed = True
    for filename, data in singles.items():
        changed |= write_bytes(SINGLES / filename, data)
    return changed


# ----------------------------------------------------------------- Files

def splice(path: Path, marker: str, content: str) -> bool:
    text = path.read_text(encoding="utf-8")
    pattern = re.compile(
        rf"(<!-- {marker}:START.*?-->\n)(.*?)(\n *<!-- {marker}:END -->)", re.S)
    if not pattern.search(text):
        raise Abort(f"Marker {marker} missing in {path}")
    updated = pattern.sub(lambda m: m.group(1) + content + m.group(3), text)
    if updated == text:
        return False
    path.write_text(updated, encoding="utf-8")
    return True


def touch_sitemap(paths: list[str], day: date) -> bool:
    """Record today against the pages this run changed."""
    file = ROOT / "sitemap.xml"
    text = file.read_text(encoding="utf-8")
    updated = text
    for path in paths:
        loc = f"{SITE}{path}"
        updated = re.sub(
            rf"(<url><loc>{re.escape(loc)}</loc>)(<lastmod>[^<]*</lastmod>)?(</url>)",
            rf"\g<1><lastmod>{day.isoformat()}</lastmod>\g<3>", updated)
    if updated == text:
        return False
    file.write_text(updated, encoding="utf-8")
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
    # Date and place identify an entry; the time is extra, not part of it.
    known = {(e["datum"], e["text"]) for e in archive}
    added = 0
    for gig in from_calendar + previous:
        if gig["datum"] >= today.isoformat():
            continue
        entry = {"datum": gig["datum"], "text": archive_text(gig)}
        if gig.get("zeit"):
            entry["zeit"] = gig["zeit"]
        # Kept for the Jahresübersicht, which prints the full address. Not
        # for a private booking, where "text" is all there is to say.
        if not gig["privat"]:
            for key in ("ort", "adresse"):
                if gig.get(key):
                    entry[key] = gig[key]
        if (entry["datum"], entry["text"]) not in known:
            archive.append(entry)
            known.add((entry["datum"], entry["text"]))
            added += 1

    names = file_names(upcoming)

    print(f"  {len(upcoming)} upcoming gigs, {added} newly archived "
          f"({len(archive)} total)")

    if options.dry_run:
        print(render_gigs(upcoming, names))
        return 0

    gigs_changed = splice(ROOT / "termine/index.html", "GIGS",
                          render_gigs(upcoming, names))
    events_changed = splice(ROOT / "termine/index.html", "EVENTS",
                            render_events(upcoming))
    archive_changed = splice(ROOT / "vergangene-termine/index.html", "ARCHIVE",
                             render_archive(archive))
    next_changed = splice(ROOT / "index.html", "NEXT", render_next(upcoming))
    year_page = ROOT / "jahresuebersicht/index.html"
    head_changed = splice(
        year_page, "YEARHEAD",
        f'    <h1 class="year-title">Unsere Auftritte {today.year}</h1>')
    year_changed = splice(year_page, "YEAR",
                          render_year(archive, upcoming, today.year))

    touched = ([ "/termine/" ] if gigs_changed or events_changed else []) \
        + ([ "/vergangene-termine/" ] if archive_changed else []) \
        + ([ "/jahresuebersicht/" ] if head_changed or year_changed else []) \
        + ([ "/" ] if next_changed else [])

    changed = [
        gigs_changed, events_changed, archive_changed, next_changed,
        head_changed, year_changed,
        write_calendars(upcoming, names),
        touch_sitemap(touched, today) if touched else False,
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
