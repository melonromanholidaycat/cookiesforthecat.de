# Working on this repository

Rules for anyone changing this site, human or otherwise. Most of them exist
because breaking them is easy and the damage is not obvious from the diff.

## Language

**Code is English. Content is German.**

- Comments, docstrings, commit messages, workflow step names, CSS class names,
  variable and function names: English.
- Page text, the note in `daten/README.md`, and anything a visitor or a band
  member reads: German.
- **The JSON keys in `daten/` stay German** (`datum`, `ort`, `adresse`,
  `privat`). Those files are the documented fallback: if the calendar route
  ever falls away, a German-speaking maintainer edits them by hand. The field
  names are for that reader, so they are in that reader's language. This is
  deliberate, not drift.

## The site is static, and stays that way

- **No build step.** The committed HTML is exactly what is served. Anyone can
  fix a typo in the GitHub web editor and it is live in thirty seconds. Do not
  introduce a generator that makes the repository the source and the site an
  artefact.
- **No JavaScript.** The navigation wraps instead of collapsing into a
  hamburger for this reason.
- **No third-party requests.** There are no webfonts at all — headings use
  Georgia, which every reader already has — social links are links rather than
  embeds, and there is no analytics. The Datenschutzerklärung says
  so in as many words, so breaking this makes a legal page untrue. Anything
  that needs an external service belongs in a workflow, not in the page.

## Links must be relative

Until the custom domain is connected the site lives under
`melonromanholidaycat.github.io/cookiesforthecat.de/`, where root-relative
paths 404. Use `../termine/`, never `/termine/`. The 404 page is one
exception, since it is served from every depth.

The subscribe link on the Termine page is the other: a `webcal://` URL cannot
be relative, so it names `www.cookiesforthecat.de` and starts working when DNS
moves off the VPS. Every page's `canonical` and `og:url` already assume that
domain, so this adds no new assumption — but it is the only link on the site
that does not work today.

## The centred column

`.content` (650px) and `.wide` (1000px) centre themselves with automatic left
and right margins. Any rule that later sets `margin: 0` on the same element
undoes that, and the block drifts to the left edge of the page while everything
around it stays centred.

This has now happened twice — the gig list, then the social row on the contact
page — and in both cases nothing revealed it until something nearby gained an
edge to be compared against. Write `margin: 0 auto`.

## Generated regions

Three files contain regions written by `skripte/termine.py`:

```
termine/index.html              <!-- GIGS:START -->    … <!-- GIGS:END -->
vergangene-termine/index.html   <!-- ARCHIVE:START --> … <!-- ARCHIVE:END -->
index.html                      <!-- NEXT:START -->    … <!-- NEXT:END -->
```

Editing inside them is pointless — the next hourly run overwrites it. Edit the
calendar, or the script.

The same script owns two paths outright:

```
termine/auftritte.ics    the feed people subscribe to
termine/kalender/*.ics   one file per gig, for a single download
```

Anything in `termine/kalender/` that does not belong to a current gig is
deleted on the next run — that is the point, so a cancelled gig cannot leave a
downloadable file behind. Nothing hand-written survives there.

Those files are generated from `daten/termine.json`, never from the calendar
feed directly. The feed carries the real titles of private bookings, which the
band was told they may use; the sanitising happens on the way into the JSON, so
everything downstream of it is safe to publish and nothing upstream is.

`daten/archiv.json` is **append-only**. The gig history is meant to be
permanent, and nothing should ever remove from it.

## Shared header and footer

Identical on every page, byte for byte. There is no templating, so changing
them means changing all nine files consistently. Check with a diff afterwards
rather than trusting that you got them all.

## Type and colour

- **Every `font-size` is a token** from the scale in `:root`, or a `clamp()`
  between two of them. No free-standing values — the last two produced a footer
  where the social links were smaller than the legal links on a phone and twice
  their size on a desktop.
- **Every text/background pair clears WCAG AA (4.5:1).** Current values:
  text 13.79:1, links 5.48:1, muted 5.33:1. Check before changing a colour.
- **Focus must be more visible than the resting state, not less.** An earlier
  version removed a link's underline on focus, which is backwards.

## Images

- Always set `width` and `height`, so the page does not reflow while loading.
- Serve at twice the display size, in WebP, for retina screens.
- Do not lazy-load anything above the fold.
- Check bytes per pixel when adding a photo. Healthy is 0.2–0.3; the originals
  inherited from WordPress ran as high as 10.6, and one 436×614 thumbnail
  weighed 2.3 MB.

## Deliberately left alone

- **The press kit** in `assets/files/` — full-resolution photos and fillable
  poster PDFs. They are download targets, not page weight, and full resolution
  is the point. The three poster JPEGs each carry a 1.83 MB embedded CMYK press
  profile; stripping it would save 5.5 MB and change no pixels, but it has not
  been done because the owner decided to leave these files untouched.
- **The old WordPress install** is still serving the real domain. It is also
  the only remaining source of some original artwork, so do not treat the DNS
  switch as routine.

## Workflow

Changes go through a pull request against `main`. The gig sync is the one thing
that commits directly, by design: a cancelled gig should not wait for a review.
