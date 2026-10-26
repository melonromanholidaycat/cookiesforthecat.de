"""Gig rendering and calendar-data regression checks.

Run with: python -m unittest discover -s skripte
"""

from copy import deepcopy
from datetime import date, datetime
import unittest

from icalendar import Event

import termine


class AddressFormattingTests(unittest.TestCase):
    def gig(self, address, private=False):
        event = Event()
        event.add("SUMMARY", "Test venue")
        event.add("LOCATION", address)
        if private:
            event.add("DESCRIPTION", "privat")
        return termine.one_gig(event, date(2026, 12, 20))

    def test_separator_variants_and_trailing_country(self):
        for separator in [", ", " · ", " • ", "; ", "\n", "\r\n"]:
            with self.subTest(separator=separator):
                address = separator.join(["Moorfuhrtweg 9", "22301 Hamburg",
                                          "Deutschland"])
                gig = self.gig(address)
                output = termine.gig_lines(gig, "test")
                self.assertIn('class="gig-address">Moorfuhrtweg 9 · '
                              '22301 Hamburg</p>', output)

    def test_foreign_country_and_street_punctuation_survive(self):
        for address, expected in [
            ("Piazza Unità 1, 42017 Novellara, Italien",
             "Piazza Unità 1 · 42017 Novellara · Italien"),
            ("Dr.-Weg 1, 23552 Lübeck Deutschland",
             "Dr.-Weg 1 · 23552 Lübeck"),
            ("  Weg  1 , • 23552 Lübeck ; deutschland. ",
             "Weg 1 · 23552 Lübeck"),
            ("Deutschlandstraße 1 · 23552 Lübeck",
             "Deutschlandstraße 1 · 23552 Lübeck"),
        ]:
            with self.subTest(address=address):
                self.assertEqual(termine.format_address(address), expected)
                self.assertEqual(termine.format_address(expected), expected)

    def test_escaping_and_empty_address(self):
        output = termine.gig_lines(
            self.gig("Weg &lt;1&gt; &amp; Hof, Hamburg"), "test")
        self.assertIn("Weg &lt;1&gt; &amp; Hof · Hamburg", output)
        for address in ["", " , · • ; \n", "Deutschland"]:
            with self.subTest(address=address):
                self.assertNotIn('class="gig-address"',
                                 termine.gig_lines(self.gig(address), "test"))

    def test_display_does_not_change_source_downloads_or_archive(self):
        gig = self.gig("Piazza Unità 1 · Novellara, Italien")
        original = deepcopy(gig)
        archive = termine.archive_text(gig)
        event = termine.vevent(gig, "test", standalone=True).to_ical()
        termine.gig_lines(gig, "test")
        self.assertEqual(gig, original)
        self.assertEqual(termine.archive_text(gig), archive)
        self.assertEqual(archive, "Test venue, Novellara, Italien")
        self.assertEqual(termine.vevent(gig, "test", standalone=True).to_ical(),
                         event)

    def test_private_locations_remain_hidden(self):
        gig = self.gig("Secret address, 23552 Lübeck, Deutschland", private=True)
        self.assertIsNone(gig["adresse"])
        self.assertNotIn("Secret", termine.gig_lines(gig, "test"))
        self.assertNotIn("Secret", str(termine.vevent(gig, "test", True)))
        self.assertEqual(termine.archive_text(gig), "private Veranstaltung")


class NextGigTests(unittest.TestCase):
    def gig(self, day="2026-10-30", time=None, private=False, venue="Public gig"):
        return {"datum": day, "zeit": time, "privat": private,
                "ort": "private Veranstaltung" if private else venue}

    def render(self, gigs, now="2026-10-26T12:00:00+01:00"):
        return termine.render_next(gigs, datetime.fromisoformat(now))

    def test_public_gig_wins_on_same_day(self):
        private = self.gig(private=True)
        public = self.gig(time="19:00", venue="Candlelight Shopping")
        for gigs in [[private, public], [public, private]]:
            with self.subTest(gigs=gigs):
                before = deepcopy(gigs)
                output = self.render(gigs)
                self.assertIn("Candlelight Shopping", output)
                self.assertIn("19:00 Uhr", output)
                self.assertIn('href="termine/"', output)
                self.assertEqual(gigs, before)

    def test_multiple_public_gigs_keep_chronological_order(self):
        output = self.render([self.gig(private=True),
                              self.gig(time="14:00", venue="First public gig"),
                              self.gig(time="19:00", venue="Later public gig")])
        self.assertIn("First public gig", output)
        self.assertNotIn("Later public gig", output)

    def test_private_only_day_is_not_skipped(self):
        output = self.render([self.gig(private=True),
                              self.gig(day="2026-10-31", time="19:00")])
        self.assertIn("30.10.2026", output)
        self.assertNotIn("31.10.2026", output)
        self.assertNotIn("Public gig", output)
        self.assertNotIn("private Veranstaltung", output)

    def test_ended_public_gig_is_not_promoted(self):
        gigs = [self.gig(private=True), self.gig(time="14:00")]
        self.assertIn("Public gig", self.render(gigs, "2026-10-30T15:59:00+01:00"))
        output = self.render(gigs, "2026-10-30T16:00:00+01:00")
        self.assertIn("30.10.2026", output)
        self.assertNotIn("Public gig", output)

    def test_later_public_gig_replaces_ended_public_gig(self):
        output = self.render([self.gig(private=True),
                              self.gig(time="14:00", venue="Ended gig"),
                              self.gig(time="19:00", venue="Evening gig")],
                             "2026-10-30T16:00:00+01:00")
        self.assertIn("Evening gig", output)
        self.assertNotIn("Ended gig", output)

    def test_all_day_public_gig_expires_at_local_midnight(self):
        gigs = [self.gig(private=True), self.gig(),
                self.gig(day="2026-10-31", time="19:00", venue="Tomorrow")]
        self.assertIn("Public gig", self.render(gigs, "2026-10-30T22:59:00+00:00"))
        output = self.render(gigs, "2026-10-30T23:00:00+00:00")
        self.assertIn("Tomorrow", output)
        self.assertNotIn("Public gig", output)

    def test_no_remaining_gigs_keep_fallback_link(self):
        for gigs in [[], [self.gig(time="14:00")]]:
            with self.subTest(gigs=gigs):
                output = self.render(gigs, "2026-10-31T12:00:00+01:00")
                self.assertIn('href="termine/">Alle Termine ansehen', output)
                self.assertNotIn("Nächster Auftritt", output)


if __name__ == "__main__":
    unittest.main()
