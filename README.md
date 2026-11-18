# Hangout Time Finder

A small Tkinter app for comparing date-specific availability and finding when
everyone can meet.

## Requirements

- Python 3.10 or newer
- Tkinter, which is included with most Python installations

The app uses only Python's standard library; no packages need to be installed.

## Run on macOS

Double-click **Hangout Time Finder.app** in Finder. It finds an installed
Python 3 with Tkinter and opens the app without using Terminal.

## Run from a terminal

From this folder, run:

```bash
python3 hangout_finder.py
```

Choose Day, 3 days, Week, Month, or Year from the view menu. In Day, 3-day,
and Week views, drag across 30-minute time slots. In Month and Year views,
drag across dates to select a day range. After releasing, enter a name and
adjust either date and time before saving. Dates can be typed or selected
from the date picker.

Choose Morning, Afternoon, Evening, or Night for either endpoint, or type a
time such as `8pm`, `noon`, or `20:30`. Use the same name to add more ranges
for that person. The people list shows their full ranges, and the shared
report updates as ranges are added.
