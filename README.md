# cookiesforthecat.de

Statische Website für **Cookies For The Cat**, ein Akustik-Duo aus
Norddeutschland.

## Aufbau

Reines HTML und CSS. Kein Build-Schritt, kein JavaScript, keine
Abhängigkeiten. Was in `main` liegt, wird genau so ausgeliefert.

```
index.html                Startseite
ueber-uns/                Über uns
termine/                  Kommende Termine
vergangene-termine/       Archiv
kontakt/                  Kontakt
veranstalter/             Pressematerial für Veranstalter
impressum/                Impressum
datenschutz/              Datenschutzerklärung
assets/                   style.css, Schriften, Bilder, Downloads
```

## Deployment

GitHub Pages, deploy-from-branch: `main`, Verzeichnis `/` (root).
Ein Merge nach `main` ist ein Deploy. Es gibt keine CI-Konfiguration.

## Bearbeiten

Jede Seite lässt sich direkt in der GitHub-Weboberfläche bearbeiten; die
Änderung ist nach etwa 30 Sekunden live.

Kopf- und Fußzeile sind auf allen Seiten identisch. Wer sie ändert,
muss die Änderung in jeder Datei nachziehen.

## Rechte

Texte, Fotos, Plakate und sonstige Inhalte sind Eigentum von
Cookies For The Cat und nicht zur Weiterverwendung freigegeben.
