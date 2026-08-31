# Working on this repository

Rules for anyone changing this site, human or otherwise. Most of them exist
because breaking them is easy and the damage is not obvious from the diff.

## Language

**Code is English. Content is German.**

- Comments, docstrings, commit messages, workflow step names, variable and
  function names: English.
- Page text, the note in `daten/README.md`, and anything a visitor or a band
  member reads: German.
- **CSS class names and JSON data keys stay German** (`termin-ort`, `datum`,
  `adresse`). They describe German content and appear in the markup, so they
  match the pages they style. Renaming them would churn every HTML file for no
  gain. This is deliberate, not drift.

## The site is static, and stays that way

- **No build step.** The committed HTML is exactly what is served. Anyone can
  fix a typo in the GitHub web editor and it is live in thirty seconds. Do not
  introduce a generator that makes the repository the source and the site an
  artefact.
- **No JavaScript.** The navigation wraps instead of collapsing into a
  hamburger for this reason.
- **No third-party requests.** Fonts are self-hosted, social links are links
  rather than embeds, and there is no analytics. The Datenschutzerklärung says
  so in as many words, so breaking this makes a legal page untrue. Anything
  that needs an external service belongs in a workflow, not in the page.

## Links must be relative

Until the custom domain is connected the site lives under
`melonromanholidaycat.github.io/cookiesforthecat.de/`, where root-relative
paths 404. Use `../termine/`, never `/termine/`. The 404 page is the one
exception, since it is served from every depth.

## Generated regions

Three files contain regions written by `skripte/termine.py`:

```
termine/index.html              <!-- GIGS:START -->    … <!-- GIGS:END -->
vergangene-termine/index.html   <!-- ARCHIVE:START --> … <!-- ARCHIVE:END -->
index.html                      <!-- NEXT:START -->    … <!-- NEXT:END -->
```

Editing inside them is pointless — the next hourly run overwrites it. Edit the
calendar, or the script.

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
