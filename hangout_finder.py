"""Compare date-specific availability for a group of people."""

import re
from datetime import date, datetime, time, timedelta
from typing import Callable

DateWindow = tuple[datetime, datetime]

WEEKDAYS = {
    name.lower(): index for index, name in enumerate(
        ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")
    )
}
DAYPART_TIMES = {
    "Morning (7:30 AM)": time(7, 30),
    "Afternoon (12:00 PM)": time(12),
    "Evening (5:00 PM)": time(17),
    "Night (8:00 PM)": time(20),
}
DAYPART_NAMES = {
    "morning": time(7, 30),
    "afternoon": time(12),
    "evening": time(17),
    "night": time(20),
}
WEEKDAYS.update({name[:3].lower(): index for name, index in WEEKDAYS.copy().items()})
MONTHS = {
    name.lower(): index
    for index, name in enumerate(
        ("January", "February", "March", "April", "May", "June",
         "July", "August", "September", "October", "November", "December"),
        start=1,
    )
}
MONTHS.update({name[:3].lower(): month for name, month in MONTHS.items()})


def parse_clock(text: str) -> time:
    value = text.strip().lower().replace(" ", "")
    if value in ("noon", "midday"):
        return time(12)
    if value == "midnight":
        return time(0)
    for pattern in ("%I:%M%p", "%I%p", "%H:%M", "%H"):
        try:
            return datetime.strptime(value, pattern).time()
        except ValueError:
            pass
    raise ValueError(f"Couldn't read time {text!r}. Try 'at 8pm' or 'at 20:00'.")


def parse_availability_time(text: str) -> time:
    value = text.strip()
    if value in DAYPART_TIMES:
        return DAYPART_TIMES[value]
    if value.casefold() in DAYPART_NAMES:
        return DAYPART_NAMES[value.casefold()]
    return parse_clock(value)


def parse_calendar_date(text: str) -> date:
    value = text.strip()
    for pattern in (
        "%Y-%m-%d",
        "%m/%d/%Y",
        "%b %d, %Y",
        "%B %d, %Y",
        "%b %d %Y",
        "%B %d %Y",
    ):
        try:
            return datetime.strptime(value, pattern).date()
        except ValueError:
            pass
    raise ValueError("Enter a date as YYYY-MM-DD or choose one from the calendar.")


def make_date_window(
    start_date: date,
    start_time: time,
    end_date: date,
    end_time: time,
) -> DateWindow:
    start = datetime.combine(start_date, start_time)
    end = datetime.combine(end_date, end_time)
    if end <= start:
        raise ValueError("The end must be later than the start.")
    return start, end


