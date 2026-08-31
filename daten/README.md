# Auftritte eintragen

Die Termine auf der Website kommen aus dem Google-Kalender **„Auftritte“**.
Wer dort einen Termin anlegt, ändert oder löscht, ändert damit die Website.
Es dauert höchstens eine Stunde, bis die Änderung online ist.

Sonst ist nichts zu tun — kein Login auf der Website, keine Datei, nichts.

## Einen Auftritt anlegen

Wichtig: **immer im Kalender „Auftritte“** speichern, nicht im eigenen. Alles,
was in diesem Kalender steht, steht öffentlich auf der Website.

| Feld im Kalender | Steht später auf der Website |
| --- | --- |
| **Titel** | der Name der Location, z. B. `Finnegan Irish Pub` |
| **Ort** | die Adresse, z. B. `Mengstraße 42 · 23552 Lübeck` |
| **Beschreibung** | der Text unter dem Termin |
| **Uhrzeit** | wird angezeigt, z. B. `21.00 Uhr` |

Die **Endzeit** wird nie angezeigt. Sie darf also ruhig ungenau sein.

Steht die Uhrzeit noch nicht fest, den Termin als **ganztägig** eintragen —
dann erscheint nur das Datum. Wenn ihr dazuschreiben wollt, dass die Zeit noch
kommt, schreibt das einfach in die Beschreibung.

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
der Website erscheint ausschließlich `private Veranstaltung`. Ihr könnt also
ruhig den Namen des Kunden als Titel nehmen, damit ihr selbst wisst, worum es
geht.

## Ändern und Absagen

Termin im Kalender ändern — die Website zieht nach. Termin löschen oder im
Kalender auf „abgesagt“ setzen — er verschwindet von der Website.

Vergangene Auftritte wandern von selbst in die Liste **Vergangene Termine** und
bleiben dort dauerhaft stehen, auch wenn ihr den Kalendereintrag später
aufräumt.

## Am Handy

Die Schnelleingabe zeigt Ort und Beschreibung nicht an. Dafür beim Anlegen auf
**„Weitere Optionen“** tippen — sonst entsteht ein Termin, bei dem auf der
Website nur der Name steht, ohne Adresse und Text.

---

## Für die technische Seite

`termine.json` ist der Stand der kommenden Auftritte beim letzten Abgleich,
`archiv.json` die vollständige Vergangenheit. Das Archiv wird nur ergänzt,
nie gekürzt.

Sollte der Kalender einmal wegfallen, sind beide Dateien weiterhin da und von
Hand zu pflegen; `skripte/termine.py` erzeugt die Seiten daraus.
