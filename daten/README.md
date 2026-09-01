# Auftritte eintragen

Die Termine auf der Website kommen aus dem Google-Kalender.
Wer dort einen Termin anlegt, ändert oder löscht, ändert damit die Website.
Es dauert höchstens eine Stunde, bis die Änderung online ist. Sonst ist nichts zu tun.

## Einen Auftritt anlegen

| Feld im Kalender | Steht später auf der Website |
| --- | --- |
| **Titel** | der Name der Location, z. B. `Finnegan Irish Pub` |
| **Ort** | die Adresse, z. B. `Mengstraße 42 · 23552 Lübeck` |
| **Beschreibung** | der Text unter dem Termin |
| **Uhrzeit** | wird angezeigt, z. B. `21.00 Uhr` |

Die **Endzeit** wird nie angezeigt. Sie darf also ruhig ungenau sein.

Steht die Uhrzeit noch nicht fest, den Termin als **ganztägig** eintragen —
dann erscheint nur das Datum.

### Link zur Location

Soll der Name der Location auf deren Website verlinken: die Adresse in eine
**eigene Zeile in der Beschreibung** schreiben, sonst nichts in dieser Zeile.

```
https://www.finnegan.de/

Unser jährliches Konzert im Finnegan. Die Musik spielt im Keller.
```

### Private Veranstaltungen

Bei geschlossenen Gesellschaften soll auf der Website nur das Datum stehen und
sonst nichts. Dafür in die Beschreibung eine Zeile mit nur diesem Wort setzen:

```
privat
```

Dann ist es egal, was im Titel, im Ort und im Rest der Beschreibung steht — auf
der Website erscheint ausschließlich `private Veranstaltung`.

## Regelmäßige Auftritte

Eine Serie („jeden Montag“) darf im Kalender angelegt werden. Auf der Website
erscheinen die nächsten Termine daraus, höchstens zwölf und höchstens ein
halbes Jahr im Voraus. Einzelne Termine einer Serie dürfen verschoben oder
gelöscht werden — die Website folgt.

Für einen Auftritt über mehrere Tage bitte pro Tag einen Termin anlegen.

## Ändern und Absagen

Termin im Kalender ändern — die Website zieht nach. Termin löschen oder im
Kalender auf „abgesagt“ setzen — er verschwindet von der Website.

Vergangene Auftritte wandern von selbst in die Liste **Vergangene Termine** und
bleiben dort dauerhaft stehen, auch wenn der Eintrag im Google-Kalender verschwindet.

## Kalender-Abo

Auf der Website kann jeder alle Termine abonnieren oder einen einzelnen Termin
in den eigenen Kalender laden. Beides entsteht automatisch aus diesem Kalender.

Veröffentlicht wird dabei genau das, was auch auf der Website steht — bei einer
privaten Veranstaltung also nur das Datum und die Worte „private
Veranstaltung“.

Jeder Auftritt bekommt im Abo zwei Stunden. Die Endzeit aus dem Kalender wird
also weiterhin nirgends veröffentlicht.

---

## Für die technische Seite

`termine.json` ist der Stand der kommenden Auftritte beim letzten Abgleich,
`archiv.json` die vollständige Vergangenheit. Das Archiv wird nur ergänzt,
nie gekürzt.

Sollte der Kalender einmal wegfallen, sind beide Dateien weiterhin da und von
Hand zu pflegen; `skripte/termine.py` erzeugt die Seiten daraus. Die Uhrzeit
steht dort als `"zeit": "19:00"`; die Schreibweise `19.00 Uhr` entsteht erst
beim Erzeugen der Seite.

`termine/kalender.ics` und die Dateien in `termine/kalender/` entstehen im
selben Lauf und gehören dem Skript — von Hand geändert werden sie beim nächsten
Lauf überschrieben oder gelöscht.