def grid_selection_to_window(
    start_date: date,
    first_cell: tuple[int, int],
    last_cell: tuple[int, int],
    day_count: int = 7,
) -> DateWindow:
    def offset(cell: tuple[int, int]) -> int:
        day_index, slot_index = cell
        if not 1 <= day_count <= 7 or not 0 <= day_index < day_count or not 0 <= slot_index < 48:
            raise ValueError("The calendar selection is outside the visible days.")
        return day_index * 24 * 60 + slot_index * 30

    start_offset = min(offset(first_cell), offset(last_cell))
    end_offset = max(offset(first_cell), offset(last_cell)) + 30
    start_day = start_date + timedelta(days=start_offset // (24 * 60))
    end_day = start_date + timedelta(days=end_offset // (24 * 60))
    start_time = time((start_offset % (24 * 60)) // 60, start_offset % 60)
    end_time = time((end_offset % (24 * 60)) // 60, end_offset % 60)
    return make_date_window(start_day, start_time, end_day, end_time)


def parse_endpoint(
    text: str,
    not_before: date,
    choose_daypart: Callable[[str], str],
) -> tuple[date, time, str | None]:
    time_match = re.search(
        r"\bat\s+(\d{1,2}(?::\d{2})?\s*(?:am|pm)?)\b", text, re.IGNORECASE
    )
    exact_time = parse_clock(time_match.group(1)) if time_match else None
    without_time = text[:time_match.start()] + text[time_match.end():] if time_match else text

    pattern = re.compile(
        r"^\s*(?P<weekday>[a-z]+)?\s*"
        r"(?:(?P<part1>morning|afternoon|night)\s+)?"
        r"(?:(?P<month>[a-z]+)\s+)?"
        r"(?P<day>\d{1,2})(?:st|nd|rd|th)?"
        r"(?:\s+(?P<part2>morning|afternoon|night))?"
        r"(?:\s+(?P<year>\d{4}))?\s*$",
        re.IGNORECASE,
    )
    match = pattern.match(without_time)
    if not match:
        raise ValueError(
            f"Couldn't read {text!r}. Try 'Friday night 20 to Saturday morning 28'."
        )

    weekday_text = match.group("weekday")
    weekday = WEEKDAYS.get(weekday_text.lower()) if weekday_text else None
    if weekday_text and weekday is None:
        raise ValueError(f"Unknown weekday {weekday_text!r}.")
    month_text = match.group("month")
    month = MONTHS.get(month_text.lower()) if month_text else None
    if month_text and month is None:
        raise ValueError(f"Unknown month {month_text!r}.")
    day = int(match.group("day"))
    year_text = match.group("year")
    period = match.group("part1") or match.group("part2")
    if not period and not exact_time:
        period = choose_daypart(text)

    candidates: list[date] = []
    years = [int(year_text)] if year_text else range(not_before.year, not_before.year + 3)
    for candidate_year in years:
        months = [month] if month else range(1, 13)
        for candidate_month in months:
            try:
                candidate = date(candidate_year, candidate_month, day)
            except ValueError:
                continue
            if candidate >= not_before and (weekday is None or candidate.weekday() == weekday):
                candidates.append(candidate)
        if candidates:
            break
    if not candidates:
        raise ValueError(f"Couldn't find a future date matching {text!r}. Include a month/year if needed.")

    if exact_time:
        endpoint_time = exact_time
    else:
        endpoint_time = {
            "morning": time(7, 30),
            "afternoon": time(12),
            "night": time(18),
        }[period.lower()]
    return candidates[0], endpoint_time, period.lower() if period and not exact_time else None


def parse_date_window(
    text: str,
    choose_daypart: Callable[[str], str],
    today: date | None = None,
) -> DateWindow:
    parts = re.split(r"\s+to\s+", text.strip(), maxsplit=1, flags=re.IGNORECASE)
    if len(parts) != 2:
        raise ValueError("Separate the start and end with 'to', e.g. 'Friday night 20 to Saturday morning 28'.")
    today = today or date.today()
    start_date, start_time, start_period = parse_endpoint(parts[0], today, choose_daypart)
    end_date, end_time, end_period = parse_endpoint(parts[1], start_date, choose_daypart)

    start = datetime.combine(start_date, start_time)
    end = datetime.combine(end_date, end_time)
    if end_period:
        end_time = {
            "morning": time(12),
            "afternoon": time(18),
            "night": time(0),
        }[end_period]
        end = datetime.combine(end_date, end_time)
        if end_period == "night":
            end += timedelta(days=1)
    if end <= start:
        raise ValueError("The end must be after the start. Check the dates and times.")
    return start, end


def split_windows(
    text: str,
    choose_daypart: Callable[[str], str],
) -> list[DateWindow]:
    windows = [parse_date_window(part, choose_daypart) for part in text.split(";") if part.strip()]
    if not windows:
        raise ValueError("Enter at least one availability range.")
    return windows


def merge_date_windows(windows: list[DateWindow]) -> list[DateWindow]:
    merged: list[DateWindow] = []
    for start, end in sorted(windows):
        if merged and start <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
        else:
            merged.append((start, end))
    return merged


def clip_to_day(windows: list[DateWindow], day: date) -> list[DateWindow]:
    day_start = datetime.combine(day, time.min)
    day_end = day_start + timedelta(days=1)
    return merge_date_windows([
        (max(start, day_start), min(end, day_end))
        for start, end in windows
        if start < day_end and end > day_start
    ])


def intersect_date_windows(left: list[DateWindow], right: list[DateWindow]) -> list[DateWindow]:
    common: list[DateWindow] = []
    for left_start, left_end in left:
        for right_start, right_end in right:
            start, end = max(left_start, right_start), min(left_end, right_end)
            if start < end:
                common.append((start, end))
    return merge_date_windows(common)


def format_datetime(value: datetime) -> str:
    return value.strftime("%H:%M")


def build_report(people: list[tuple[str, list[DateWindow]]]) -> str:
    dates: set[date] = set()
    for _, windows in people:
        for start, end in windows:
            current = start.date()
            last = (end - timedelta(microseconds=1)).date()
            while current <= last:
                dates.add(current)
                current += timedelta(days=1)

    if not dates:
        return "Add at least one person's availability first."
    lines: list[str] = []
    for day in sorted(dates):
        available = [
            (name, clip_to_day(windows, day))
            for name, windows in people
            if clip_to_day(windows, day)
        ]
        unavailable = [name for name, windows in people if not clip_to_day(windows, day)]
        lines.append(day.strftime("%A, %B %d, %Y").replace(" 0", " "))
        lines.append("Can make it:")
        for name, windows in available:
            times = ", ".join(
                f"{format_datetime(start)}-{format_datetime(end)}" for start, end in windows
            )
            lines.append(f"  {name} ({times})")
        if not available:
            lines.append("  Nobody")
        lines.append(f"Cannot make it: {', '.join(unavailable) if unavailable else 'nobody'}")

        if people:
            shared = clip_to_day(people[0][1], day)
            for _, windows in people[1:]:
                shared = intersect_date_windows(shared, clip_to_day(windows, day))
            common_text = ", ".join(
                f"{format_datetime(start)}-{format_datetime(end)}" for start, end in shared
            ) or "none"
            lines.append(f"Everyone overlaps: {common_text}")
        lines.append("")
    return "\n".join(lines)


def main() -> None:
    import calendar
    import math
    import tkinter as tk
    from tkinter import messagebox, scrolledtext, ttk

    colors = {
        "background": "#EAF4FF",
        "surface": "#FFFFFF",
        "light": "#D6E9FA",
        "mid": "#79AEDD",
        "mid_hover": "#659ACB",
        "text": "#244563",
        "muted": "#5B7691",
        "border": "#B8D5EF",
        "selection": "#A8CDEE",
    }
    slot_minutes = 30
    slot_height = 28
    time_column_width = 62
    people: list[tuple[str, list[DateWindow]]] = []
    today = date.today()
    anchor_date = [today]
    view_mode = ["Week"]
    drag_state: dict[str, tuple[int, int] | None] = {"start": None, "end": None}
    date_drag: dict[str, date | None] = {"start": None, "end": None}
    month_cells: list[date] = []
    year_cells: list[tuple[date, float, float, float, float]] = []

    def draw_rounded_rectangle(
        canvas: tk.Canvas,
        x1: float,
        y1: float,
        x2: float,
        y2: float,
        radius: float,
        fill: str,
        outline: str = "",
        width: int = 1,
        tags: tuple[str, ...] = (),
    ) -> None:
        radius = max(0, min(radius, (x2 - x1) / 2, (y2 - y1) / 2))
        points: list[float] = []
        corners = (
            (x2 - radius, y1 + radius, -90),
            (x2 - radius, y2 - radius, 0),
            (x1 + radius, y2 - radius, 90),
            (x1 + radius, y1 + radius, 180),
        )
        for center_x, center_y, start_angle in corners:
            for step in range(7):
                angle = math.radians(start_angle + step * 15)
                points.extend(
                    (center_x + radius * math.cos(angle), center_y + radius * math.sin(angle))
                )
        canvas.create_polygon(
            points,
            fill=fill,
            outline=outline,
            width=width,
            tags=tags,
        )

    root = tk.Tk()
    root.title("Hangout Time Finder")
    root.geometry("1120x960")
    root.minsize(860, 820)
    root.configure(background=colors["background"])

    style = ttk.Style(root)
    style.theme_use("clam")
    style.configure(".", font=("Helvetica Neue", 11))
    style.configure("App.TFrame", background=colors["background"])
    style.configure("Card.TFrame", background=colors["surface"])
    style.configure(
        "Card.TLabelframe",
        background=colors["surface"],
        bordercolor=colors["border"],
        borderwidth=0,
        relief="flat",
        padding=10,
    )
    style.configure(
        "Card.TLabelframe.Label",
        background=colors["surface"],
        foreground=colors["text"],
        font=("Helvetica Neue", 11, "bold"),
    )
    style.configure("Card.TLabel", background=colors["surface"], foreground=colors["text"])
    style.configure("Hint.TLabel", foreground=colors["muted"], font=("Helvetica Neue", 10))
    style.configure("TLabel", background=colors["surface"], foreground=colors["text"])
    style.configure(
        "Primary.TButton",
        background=colors["mid"],
        foreground="#FFFFFF",
        padding=(12, 7),
        borderwidth=0,
        font=("Helvetica Neue", 10, "bold"),
    )
    style.map(
        "Primary.TButton",
        background=[("active", colors["mid_hover"]), ("pressed", colors["mid_hover"])],
    )
    style.configure(
        "Date.TButton",
        background=colors["light"],
        foreground=colors["text"],
        padding=(9, 6),
        borderwidth=0,
    )
    style.map("Date.TButton", background=[("active", "#C2DDF5")])
    style.configure("TButton", padding=(10, 7), borderwidth=0, relief="flat")
    style.configure("TEntry", fieldbackground="#FFFFFF", foreground=colors["text"], padding=6)
    style.configure(
        "TCombobox",
        fieldbackground="#FFFFFF",
        foreground=colors["text"],
        padding=5,
    )
    style.map("TCombobox", fieldbackground=[("readonly", "#FFFFFF")])
    style.configure(
        "Treeview",
        background="#FFFFFF",
        fieldbackground="#FFFFFF",
        foreground=colors["text"],
        rowheight=28,
    )
    style.configure(
        "Treeview.Heading",
        background=colors["light"],
        foreground=colors["text"],
        font=("Helvetica Neue", 10, "bold"),
        padding=6,
    )
    style.map(
        "Treeview",
        background=[("selected", colors["mid"])],
        foreground=[("selected", "#FFFFFF")],
    )
    style.configure("TNotebook", background=colors["background"], borderwidth=0)
    style.configure(
        "TNotebook.Tab",
        background=colors["light"],
        foreground=colors["text"],
        padding=(12, 6),
    )
    style.map("TNotebook.Tab", background=[("selected", colors["surface"])])

    outer = ttk.Frame(root, style="App.TFrame", padding=(18, 14))
    outer.pack(fill="both", expand=True)
    header = tk.Frame(outer, background=colors["background"], padx=18, pady=11)
    header.pack(fill="x", pady=(0, 8))
    header_background = tk.Canvas(
        header,
        background=colors["background"],
        highlightthickness=0,
        borderwidth=0,
    )
    header_background.place(x=0, y=0, relwidth=1, relheight=1)

    def paint_header(event: tk.Event) -> None:
        header_background.delete("all")
        draw_rounded_rectangle(
            header_background,
            1,
            1,
            event.width - 1,
            event.height - 1,
            14,
            colors["mid"],
        )

    header.bind("<Configure>", paint_header)
    tk.Label(
        header,
        text="Find a time everyone can make it",
        background=colors["mid"],
        foreground="#FFFFFF",
        font=("Helvetica Neue", 18, "bold"),
    ).pack(anchor="w")
    tk.Label(
        header,
        text="Drag across the calendar to select a range, then enter who is available.",
        background=colors["mid"],
        foreground="#F5FAFF",
        font=("Helvetica Neue", 10),
    ).pack(anchor="w", pady=(2, 0))

    week_controls = ttk.Frame(outer, style="App.TFrame")
    week_controls.pack(fill="x", pady=(0, 5))
    ttk.Button(
        week_controls,
        text="Previous",
        command=lambda: shift_period(-1),
    ).pack(side="left")
    ttk.Button(
        week_controls,
        text="Today",
        command=lambda: go_today(),
    ).pack(side="left", padx=5)
    ttk.Button(
        week_controls,
        text="Next",
        command=lambda: shift_period(1),
    ).pack(side="left")
    week_label = ttk.Label(week_controls, style="Hint.TLabel", anchor="e")
    week_label.pack(side="right", fill="x", expand=True, padx=(10, 0))
    ttk.Label(week_controls, text="View:", style="Hint.TLabel").pack(
        side="right", padx=(8, 4)
    )
    view_selector = ttk.Combobox(
        week_controls,
        values=("Day", "3 days", "Week", "Month", "Year"),
        state="readonly",
        width=9,
    )
    view_selector.set(view_mode[0])
    view_selector.pack(side="right")
    view_selector.bind(
        "<<ComboboxSelected>>", lambda _event: set_view(view_selector.get())
    )

    calendar_card = ttk.LabelFrame(
        outer, text="Week calendar", style="Card.TLabelframe"
    )
    calendar_card.pack(fill="both", expand=True, pady=(0, 8))
    calendar_card.columnconfigure(0, weight=1)
    calendar_card.rowconfigure(1, weight=1)
    week_header = tk.Canvas(
        calendar_card,
        height=38,
        background=colors["surface"],
        highlightthickness=0,
        borderwidth=0,
    )
    week_header.grid(row=0, column=0, sticky="ew")
    calendar_canvas = tk.Canvas(
        calendar_card,
        height=450,
        background=colors["surface"],
        highlightthickness=0,
        borderwidth=0,
        cursor="crosshair",
    )
    calendar_canvas.grid(row=1, column=0, sticky="nsew")
    calendar_scroll = ttk.Scrollbar(
        calendar_card, orient="vertical", command=calendar_canvas.yview
    )
    calendar_scroll.grid(row=1, column=1, sticky="ns")
    calendar_canvas.configure(yscrollcommand=calendar_scroll.set)

    tabs = ttk.Notebook(outer)
    tabs.pack(fill="both", expand=True)
    people_tab = ttk.Frame(tabs, style="Card.TFrame", padding=8)
    report_tab = ttk.Frame(tabs, style="Card.TFrame", padding=8)
    tabs.add(people_tab, text="People and ranges")
    tabs.add(report_tab, text="Shared availability")

    people_tab.columnconfigure(0, weight=1)
    people_tab.rowconfigure(0, weight=1)
    people_tree = ttk.Treeview(
        people_tab,
        columns=("person", "ranges"),
        show="headings",
        selectmode="browse",
        height=4,
    )
    people_tree.heading("person", text="Person")
    people_tree.heading("ranges", text="Availability ranges")
    people_tree.column("person", width=150, minwidth=110, stretch=False)
    people_tree.column("ranges", width=700, minwidth=250)
    people_tree.grid(row=0, column=0, sticky="nsew")
    people_scroll = ttk.Scrollbar(people_tab, orient="vertical", command=people_tree.yview)
    people_scroll.grid(row=0, column=1, sticky="ns")
    people_hscroll = ttk.Scrollbar(people_tab, orient="horizontal", command=people_tree.xview)
    people_hscroll.grid(row=1, column=0, sticky="ew")
    people_tree.configure(
        xscrollcommand=people_hscroll.set,
        yscrollcommand=people_scroll.set,
    )
    people_status = ttk.Label(people_tab, text="No availability added yet.", style="Hint.TLabel")
    people_status.grid(row=2, column=0, sticky="w", pady=(5, 0))
    ttk.Button(
        people_tab,
        text="Remove selected person",
        command=lambda: remove_person(),
    ).grid(row=2, column=1, sticky="e", pady=(5, 0))

    output = scrolledtext.ScrolledText(
        report_tab,
        wrap="word",
        state="disabled",
        height=7,
        background="#FFFFFF",
        foreground=colors["text"],
        insertbackground=colors["text"],
        selectbackground=colors["light"],
        relief="flat",
        padx=10,
        pady=8,
        font=("Menlo", 10),
    )
    output.pack(fill="both", expand=True)
    output.tag_configure("day", foreground=colors["mid_hover"], font=("Helvetica Neue", 10, "bold"))
    output.tag_configure("overlap", foreground=colors["mid_hover"], font=("Menlo", 10, "bold"))
    output.tag_configure("empty", foreground=colors["muted"], justify="center")

    def format_date_label(value: date) -> str:
        return f"{value.strftime('%a, %b')} {value.day}, {value.year}"

    def format_clock(value: time) -> str:
        return value.strftime("%I:%M %p").lstrip("0")

    def update_output(text: str, empty: bool = False) -> None:
        output.configure(state="normal")
        output.delete("1.0", "end")
        for line in text.splitlines(keepends=True):
            if empty:
                tag = "empty"
            elif line.startswith("Everyone overlaps:"):
                tag = "overlap"
            elif re.search(r", \d{4}$", line.rstrip()):
                tag = "day"
            else:
                tag = ""
            output.insert("end", line, tag)
        output.configure(state="disabled")

    def format_range(window: DateWindow) -> str:
        start, end = window
        return (
            f"{format_date_label(start.date())} {format_clock(start.time())} "
            f"to {format_date_label(end.date())} {format_clock(end.time())}"
        )

    def refresh_people() -> None:
        people_tree.delete(*people_tree.get_children())
        range_count = sum(len(windows) for _, windows in people)
        for index, (name, windows) in enumerate(people):
            ranges = "  |  ".join(format_range(window) for window in windows)
            people_tree.insert("", "end", iid=str(index), values=(name, ranges))
        if people:
            person_word = "person" if len(people) == 1 else "people"
            range_word = "range" if range_count == 1 else "ranges"
            people_status.configure(
                text=f"{len(people)} {person_word}  |  {range_count} availability {range_word}"
            )
        else:
            people_status.configure(text="No availability added yet.")

    def show_results() -> None:
        if not people:
            update_output("Drag across the calendar and add someone's availability.", empty=True)
            return
        update_output(build_report(people))

    def add_person_range(window: DateWindow, name: str) -> None:
        for existing_name, windows in people:
            if existing_name.casefold() == name.casefold():
                windows.append(window)
                break
        else:
            people.append((name, [window]))
        refresh_people()
        show_results()
        redraw_calendar()

    def prompt_for_range(window: DateWindow) -> None:
        start, end = window
        dialog = tk.Toplevel(root)
        dialog.title("Add availability")
        dialog.transient(root)
        dialog.resizable(False, False)
        dialog.configure(background=colors["background"])
        dialog.grab_set()

        form = ttk.LabelFrame(
            dialog, text="Selected availability", style="Card.TLabelframe", padding=14
        )
        form.pack(fill="both", expand=True, padx=14, pady=14)
        form.columnconfigure(0, weight=1)
        form.columnconfigure(1, weight=1)
        ttk.Label(form, text="Person's name").grid(row=0, column=0, sticky="w")
        name_entry = ttk.Entry(form, width=36)
        name_entry.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(3, 10))

        start_date_var = tk.StringVar(value=start.date().isoformat())
        end_date_var = tk.StringVar(value=end.date().isoformat())

        def open_date_picker(initial: date, on_select: Callable[[date], None]) -> None:
            picker = tk.Toplevel(dialog)
            picker.title("Choose a date")
            picker.transient(dialog)
            picker.resizable(False, False)
            picker.configure(background=colors["background"])
            month = [initial.replace(day=1)]

            picker_frame = ttk.LabelFrame(
                picker, text="Choose a date", style="Card.TLabelframe", padding=12
            )
            picker_frame.pack(fill="both", expand=True, padx=10, pady=10)
            navigation = ttk.Frame(picker_frame, style="Card.TFrame")
            navigation.pack(fill="x", pady=(0, 7))
            month_label = ttk.Label(navigation, style="Card.TLabel", anchor="center")
            month_label.pack(side="left", fill="x", expand=True)
            days_frame = ttk.Frame(picker_frame, style="Card.TFrame")
            days_frame.pack(fill="both", expand=True)

            def close_picker(chosen: date | None = None) -> None:
                if chosen is not None:
                    on_select(chosen)
                picker.destroy()
                dialog.grab_set()

            def render_month() -> None:
                month_label.configure(text=month[0].strftime("%B %Y"))
                for child in days_frame.winfo_children():
                    child.destroy()
                for column, weekday in enumerate(("M", "T", "W", "T", "F", "S", "S")):
                    ttk.Label(
                        days_frame,
                        text=weekday,
                        style="Hint.TLabel",
                        anchor="center",
                    ).grid(row=0, column=column, sticky="nsew", pady=(0, 3))
                weeks = calendar.Calendar(firstweekday=calendar.MONDAY).monthdayscalendar(
                    month[0].year, month[0].month
                )
                while len(weeks) < 6:
                    weeks.append([0] * 7)
                for row, week in enumerate(weeks, start=1):
                    for column, day_number in enumerate(week):
                        if day_number:
                            ttk.Button(
                                days_frame,
                                text=str(day_number),
                                style="Date.TButton",
                                width=3,
                                command=lambda day=day_number: close_picker(
                                    date(month[0].year, month[0].month, day)
                                ),
                            ).grid(row=row, column=column, sticky="nsew", padx=1, pady=1)
                        else:
                            ttk.Label(days_frame, text="", style="Card.TLabel").grid(
                                row=row, column=column, sticky="nsew"
                            )

            def shift_month(amount: int) -> None:
                if amount < 0:
                    month[0] = (month[0] - timedelta(days=1)).replace(day=1)
                else:
                    month[0] = (month[0].replace(day=28) + timedelta(days=4)).replace(day=1)
                render_month()

            ttk.Button(
                navigation, text="<", width=3, command=lambda: shift_month(-1)
            ).pack(side="left", before=month_label)
            ttk.Button(navigation, text=">", width=3, command=lambda: shift_month(1)).pack(
                side="right"
            )
            for column in range(7):
                days_frame.columnconfigure(column, weight=1)
            render_month()
            picker.protocol("WM_DELETE_WINDOW", lambda: close_picker())
            picker.grab_set()

        def add_date_field(
            label: str,
            row: int,
            value: date,
        ) -> tk.StringVar:
            ttk.Label(form, text=label).grid(row=row, column=0, sticky="w", pady=(0, 3))
            variable = tk.StringVar(value=value.isoformat())
            field = ttk.Frame(form, style="Card.TFrame")
            field.grid(row=row + 1, column=0, columnspan=2, sticky="ew", pady=(0, 8))
            field.columnconfigure(0, weight=1)
            entry = ttk.Entry(field, textvariable=variable)
            entry.grid(row=0, column=0, sticky="ew", padx=(0, 6))

            def pick_date() -> None:
                try:
                    initial_date = parse_calendar_date(variable.get())
                except ValueError:
                    initial_date = value
                open_date_picker(initial_date, lambda chosen: variable.set(chosen.isoformat()))

            ttk.Button(field, text="Choose date", command=pick_date).grid(
                row=0, column=1, sticky="ew"
            )
            return variable

        start_date_var = add_date_field("Start date", 2, start.date())
        end_date_var = add_date_field("End date", 4, end.date())

        time_options = tuple(DAYPART_TIMES)
        ttk.Label(form, text="Starting time or day part").grid(
            row=6, column=0, sticky="w", pady=(2, 0)
        )
        ttk.Label(form, text="Ending time or day part").grid(
            row=6, column=1, sticky="w", pady=(2, 0)
        )
        start_time_box = ttk.Combobox(form, values=time_options, state="normal", width=22)
        start_time_box.set(format_clock(start.time()))
        start_time_box.grid(row=7, column=0, sticky="ew", padx=(0, 8), pady=(3, 10))
        end_time_box = ttk.Combobox(form, values=time_options, state="normal", width=22)
        end_time_box.set(format_clock(end.time()))
        end_time_box.grid(row=7, column=1, sticky="ew", pady=(3, 10))
        ttk.Label(
            form,
            text="Dates accept YYYY-MM-DD or M/D/YYYY. Choose a day part or type a time like 8pm.",
            style="Hint.TLabel",
            wraplength=370,
        ).grid(row=8, column=0, columnspan=2, sticky="w", pady=(0, 10))

        def save_range() -> None:
            name = name_entry.get().strip()
            if not name:
                messagebox.showerror("Name needed", "Enter the person's name.", parent=dialog)
                name_entry.focus_set()
                return
            try:
                edited_window = make_date_window(
                    parse_calendar_date(start_date_var.get()),
                    parse_availability_time(start_time_box.get()),
                    parse_calendar_date(end_date_var.get()),
                    parse_availability_time(end_time_box.get()),
                )
            except ValueError as error:
                messagebox.showerror("Check the time range", str(error), parent=dialog)
                return
            add_person_range(edited_window, name)
            dialog.destroy()

        buttons = ttk.Frame(form, style="Card.TFrame")
        buttons.grid(row=9, column=0, columnspan=2, sticky="ew")
        ttk.Button(buttons, text="Cancel", command=dialog.destroy).pack(side="right")
        ttk.Button(
            buttons,
            text="Add availability",
            style="Primary.TButton",
            command=save_range,
        ).pack(side="right", padx=(0, 8))
        name_entry.bind("<Return>", lambda _event: save_range())
        name_entry.focus_set()

    def cell_at(event: tk.Event) -> tuple[int, int] | None:
        day_count = len(visible_dates())
        width = calendar_canvas.winfo_width()
        day_width = (width - time_column_width) / day_count
        x = calendar_canvas.canvasx(event.x) - time_column_width
        y = calendar_canvas.canvasy(event.y)
        if x < 0 or day_width <= 0 or y < 0:
            return None
        day_index = int(x // day_width)
        slot_index = int(y // slot_height)
        if day_index >= day_count or slot_index >= 48:
            return None
        return day_index, slot_index

    def draw_availability(day_width: float) -> None:
        person_colors = ("#C2DDF5", "#9FC5EA", "#D7E9F8", "#AFD0EE", "#87B4DF", "#D0E4F6")
        for day_index, day in enumerate(visible_dates()):
            intervals: list[tuple[datetime, datetime, int, str]] = []
            for person_index, (name, windows) in enumerate(people):
                for start, end in clip_to_day(windows, day):
                    intervals.append((start, end, person_index, name))
            intervals.sort(key=lambda item: (item[0], item[1]))
            lane_ends: list[datetime] = []
            positioned: list[tuple[datetime, datetime, int, str, int]] = []
            for start, end, person_index, name in intervals:
                lane = next(
                    (index for index, lane_end in enumerate(lane_ends) if lane_end <= start),
                    len(lane_ends),
                )
                if lane == len(lane_ends):
                    lane_ends.append(end)
                else:
                    lane_ends[lane] = end
                positioned.append((start, end, person_index, name, lane))
            lane_count = max(1, len(lane_ends))
            day_x = time_column_width + day_index * day_width
            lane_width = day_width / lane_count
            day_start = datetime.combine(day, time.min)
            for start, end, person_index, name, lane in positioned:
                start_minutes = (start - day_start).total_seconds() / 60
                end_minutes = (end - day_start).total_seconds() / 60
                y1 = start_minutes / slot_minutes * slot_height
                y2 = end_minutes / slot_minutes * slot_height
                x1 = day_x + lane * lane_width + 2
                x2 = day_x + (lane + 1) * lane_width - 2
                draw_rounded_rectangle(
                    calendar_canvas,
                    x1,
                    y1 + 1,
                    x2,
                    y2 - 1,
                    min(7, (y2 - y1) / 2),
                    person_colors[person_index % len(person_colors)],
                    colors["mid_hover"],
                    tags=("availability",),
                )
                if y2 - y1 >= 18 and x2 - x1 >= 12:
                    label = name if y2 - y1 < 42 else f"{name}  {format_clock(start.time())}"
                    calendar_canvas.create_text(
                        x1 + 4,
                        y1 + 3,
                        text=label,
                        anchor="nw",
                        fill=colors["text"],
                        font=("Helvetica Neue", 9),
                        width=max(1, x2 - x1 - 8),
                        tags=("availability",),
                    )

    def draw_selection(day_width: float) -> None:
        first_cell = drag_state["start"]
        last_cell = drag_state["end"]
        if first_cell is None or last_cell is None:
            return
        dates = visible_dates()
        start, end = grid_selection_to_window(
            dates[0], first_cell, last_cell, day_count=len(dates)
        )
        for day_index, day in enumerate(dates):
            day_start = datetime.combine(day, time.min)
            day_end = day_start + timedelta(days=1)
            clipped_start = max(start, day_start)
            clipped_end = min(end, day_end)
            if clipped_start >= clipped_end:
                continue
            y1 = (clipped_start - day_start).total_seconds() / 60 / slot_minutes * slot_height
            y2 = (clipped_end - day_start).total_seconds() / 60 / slot_minutes * slot_height
            x1 = time_column_width + day_index * day_width + 1
            x2 = time_column_width + (day_index + 1) * day_width - 1
            draw_rounded_rectangle(
                calendar_canvas,
                x1,
                y1 + 1,
                x2,
                y2 - 1,
                7,
                colors["selection"],
                colors["mid_hover"],
                width=2,
                tags=("selection",),
            )

    def visible_dates() -> list[date]:
        mode = view_mode[0]
        if mode == "Day":
            return [anchor_date[0]]
        if mode == "3 days":
            return [anchor_date[0] + timedelta(days=offset) for offset in range(3)]
        monday = anchor_date[0] - timedelta(days=anchor_date[0].weekday())
        return [monday + timedelta(days=offset) for offset in range(7)]

    def period_label() -> str:
        mode = view_mode[0]
        if mode == "Year":
            return str(anchor_date[0].year)
        if mode == "Month":
            return anchor_date[0].strftime("%B %Y")
        dates = visible_dates()
        if mode == "Day":
            return format_date_label(dates[0])
        if dates[0].year == dates[-1].year:
            return (
                f"{dates[0].strftime('%b')} {dates[0].day} - "
                f"{dates[-1].strftime('%b')} {dates[-1].day}, {dates[-1].year}"
            )
        return f"{format_date_label(dates[0])} - {format_date_label(dates[-1])}"

    def draw_day_header(width: int, labels: list[str], time_axis: bool) -> float:
        offset = time_column_width if time_axis else 0
        day_width = (width - offset) / len(labels)
        week_header.delete("all")
        week_header.configure(scrollregion=(0, 0, width, 38))
        if time_axis:
            week_header.create_rectangle(
                0, 0, time_column_width, 38, fill=colors["light"], outline=colors["border"]
            )
            week_header.create_text(
                time_column_width / 2,
                19,
                text="Time",
                fill=colors["text"],
                font=("Helvetica Neue", 9, "bold"),
            )
        for day_index, label in enumerate(labels):
            x1 = offset + day_index * day_width
            x2 = offset + (day_index + 1) * day_width
            week_header.create_rectangle(
                x1, 0, x2, 38, fill=colors["light"], outline=colors["border"]
            )
            week_header.create_text(
                (x1 + x2) / 2,
                19,
                text=label,
                fill=colors["text"],
                font=("Helvetica Neue", 9, "bold"),
            )
        return day_width

    def draw_time_grid() -> None:
        width = calendar_canvas.winfo_width()
        dates = visible_dates()
        day_width = draw_day_header(
            width,
            [f"{day.strftime('%a')} {day.month}/{day.day}" for day in dates],
            time_axis=True,
        )
        calendar_canvas.configure(
            height=450,
            scrollregion=(0, 0, width, 48 * slot_height),
            yscrollincrement=slot_height,
        )
        calendar_canvas.delete("all")
        for day_index in range(len(dates)):
            x1 = time_column_width + day_index * day_width
            x2 = time_column_width + (day_index + 1) * day_width
            calendar_canvas.create_rectangle(
                x1,
                0,
                x2,
                48 * slot_height,
                fill="#FFFFFF" if day_index % 2 == 0 else "#F7FBFF",
                outline="",
            )
        for slot_index in range(49):
            y = slot_index * slot_height
            if slot_index < 48 and slot_index % 2 == 0:
                calendar_canvas.create_text(
                    time_column_width - 7,
                    y + 2,
                    text=time(slot_index // 2, 0).strftime("%I %p").lstrip("0"),
                    anchor="ne",
                    fill=colors["muted"],
                    font=("Helvetica Neue", 8),
                )
            calendar_canvas.create_line(
                time_column_width,
                y,
                width,
                y,
                fill=colors["border"] if slot_index % 2 == 0 else "#E7F0F8",
                width=1,
            )
        for day_index in range(len(dates) + 1):
            x = time_column_width + day_index * day_width
            calendar_canvas.create_line(
                x, 0, x, 48 * slot_height, fill=colors["border"], width=1
            )
        draw_availability(day_width)
        draw_selection(day_width)

    def people_available_on(day: date) -> list[str]:
        return [
            name
            for name, windows in people
            if clip_to_day(windows, day)
        ]

    def selected_date(day: date) -> bool:
        first = date_drag["start"]
        last = date_drag["end"]
        return first is not None and last is not None and min(first, last) <= day <= max(first, last)

    def draw_month_view() -> None:
        width = calendar_canvas.winfo_width()
        day_width = draw_day_header(
            width, ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"], time_axis=False
        )
        first_of_month = anchor_date[0].replace(day=1)
        grid_start = first_of_month - timedelta(days=first_of_month.weekday())
        month_cells.clear()
        calendar_canvas.configure(
            height=480,
            scrollregion=(0, 0, width, 6 * 90),
            yscrollincrement=90,
        )
        calendar_canvas.delete("all")
        for index in range(42):
            day = grid_start + timedelta(days=index)
            month_cells.append(day)
            column, row = index % 7, index // 7
            x1, y1 = column * day_width, row * 90
            x2, y2 = x1 + day_width, y1 + 90
            names = people_available_on(day)
            fill = (
                colors["selection"]
                if selected_date(day)
                else "#EAF4FF"
                if day == today
                else "#FFFFFF"
                if day.month == first_of_month.month
                else "#F4F8FC"
            )
            calendar_canvas.create_rectangle(
                x1, y1, x2, y2, fill=fill, outline=colors["border"], width=1
            )
            day_color = colors["muted"] if day.month != first_of_month.month else colors["text"]
            calendar_canvas.create_text(
                x1 + 8,
                y1 + 7,
                text=str(day.day),
                anchor="nw",
                fill=day_color,
                font=("Helvetica Neue", 10, "bold"),
            )
            for name_index, name in enumerate(names[:3]):
                chip_y = y1 + 27 + name_index * 18
                draw_rounded_rectangle(
                    calendar_canvas,
                    x1 + 5,
                    chip_y,
                    x2 - 5,
                    chip_y + 16,
                    6,
                    "#D6E9FA",
                    "",
                )
                calendar_canvas.create_text(
                    x1 + 10,
                    chip_y + 8,
                    text=name,
                    anchor="w",
                    fill=colors["text"],
                    font=("Helvetica Neue", 8),
                    width=max(1, day_width - 18),
                )
            if len(names) > 3:
                calendar_canvas.create_text(
                    x1 + 8,
                    y2 - 8,
                    text=f"+{len(names) - 3} more",
                    anchor="sw",
                    fill=colors["muted"],
                    font=("Helvetica Neue", 8),
                )

    def draw_year_view() -> None:
        width = calendar_canvas.winfo_width()
        year_cells.clear()
        week_header.delete("all")
        week_header.configure(scrollregion=(0, 0, width, 38))
        week_header.create_text(
            width / 2,
            19,
            text=f"{anchor_date[0].year} - drag across dates to add availability",
            fill=colors["text"],
            font=("Helvetica Neue", 10, "bold"),
        )
        gap = 10
        columns = 3
        panel_width = (width - gap * (columns + 1)) / columns
        panel_height = 152
        total_height = gap + 4 * (panel_height + gap)
        calendar_canvas.configure(
            height=480,
            scrollregion=(0, 0, width, total_height),
            yscrollincrement=20,
        )
        calendar_canvas.delete("all")
        for month_index in range(12):
            month_number = month_index + 1
            row, column = divmod(month_index, columns)
            panel_x = gap + column * (panel_width + gap)
            panel_y = gap + row * (panel_height + gap)
            draw_rounded_rectangle(
                calendar_canvas,
                panel_x,
                panel_y,
                panel_x + panel_width,
                panel_y + panel_height,
                9,
                "#FFFFFF",
                colors["border"],
            )
            calendar_canvas.create_text(
                panel_x + panel_width / 2,
                panel_y + 13,
                text=calendar.month_name[month_number],
                fill=colors["mid_hover"],
                font=("Helvetica Neue", 10, "bold"),
            )
            day_width = (panel_width - 16) / 7
            for day_index, label in enumerate(("M", "T", "W", "T", "F", "S", "S")):
                calendar_canvas.create_text(
                    panel_x + 8 + (day_index + 0.5) * day_width,
                    panel_y + 29,
                    text=label,
                    fill=colors["muted"],
                    font=("Helvetica Neue", 7),
                )
            weeks = calendar.Calendar(firstweekday=calendar.MONDAY).monthdayscalendar(
                anchor_date[0].year, month_number
            )
            while len(weeks) < 6:
                weeks.append([0] * 7)
            for week_index, week in enumerate(weeks):
                for day_index, day_number in enumerate(week):
                    if not day_number:
                        continue
                    day = date(anchor_date[0].year, month_number, day_number)
                    x1 = panel_x + 8 + day_index * day_width
                    y1 = panel_y + 38 + week_index * 17
                    x2, y2 = x1 + day_width, y1 + 17
                    year_cells.append((day, x1, y1, x2, y2))
                    if selected_date(day) or day == today:
                        draw_rounded_rectangle(
                            calendar_canvas,
                            x1 + 1,
                            y1 + 1,
                            x2 - 1,
                            y2 - 1,
                            5,
                            colors["selection"] if selected_date(day) else colors["light"],
                            "",
                        )
                    calendar_canvas.create_text(
                        (x1 + x2) / 2,
                        (y1 + y2) / 2,
                        text=str(day_number),
                        fill=colors["text"],
                        font=("Helvetica Neue", 8),
                    )
                    if people_available_on(day):
                        calendar_canvas.create_oval(
                            x2 - 5,
                            y1 + 2,
                            x2 - 2,
                            y1 + 5,
                            fill=colors["mid_hover"],
                            outline="",
                        )

    def redraw_calendar(_event: tk.Event | None = None) -> None:
        width = calendar_canvas.winfo_width()
        if width <= 0:
            return
        week_label.configure(text=period_label())
        mode = view_mode[0]
        if mode in ("Day", "3 days", "Week"):
            calendar_card.configure(
                text=f"{mode} view - drag across 30-minute slots to select times"
            )
            draw_time_grid()
        elif mode == "Month":
            calendar_card.configure(text="Month view - drag across dates to select a range")
            draw_month_view()
        else:
            calendar_card.configure(text="Year view - drag across dates to select a range")
            draw_year_view()

    def shift_period(amount: int) -> None:
        mode = view_mode[0]
        current = anchor_date[0]
        if mode == "Day":
            updated = current + timedelta(days=amount)
        elif mode == "3 days":
            updated = current + timedelta(days=3 * amount)
        elif mode == "Week":
            updated = current + timedelta(days=7 * amount)
        elif mode == "Month":
            month_index = current.year * 12 + current.month - 1 + amount
            year, month = divmod(month_index, 12)
            month += 1
            updated = date(year, month, min(current.day, calendar.monthrange(year, month)[1]))
        else:
            year = current.year + amount
            updated = date(year, current.month, min(current.day, calendar.monthrange(year, current.month)[1]))
        anchor_date[0] = updated
        redraw_calendar()
        calendar_canvas.yview_moveto(0)

    def set_view(mode: str) -> None:
        view_mode[0] = mode
        drag_state["start"] = None
        drag_state["end"] = None
        date_drag["start"] = None
        date_drag["end"] = None
        redraw_calendar()
        calendar_canvas.yview_moveto(0)

    def go_today() -> None:
        anchor_date[0] = today
        redraw_calendar()
        calendar_canvas.yview_moveto(0)

    def date_at(event: tk.Event) -> date | None:
        x = calendar_canvas.canvasx(event.x)
        y = calendar_canvas.canvasy(event.y)
        if view_mode[0] == "Month":
            width = calendar_canvas.winfo_width()
            day_width = width / 7
            column = int(x // day_width)
            row = int(y // 90)
            if 0 <= column < 7 and 0 <= row < 6:
                return month_cells[row * 7 + column]
        elif view_mode[0] == "Year":
            for value, x1, y1, x2, y2 in year_cells:
                if x1 <= x <= x2 and y1 <= y <= y2:
                    return value
        return None

    def update_drag(event: tk.Event) -> None:
        if view_mode[0] in ("Month", "Year"):
            if date_drag["start"] is None:
                return
            selected = date_at(event)
            if selected is not None:
                date_drag["end"] = selected
                redraw_calendar()
            return
        if drag_state["start"] is None:
            return
        cell = cell_at(event)
        if cell is not None:
            drag_state["end"] = cell
            redraw_calendar()

    def begin_drag(event: tk.Event) -> None:
        if view_mode[0] in ("Month", "Year"):
            selected = date_at(event)
            if selected is None:
                return
            date_drag["start"] = selected
            date_drag["end"] = selected
            redraw_calendar()
            return
        cell = cell_at(event)
        if cell is None:
            return
        drag_state["start"] = cell
        drag_state["end"] = cell
        redraw_calendar()

    def finish_drag(event: tk.Event) -> None:
        if view_mode[0] in ("Month", "Year"):
            if date_drag["start"] is None:
                return
            selected = date_at(event)
            if selected is not None:
                date_drag["end"] = selected
            first = date_drag["start"]
            last = date_drag["end"]
            date_drag["start"] = None
            date_drag["end"] = None
            redraw_calendar()
            if first is not None and last is not None:
                start_day, end_day = min(first, last), max(first, last)
                prompt_for_range(
                    make_date_window(start_day, time(9), end_day, time(17))
                )
            return
        if drag_state["start"] is None:
            return
        cell = cell_at(event)
        if cell is not None:
            drag_state["end"] = cell
        first_cell = drag_state["start"]
        last_cell = drag_state["end"]
        drag_state["start"] = None
        drag_state["end"] = None
        redraw_calendar()
        if first_cell is not None and last_cell is not None:
            dates = visible_dates()
            prompt_for_range(
                grid_selection_to_window(
                    dates[0], first_cell, last_cell, day_count=len(dates)
                )
            )

    def scroll_calendar(event: tk.Event) -> str:
        calendar_canvas.yview_scroll(-1 if event.delta > 0 else 1, "units")
        return "break"

    def remove_person() -> None:
        selected = people_tree.selection()
        if not selected:
            messagebox.showinfo(
                "Select a person",
                "Choose a person in the list before removing them.",
                parent=root,
            )
            return
        people.pop(int(selected[0]))
        refresh_people()
        show_results()
        redraw_calendar()

    calendar_canvas.bind("<ButtonPress-1>", begin_drag)
    calendar_canvas.bind("<B1-Motion>", update_drag)
    calendar_canvas.bind("<ButtonRelease-1>", finish_drag)
    calendar_canvas.bind("<MouseWheel>", scroll_calendar)
    calendar_canvas.bind("<Configure>", redraw_calendar)
    week_header.bind("<Configure>", redraw_calendar)

    update_output("Drag across the calendar to add someone's availability.", empty=True)
    root.after_idle(redraw_calendar)
    root.mainloop()


if __name__ == "__main__":
    main()
