"""Address display and calendar-data regression checks.

Run with: python -m unittest discover -s skripte
"""

from copy import deepcopy
from datetime import date
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


if __name__ == "__main__":
    unittest.main()
