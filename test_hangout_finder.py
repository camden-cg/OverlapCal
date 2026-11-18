import unittest
from datetime import date, datetime, time

from hangout_finder import (
    build_report,
    grid_selection_to_window,
    make_date_window,
    parse_availability_time,
    parse_calendar_date,
    parse_clock,
)


class DateWindowTests(unittest.TestCase):
    def test_daypart_choices_map_to_intuitive_start_times(self):
        self.assertEqual(parse_availability_time("Morning (6:00 AM)"), time(6))
        self.assertEqual(parse_availability_time("Evening (5:00 PM)"), time(17))
        self.assertEqual(parse_availability_time("Night (8:00 PM)"), time(20))

    def test_natural_time_input_accepts_am_pm_and_day_words(self):
        self.assertEqual(parse_availability_time("8pm"), time(20))
        self.assertEqual(parse_availability_time("night"), time(20))
        self.assertEqual(parse_availability_time("noon"), time(12))
        self.assertEqual(parse_clock("midnight"), time(0))

    def test_calendar_drag_selects_across_days(self):
        window = grid_selection_to_window(
            date(2026, 11, 16),
            (0, 20),
            (2, 30),
        )
        self.assertEqual(
            window,
            (datetime(2026, 11, 16, 10), datetime(2026, 11, 18, 15, 30)),
        )

    def test_calendar_drag_works_in_either_direction(self):
        forward = grid_selection_to_window(date(2026, 11, 16), (0, 20), (2, 30))
        backward = grid_selection_to_window(date(2026, 11, 16), (2, 30), (0, 20))
        self.assertEqual(forward, backward)

    def test_calendar_drag_supports_day_and_three_day_views(self):
        day = grid_selection_to_window(date(2026, 11, 18), (0, 20), (0, 22), day_count=1)
        three_days = grid_selection_to_window(
            date(2026, 11, 18), (0, 20), (2, 30), day_count=3
        )
        self.assertEqual(day, (datetime(2026, 11, 18, 10), datetime(2026, 11, 18, 11, 30)))
        self.assertEqual(
            three_days,
            (datetime(2026, 11, 18, 10), datetime(2026, 11, 20, 15, 30)),
        )

    def test_last_slot_ends_at_midnight_on_the_next_day(self):
        window = grid_selection_to_window(date(2026, 11, 16), (6, 47), (6, 47))
        self.assertEqual(
            window,
            (datetime(2026, 11, 22, 23, 30), datetime(2026, 11, 23)),
        )

    def test_range_can_span_multiple_days(self):
        window = make_date_window(
            date(2026, 11, 20),
            time(20),
            date(2026, 11, 22),
            time(9),
        )
        self.assertEqual(
            window,
            (datetime(2026, 11, 20, 20), datetime(2026, 11, 22, 9)),
        )

    def test_date_input_accepts_iso_and_us_formats(self):
        self.assertEqual(parse_calendar_date("2026-11-18"), date(2026, 11, 18))
        self.assertEqual(parse_calendar_date("11/18/2026"), date(2026, 11, 18))

    def test_end_must_be_after_start(self):
        with self.assertRaisesRegex(ValueError, "later than the start"):
            make_date_window(
                date(2026, 11, 20),
                time(20),
                date(2026, 11, 20),
                time(19),
            )

    def test_report_splits_shared_overlap_by_date(self):
        people = [
            (
                "Alex",
                [
                    make_date_window(
                        date(2026, 11, 20), time(20), date(2026, 11, 22), time(9)
                    )
                ],
            ),
            (
                "Sam",
                [
                    make_date_window(
                        date(2026, 11, 21), time(10), date(2026, 11, 22), time(11)
                    )
                ],
            ),
        ]

        report = build_report(people)

        self.assertIn("Saturday, November 21, 2026", report)
        self.assertIn("Everyone overlaps: 10:00-00:00", report)
        self.assertIn("Sunday, November 22, 2026", report)
        self.assertIn("Everyone overlaps: 00:00-09:00", report)


if __name__ == "__main__":
    unittest.main()
