#!/usr/bin/env python3
"""Holt die Auftrittstermine aus dem geteilten Google-Kalender und schreibt sie
in die Seiten.

Der Kalender ist die Quelle für kommende Termine. Wer einen Auftritt anlegt,
ändert oder löscht, ändert damit die Website — mehr ist nicht nötig.

Was dieses Skript anfasst:

    termine/index.html              der Block zwischen den GIGS-Markern
    vergangene-termine/index.html   der Block zwischen den ARCHIV-Markern
    index.html                      der nächste Termin auf der Startseite
    daten/termine.json              Stand der kommenden Termine
    daten/archiv.json               Archiv, wird nur ergänzt, nie gekürzt

Alles außerhalb der Marker bleibt unberührt. Die HTML-Dateien im Repository
sind weiterhin das, was ausgeliefert wird; es gibt keinen Build-Schritt.

Aufruf:
    CALENDAR_ICS_URL=... python3 skripte/termine.py
    CALENDAR_ICS_FILE=fixture.ics python3 skripte/termine.py --probelauf
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

WURZEL = Path(__file__).resolve().parent.parent
ZONE = ZoneInfo("Europe/Berlin")

# Namen fest verdrahtet — die Sprachumgebung eines CI-Containers ist nichts,
# worauf man sich verlassen sollte.
WOCHENTAGE = ["Montag", "Dienstag", "Mittwoch", "Donnerstag",
              "Freitag", "Samstag", "Sonntag"]

# Eine Zeile, die nur aus einer Adresse besteht, wird zum Link auf die
# Spielstätte. Eine Zeile "privat" macht den Eintrag anonym.
NUR_URL = re.compile(r"^https?://\S+$")
PRIVAT = re.compile(r"^privat\.?$", re.IGNORECASE)


class Abbruch(Exception):
    """Etwas stimmt nicht — lieber nichts schreiben als etwas Falsches."""


# --------------------------------------------------------------- Kalender

def feed_lesen(quelle: str | None, datei: str | None) -> bytes:
    if datei:
        return Path(datei).read_bytes()
    if not quelle:
        raise Abbruch("Weder CALENDAR_ICS_URL noch CALENDAR_ICS_FILE gesetzt.")
    try:
        with urllib.request.urlopen(quelle, timeout=60) as antwort:
            return antwort.read()
    except Exception as fehler:                      # noqa: BLE001
        raise Abbruch(f"Kalender nicht erreichbar: {fehler}") from fehler


def beschreibung_zerlegen(text: str) -> tuple[list[str], str | None, bool]:
    """Absätze, Link auf die Spielstätte, Privat-Kennzeichen."""
    absaetze, link, privat = [], None, False
    for zeile in (text or "").replace("\r\n", "\n").split("\n"):
        zeile = zeile.strip()
        if not zeile:
            continue
        if PRIVAT.match(zeile):
            privat = True
        elif NUR_URL.match(zeile) and link is None:
            link = zeile
        else:
            absaetze.append(zeile)
    return absaetze, link, privat


def termine_lesen(rohdaten: bytes) -> list[dict]:
    try:
        kalender = Calendar.from_ical(rohdaten)
    except Exception as fehler:                      # noqa: BLE001
        raise Abbruch(f"Kalender ist nicht lesbar: {fehler}") from fehler
    termine, uebersprungen = [], []

    for eintrag in kalender.walk("VEVENT"):
        if str(eintrag.get("STATUS", "")).upper() == "CANCELLED":
            continue
        if eintrag.get("RRULE"):
            uebersprungen.append(str(eintrag.get("SUMMARY", "?")))
            continue

        beginn = eintrag.get("DTSTART")
        if beginn is None:
            continue
        wert = beginn.dt

        if isinstance(wert, datetime):
            # Google liefert mit Zeitzone; ohne Angabe als Ortszeit deuten.
            wert = wert.astimezone(ZONE) if wert.tzinfo else wert.replace(tzinfo=ZONE)
            tag, zeit = wert.date(), f"{wert.hour}.{wert.minute:02d} Uhr"
        else:
            # Ganztägig: keine Uhrzeit anzeigen. Steht die Zeit noch nicht
            # fest, gehört das in die Beschreibung — dann stimmt es immer.
            tag, zeit = wert, None

        absaetze, link, privat = beschreibung_zerlegen(
            str(eintrag.get("DESCRIPTION", "")))
        ort = str(eintrag.get("SUMMARY", "")).strip()
        adresse = str(eintrag.get("LOCATION", "")).strip()

        termine.append({
            "datum": tag.isoformat(),
            "zeit": None if privat else zeit,
            "ort": "private Veranstaltung" if privat else (ort or None),
            "ort_link": None if privat else link,
            "adresse": None if privat else (adresse or None),
            "text": [] if privat else absaetze,
            "privat": privat,
        })

    if uebersprungen:
        print(f"  Hinweis: {len(uebersprungen)} Serientermin(e) übersprungen: "
              + ", ".join(uebersprungen), file=sys.stderr)

    termine.sort(key=lambda t: (t["datum"], t["zeit"] or ""))
    return termine


# ------------------------------------------------------------ Darstellung

def esc(text: str) -> str:
    return html.escape(text, quote=False)


def datum_lang(iso: str, zeit: str | None) -> str:
    tag = date.fromisoformat(iso)
    lang = f"{WOCHENTAGE[tag.weekday()]}, {tag:%d.%m.%Y}"
    return f"{lang} · {zeit}" if zeit else lang


def termin_zeilen(t: dict) -> str:
    ort = esc(t["ort"]) if t["ort"] else ""
    if t.get("ort_link"):
        ort = (f'<a href="{t["ort_link"]}" rel="noopener" target="_blank">'
               f"{ort}</a>")
    zeilen = [
        '  <li class="termin">',
        f'    <p class="termin-datum"><time datetime="{t["datum"]}">'
        f'{esc(datum_lang(t["datum"], t["zeit"]))}</time></p>',
    ]
    if t["ort"]:
        zeilen.append(f'    <p class="termin-ort">{ort}</p>')
    if t.get("adresse"):
        zeilen.append(f'    <p class="termin-adresse">{esc(t["adresse"])}</p>')
    for absatz in t.get("text", []):
        zeilen.append(f'    <p class="termin-text">{esc(absatz)}</p>')
    zeilen.append("  </li>")
    return "\n".join(zeilen)


def termine_rendern(termine: list[dict]) -> str:
    if not termine:
        return ('  <p class="inhalt">Zurzeit stehen keine Termine fest. '
                "Schau bald wieder vorbei.</p>")
    return ('  <ul class="termine inhalt">\n'
            + "\n".join(termin_zeilen(t) for t in termine)
            + "\n  </ul>")


def archiv_rendern(eintraege: list[dict]) -> str:
    """Neueste zuerst, pro Jahr eine Überschrift."""
    sortiert = sorted(eintraege, key=lambda e: e["datum"], reverse=True)
    bloecke, jahr, offen = [], None, []
    for e in sortiert:
        j = e["datum"][:4]
        if j != jahr:
            if offen:
                bloecke.append((jahr, offen))
            jahr, offen = j, []
        tag = date.fromisoformat(e["datum"])
        offen.append(f'      <li><time datetime="{e["datum"]}">{tag:%d.%m.%Y}'
                     f"</time> {esc(e['text'])}</li>")
    if offen:
        bloecke.append((jahr, offen))
    return "\n\n".join(
        f'  <section class="inhalt">\n    <h2 class="archiv-jahr">{j}</h2>\n'
        f'    <ul class="archiv">\n' + "\n".join(zeilen) + "\n    </ul>\n  </section>"
        for j, zeilen in bloecke
    )


def startseite_rendern(termine: list[dict]) -> str:
    if not termine:
        return ('  <p class="mitte weiter"><a href="termine/">Alle Termine '
                "ansehen &rarr;</a></p>")
    n = termine[0]
    wo = "" if n["privat"] else f' &middot; {esc(n["ort"])}' if n["ort"] else ""
    return ('  <p class="mitte weiter"><a href="termine/">Nächster Auftritt: '
            f'{esc(datum_lang(n["datum"], n["zeit"]))}{wo} &rarr;</a></p>')


# ------------------------------------------------------------------ Dateien

def einsetzen(pfad: Path, marke: str, inhalt: str) -> bool:
    text = pfad.read_text(encoding="utf-8")
    muster = re.compile(rf"(<!-- {marke}:START.*?-->\n)(.*?)(\n  <!-- {marke}:END -->)",
                        re.S)
    if not muster.search(text):
        raise Abbruch(f"Marker {marke} fehlt in {pfad}")
    neu = muster.sub(lambda m: m.group(1) + inhalt + m.group(3), text)
    if neu == text:
        return False
    pfad.write_text(neu, encoding="utf-8")
    return True


def json_schreiben(pfad: Path, daten) -> None:
    with pfad.open("w", encoding="utf-8") as fh:
        json.dump(daten, fh, ensure_ascii=False, indent=2)
        fh.write("\n")


# --------------------------------------------------------------------- Lauf

def archiv_text(t: dict) -> str:
    """Eine Zeile fürs Archiv: 'Ort, Stadt' bzw. 'private Veranstaltung'."""
    if t["privat"]:
        return "private Veranstaltung"
    stadt = ""
    if t.get("adresse"):
        letztes = t["adresse"].split("·")[-1].strip()
        stadt = re.sub(r"^\d{5}\s*", "", letztes)
    return f"{t['ort']}, {stadt}" if t["ort"] and stadt else (t["ort"] or "Auftritt")


def main() -> int:
    argumente = argparse.ArgumentParser(description=__doc__)
    argumente.add_argument("--probelauf", action="store_true",
                           help="nur anzeigen, nichts schreiben")
    optionen = argumente.parse_args()

    heute = datetime.now(ZONE).date()
    termine_datei = WURZEL / "daten/termine.json"
    archiv_datei = WURZEL / "daten/archiv.json"

    bisher = json.loads(termine_datei.read_text(encoding="utf-8"))
    archiv = json.loads(archiv_datei.read_text(encoding="utf-8"))

    rohdaten = feed_lesen(os.environ.get("CALENDAR_ICS_URL"),
                          os.environ.get("CALENDAR_ICS_FILE"))
    aus_kalender = termine_lesen(rohdaten)

    # Ein leerer Kalender bei vorhandenem Bestand ist fast immer ein Fehler
    # auf der anderen Seite — dann lieber gar nichts tun.
    if not aus_kalender and bisher:
        raise Abbruch(f"Kalender liefert 0 Termine, zuletzt waren es "
                      f"{len(bisher)}. Es wird nichts geschrieben.")

    kommend = [t for t in aus_kalender if t["datum"] >= heute.isoformat()]

    # Vergangenes aus Kalender und letztem Stand — so geht ein Termin auch
    # dann ins Archiv, wenn der Kalendereintrag inzwischen gelöscht wurde.
    bekannt = {(e["datum"], e["text"]) for e in archiv}
    ergaenzt = 0
    for t in aus_kalender + bisher:
        if t["datum"] >= heute.isoformat():
            continue
        eintrag = {"datum": t["datum"], "text": archiv_text(t)}
        if (eintrag["datum"], eintrag["text"]) not in bekannt:
            archiv.append(eintrag)
            bekannt.add((eintrag["datum"], eintrag["text"]))
            ergaenzt += 1

    print(f"  {len(kommend)} kommende Termine, {ergaenzt} neu im Archiv "
          f"({len(archiv)} gesamt)")

    if optionen.probelauf:
        print(termine_rendern(kommend))
        return 0

    geaendert = [
        einsetzen(WURZEL / "termine/index.html", "GIGS", termine_rendern(kommend)),
        einsetzen(WURZEL / "vergangene-termine/index.html", "ARCHIV",
                  archiv_rendern(archiv)),
        einsetzen(WURZEL / "index.html", "NAECHSTER", startseite_rendern(kommend)),
    ]
    json_schreiben(termine_datei, kommend)
    json_schreiben(archiv_datei, sorted(archiv, key=lambda e: e["datum"], reverse=True))

    print("  Seiten geändert" if any(geaendert) else "  Seiten unverändert")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Abbruch as fehler:
        print(f"Abbruch: {fehler}", file=sys.stderr)
        sys.exit(1)
