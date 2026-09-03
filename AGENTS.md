# Working on this repository

Rules for anyone changing this site, human or otherwise. Most of them exist
because breaking them is easy and the damage is not obvious from the diff.

## Language

**Code is English. Content is German.**

- Comments, docstrings, commit messages, pull request titles and
  descriptions, workflow step names, CSS class names, variable and function
  names: English. Writing about German page content is not a reason to switch.
- **Keep comments short.** A line or two saying what a rule is for. Not the
  history of the change, not what the value used to be. The same goes for
  commit messages and pull requests.
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
moves off the VPS. It is the only link on the site that does not work today.

## The centred column

`.content` (650px) and `.wide` (1000px) centre themselves with automatic left
and right margins. Any rule that later sets `margin: 0` on the same element
undoes that, and the block drifts to the left edge of the page while everything
around it stays centred.

It has happened twice, and neither was visible until something nearby gained
an edge to compare against. Write `margin: 0 auto`.

## Generated regions

Three files contain regions written by `skripte/termine.py`:

```
termine/index.html              <!-- GIGS:START -->     … <!-- GIGS:END -->
termine/index.html              <!-- EVENTS:START -->   … <!-- EVENTS:END -->
vergangene-termine/index.html   <!-- ARCHIVE:START -->  … <!-- ARCHIVE:END -->
index.html                      <!-- NEXT:START -->     … <!-- NEXT:END -->
```

The EVENTS region is schema.org markup for the gigs. `sitemap.xml` gets a
`lastmod` on every page: today for the ones a run changes, and for the rest the
day git last recorded a change to the file. So a hand-edited page needs no
follow-up here. It does mean the workflow must keep `fetch-depth: 0` — a
shallow clone reports its tip commit as having introduced every file, which
would date all eight pages today. The script checks for that and leaves the
sitemap alone rather than filling it with a date it made up.

NEXT is the only region that changes without the calendar changing: a gig
drops off the home page `LENGTH` after it starts — the two hours the feed
gives every entry — while Termine keeps it for the rest of the day. So two
runs an hour apart can differ on an unchanged calendar, and the home page
follows a gig ending within the hour rather than at the minute. That is the
cost of having no JavaScript, and it is the right trade.

Its spacing is the document's own baseline rather than the site's scale, so
those rules are in `em` of the list — the ratios carry between screen and
paper, and only the base size changes. `.document > * + *` switches off the
`main > * + *` block spacing that would otherwise break it.

Editing inside them is pointless — the next hourly run overwrites it. Edit the
calendar, or the script.

The same script owns two paths outright:

```
termine/kalender.ics    the feed people subscribe to
termine/kalender/*.ics   one file per gig, for a single download
```

Anything in `termine/kalender/` that does not belong to a current gig is
deleted on the next run — that is the point, so a cancelled gig cannot leave a
downloadable file behind. Nothing hand-written survives there.

Generated from `daten/termine.json`, never from the calendar feed: that feed
carries the real titles of private bookings. Sanitising happens on the way into
the JSON, so everything downstream of it is safe to publish.

`daten/archiv.json` is **append-only**. The gig history is meant to be
permanent, and nothing should ever remove from it.

**29.08.2025 carries `private Veranstaltung` twice, and that is correct** —
two private bookings on one day. It looks exactly like a duplicate and a
consistency check will flag it; the band has confirmed it. Three other dates
carry two entries too (13.09.2025, 03.09.2022, 04.09.2021), each with two
different venues. Leave all four alone.

## Print

`@media print` at the end of the stylesheet applies to every page, but Termine
is the one anyone prints: a venue wants the dates on paper. Navigation, the
footer, the add-to-calendar links and the gig notes come off, the page box
becomes the measure, and the wordmark sits centred at the top of the sheet.
Twelve gigs come out as two A4 pages.

**`.no-print` marks prose that only makes sense on screen** — the two intro
paragraphs on Termine and on Vergangene Termine, and the in-page link between
them. It is applied one element at a time on purpose: `.page-intro` carries
real text on Veranstalter and on the 404 page, so a blanket rule would delete
it there.

This is the one place where a `font-size` is not a token and a length is not
`rem`. A sheet of paper has no viewport, so the fluid spacing that measures
against one is replaced with `pt`, and `@page` carries the margins. It sets no
`size`, so a Letter sheet still works.

The band once handed out a printed list of the year, and this site briefly
carried a page reproducing it. It was dropped: three pages saying the same
thing is worse for a reader than one, and a second list of gigs is one more
thing to keep in step. If it ever comes back, the history has it — the layout
was measured off the original PDF rather than guessed.

