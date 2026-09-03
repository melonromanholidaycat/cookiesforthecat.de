# DNS-Umzug: von der alten WordPress-Installation zu GitHub Pages

Stand: die Seite ist fertig und liegt unter
`melonromanholidaycat.github.io/cookiesforthecat.de/`. Die echte Domain zeigt
noch auf den alten Server.

## Vorher aufschreiben

Beim Registrar **alle** bestehenden DNS-Einträge notieren, bevor etwas geändert
wird — vor allem die **MX-Einträge**. `kontakt@cookiesforthecat.de` läuft über
sie. Wer nur die A-Einträge austauscht und die MX dabei verliert, schaltet die
Mailadresse ab, die im Impressum steht.

Auch TXT (SPF, DKIM) gehören dazu, falls vorhanden.

## 1. DNS ändern

Für den Apex (`cookiesforthecat.de`) die vier A-Einträge von GitHub Pages
setzen, dazu die AAAA-Einträge. Für `www` einen CNAME auf
`melonromanholidaycat.github.io.`

Die IP-Adressen nicht aus dieser Datei abschreiben, sondern aus der aktuellen
GitHub-Dokumentation holen ("Managing a custom domain for your GitHub Pages
site"). Sie ändern sich selten, aber sie ändern sich.

MX und TXT unverändert stehen lassen.

## 2. Warten

Bis die Änderung überall angekommen ist. Zwei unabhängige Resolver fragen, nicht
nur den eigenen.

## 3. Erst dann: GitHub Pages

Repository → Settings → Pages → Custom domain → `www.cookiesforthecat.de` →
Save. GitHub legt daraufhin selbst eine Datei `CNAME` im Repository an; die
gehört dort hin und darf nicht gelöscht werden.

Danach "Enforce HTTPS" ankreuzen, sobald die Option nicht mehr ausgegraut ist —
das dauert, bis das Zertifikat ausgestellt ist.

**Reihenfolge einhalten.** Wer die Domain in Pages einträgt, bevor DNS zeigt,
bekommt eine Fehlermeldung und muss von vorn anfangen.

## 4. Prüfen

- `www.cookiesforthecat.de` und `cookiesforthecat.de` laden beide die neue Seite
- HTTPS greift, keine Zertifikatswarnung
- eine Test-Mail an `kontakt@cookiesforthecat.de` kommt an
- der Abo-Link auf der Termine-Seite funktioniert jetzt: er zeigt auf
  `webcal://www.cookiesforthecat.de/termine/kalender.ics` und war bis hierhin
  der einzige tote Link der Seite
- die 404-Seite: eine erfundene Adresse aufrufen, das Logo muss geladen werden

## 5. Danach

- Der alte WordPress-Server kann abgeschaltet werden. Vorher sicherstellen, dass
  nichts mehr gebraucht wird — er war zuletzt die einzige Quelle für einige
  Original-Grafiken.
- Issue über das Aufräumen der Git-Historie wird dann fällig.
