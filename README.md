# cookiesforthecat.de

Static website for **Cookies For The Cat**, an acoustic duo from northern
Germany. Replaces a self-hosted WordPress install.

Working on this repository? Read [AGENTS.md](AGENTS.md) first — it holds the
rules that are easy to break without noticing.

## How it is built

Plain HTML and CSS. No build step, no JavaScript, no dependencies. What sits in
`main` is byte-for-byte what gets served, so any page can be edited in the
GitHub web editor and is live about thirty seconds later.

```
index.html                Home
ueber-uns/                About
termine/                  Upcoming gigs        — generated, see below
vergangene-termine/       Archive              — generated, see below
kontakt/                  Contact
veranstalter/             Press kit for venues
impressum/                Legally required imprint
datenschutz/              Privacy policy
assets/                   style.css, fonts, images, downloads
daten/                    gig data + the German note for whoever keeps the calendar
skripte/                  the calendar sync
```

## Gig dates

The gig list is not edited here. It comes from a shared Google calendar:
`skripte/termine.py` runs hourly, writes the entries into the marked regions of
`termine/index.html`, `vergangene-termine/index.html` and `index.html`, and
commits the result.

`daten/README.md` explains the calendar side, in German, for the band member
who maintains it.

## Deployment

GitHub Pages, deploy from branch `main`, directory `/`. A merge to `main` is a
deploy. There is no CI to configure beyond the calendar sync.

## Editing

Header and footer are identical on every page. Changing them means changing
every file — see AGENTS.md before you do.

## Rights

Text, photographs, posters and other content belong to Cookies For The Cat and
are not released for reuse.