## Shared header and footer

Identical on every page, byte for byte. There is no templating, so changing
them means changing all nine files consistently. Check with a diff afterwards
rather than trusting that you got them all.

## Type and colour

- **Every `font-size` is a token** from the scale in `:root`, or a `clamp()`
  between two of them. No free-standing values.
- **`--color-gold` is decoration, never text.** It is a rule, a bar, a tint.
  At 3.6:1 on the paper it would fail as body text, and that is fine as long
  as nothing sets it as a `color`.
- **Every text/background pair clears WCAG AA (4.5:1).** Current values:
  text 13.79:1, links 5.48:1, muted 5.33:1. Check before changing a colour.
- **Focus must be more visible than the resting state, not less.**

## Spacing

- **Every margin, padding and gap is a token**, or a `clamp()` between two of
  them. The scale is `--space-hair` 4px, `--space-tight` 8px, `--space-snug`
  12px, `--space-block` 24px, then the fluid `--space-loose`, `--space-section`
  and `--space-large`. Names describe size, not the thing they happen to be
  used on.
- **Everything lands on a 4px grid.** If a value needs to sit between two
  tokens, the answer is usually the nearer token, not a new number. There were
  three ad-hoc values doing one job (2.4px, 6.4px, 9.6px) before this rule.
- **A breakpoint is a measured number, not a round one.** Both of the ones
  in the footer and on Kontakt were guesses, and both were wrong by enough
  to wrap a row of links. Measure where the content stops fitting, leave a
  little slack, and put the arithmetic in the comment. Never let a
  `max-width` and a `min-width` query share a number: both match on it.
- Lengths are `rem`, not `px`. The exceptions are hairline borders and the
  fixed widths of the wordmark and the footer rule.

## Images

- Always set `width` and `height`, so the page does not reflow while loading.
- Serve at twice the display size, in WebP, for retina screens — **unless the
  image decides LCP**. The home page flyer stays at 1x on purpose: 2x costs
  124 KB and takes LCP from 776ms to 1432ms on slow 4G, on a page that is
  65 KB in total. Measured 2026-09-02. Re-measure before overturning it.
- **The alt text describes what is in the picture**, not what you remember
  putting there. That flyer showed two guitars against a wall while its alt
  named the two band members. Where the picture is mostly words, the alt
  carries the words.
- Do not lazy-load anything above the fold.
- Check bytes per pixel when adding a photo. Healthy is 0.2–0.3.

## Icons

`assets/img/icon-512.webp` is the master, carried over from the old install; the
favicon, the touch icon and `icon-192.webp` are all cut from it. Nothing in the
repository can replace it, so do not delete it in a clean-up. `site.webmanifest`
points at the two icon files and gives Android a real icon when someone adds the
site to their home screen.

## Deliberately left alone

- **The press kit** in `assets/files/` — full-resolution photos and fillable
  poster PDFs. Download targets, not page weight. The three poster JPEGs carry
  a 1.83 MB embedded CMYK profile each; stripping it would save 5.5 MB and
  change no pixels, but the owner has left these files alone.
- **The UTF-8 BOM on the two `.txt` files** in the same folder. Pages serves
  them as `charset=utf-8`, so a browser is right either way — the BOM is for
  the copy a promoter downloads and opens in an editor, where no header is
  left to read and the app has to guess. Without it, a device whose default is
  not UTF-8 shows `Grundfläche` as `GrundflÃ¤che`; that is what a venue
  reported. Keep it if you re-save either file.
- **The old WordPress install** is still serving the real domain. It is also
  the only remaining source of some original artwork, so do not treat the DNS
  switch as routine.

## Workflow

Changes go through a pull request against `main`. The gig sync is the one thing
that commits directly, by design: a cancelled gig should not wait for a review.

**A push to `main` deploys the site on its own**, including a push made by a
workflow's own `GITHUB_TOKEN`. Measured 2026-09-02 with a probe that pushed as
the token and called no API: the build appeared 11 seconds later. Nothing needs
to ask Pages for a build, and an earlier version of `termine.yml` that did was
producing two builds per sync.

**Scheduled workflows stop after 60 days without repository activity.** GitHub
applies this to public repositories, which this is. Two things follow:

- The hourly sync commits as `github-actions[bot]`. Do not assume that resets
  the clock — bot activity generally does not count. A human push, merge or
  issue does.
- If it happens the site keeps serving; it only stops updating. Re-enable the
  workflow in the Actions tab, one button. A gig you have played still sitting
  under Termine instead of the archive is the symptom to watch for.
