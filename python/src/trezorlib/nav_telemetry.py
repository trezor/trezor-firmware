# This file is part of the Trezor project.
#
# Copyright (C) SatoshiLabs and contributors
#
# This library is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License version 3
# as published by the Free Software Foundation.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the License along with this library.
# If not, see <https://www.gnu.org/licenses/lgpl-3.0.html>.

"""Decoder for the Safe 3 navigation tutorial interaction log.

The device records a timestamped event per interaction while the user walks
through `trezorctl debug nav-tutorial`, and returns the log encoded as
``NAVTEL1|<dropped>|<t_ms>,<code>,<arg>;...``. This module turns that back into
events and derives what a usability test of the new navigation needs: how long
each screen was on display (the context menu and its info screen included),
which buttons were used there, and how many attempts each action took.

The "Shift" modifier gets extra attention, because it is the least discoverable
part of the concept. For every left-button hold we know how long it lasted and
what came of it, which answers the questions that decide the design: is the
hold threshold reachable, do users who arm Shift actually use it, and how often
does a hold-that-was-meant-to-be-Shift open the menu instead.

Event codes must stay in sync with `core/embed/rust/src/ui/nav_telemetry.rs`.
"""

from __future__ import annotations

import typing as t
from dataclasses import dataclass, field

LOG_VERSION = "NAVTEL1"

#: Line prefix the device uses when streaming events to its serial console.
#: Mirrors `SERIAL_TAG` in core/embed/rust/src/ui/nav_telemetry.rs.
SERIAL_TAG = "NAVTEL"

# Event codes (see nav_telemetry.rs).
EV_SESSION_START = 0x01
EV_PAGE = 0x02
EV_SUBPAGE = 0x03
EV_SHIFT_AVAIL = 0x04
EV_PRESS = 0x10
EV_RELEASE = 0x11
EV_LONG_PRESS = 0x12
EV_SHIFT_BACK = 0x13
EV_SHIFT_END = 0x14
EV_TRIGGER = 0x15
EV_HTC_ABORT = 0x16
EV_ACTION = 0x20
EV_MENU_ITEM = 0x21
EV_MARK = 0x30

EVENT_NAMES = {
    EV_SESSION_START: "session_start",
    EV_PAGE: "page",
    EV_SUBPAGE: "subpage",
    EV_SHIFT_AVAIL: "shift_available",
    EV_PRESS: "press",
    EV_RELEASE: "release",
    EV_LONG_PRESS: "long_press",
    EV_SHIFT_BACK: "shift_back",
    EV_SHIFT_END: "shift_end",
    EV_TRIGGER: "trigger",
    EV_HTC_ABORT: "hold_to_confirm_aborted",
    EV_ACTION: "action",
    EV_MENU_ITEM: "menu_item",
    EV_MARK: "mark",
}

POS_LEFT, POS_MIDDLE, POS_RIGHT = 0, 1, 2
POS_NAMES = {0: "left", 1: "middle", 2: "right", 3: "other"}

ACTION_NAMES = {
    0: "next_page",
    1: "prev_page",
    2: "first_page",
    3: "last_page",
    4: "confirm",
    5: "cancel",
    6: "open_menu",
}

MARK_TUTORIAL_BEGIN = 1
MARK_INFO_OPEN = 2
MARK_INFO_CLOSE = 3
MARK_MENU_OPEN = 4
MARK_MENU_RESTART = 5
MARK_MENU_COMPLETE = 6
MARK_MENU_BACK = 7
MARK_END_CONFIRMED = 8
MARK_END_CANCELLED = 9
MARK_INTRO = 10
MARK_ADDRESS = 11

MARK_NAMES = {
    MARK_TUTORIAL_BEGIN: "tutorial_begin",
    MARK_INFO_OPEN: "info_screen_open",
    MARK_INFO_CLOSE: "info_screen_close",
    MARK_MENU_OPEN: "menu_open",
    MARK_MENU_RESTART: "menu_restart",
    MARK_MENU_COMPLETE: "menu_complete",
    MARK_MENU_BACK: "menu_back",
    MARK_END_CONFIRMED: "end_confirmed",
    MARK_END_CANCELLED: "end_cancelled",
    MARK_INTRO: "intro_screen",
    MARK_ADDRESS: "address_screen",
}

# Screen titles of the tutorial, indexed by page. Must match the `pages` list in
# core/src/apps/debug/nav_tutorial.py.
SCREEN_NAMES = [
    "WELCOME TO TREZOR",
    "(left/right buttons)",
    "HOLD TO CONFIRM",
    "MIDDLE BUTTON",
    # Two sub-pages: "TRY SCROLLING" then "GO BACK", whose right button is a
    # dead end - only Shift + right leaves it, which lands on REMEMBER.
    "TRY SCROLLING / GO BACK",
    "REMEMBER",
    "MENU",
    "TUTORIAL COMPLETE",
]

# The context menu and its info screen are separate layouts, not tutorial pages,
# so they get synthetic ids above the real ones. Without this their time and
# button presses would be charged to whichever screen the menu was opened from.
# Anything recorded before any screen announced itself lands here rather than
# being dropped, so a log from a mismatched firmware still shows its contents.
SCREEN_UNATTRIBUTED = 99
SCREEN_INFO = 100
SCREEN_MENU = 101
SCREEN_INTRO = 102
SCREEN_ADDRESS = 103
SYNTHETIC_SCREEN_NAMES = {
    SCREEN_UNATTRIBUTED: "[no screen reported]",
    SCREEN_INFO: "[menu info screen]",
    SCREEN_MENU: "[context menu]",
    SCREEN_INTRO: "[intro screen]",
    SCREEN_ADDRESS: "[address]",
}

# Marks that mean "a different screen is now on display".
MARK_SCREENS = {
    MARK_INFO_OPEN: SCREEN_INFO,
    MARK_MENU_OPEN: SCREEN_MENU,
    MARK_INTRO: SCREEN_INTRO,
    MARK_ADDRESS: SCREEN_ADDRESS,
}

# How long the left button must be held for Shift to engage, in ms. Mirrors
# `ButtonDetails::menu_shift_icon()` in button.rs.
SHIFT_THRESHOLD_MS = 250

# Outcomes of a left-button hold.
HOLD_USED = "used"  # Shift engaged and scrolled back
HOLD_ABANDONED = "abandoned"  # Shift engaged, then released unused
HOLD_TOO_SHORT = "too_short"  # released before Shift engaged, though it was offered
HOLD_HELD_IN_VAIN = "held_in_vain"  # held long, but Shift was not on offer here
HOLD_TAP = "tap"  # a normal short tap


def _mean(values: t.Sequence[int]) -> float | None:
    return sum(values) / len(values) if values else None


def _median(values: t.Sequence[int]) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    mid = len(ordered) // 2
    if len(ordered) % 2:
        return float(ordered[mid])
    return (ordered[mid - 1] + ordered[mid]) / 2


@dataclass
class Event:
    t_ms: int
    code: int
    arg: int

    @property
    def name(self) -> str:
        return EVENT_NAMES.get(self.code, "unknown_%#x" % self.code)

    def describe(self) -> str:
        if self.code in (EV_PRESS, EV_RELEASE, EV_LONG_PRESS, EV_TRIGGER, EV_HTC_ABORT):
            return f"{self.name}({POS_NAMES.get(self.arg, self.arg)})"
        if self.code == EV_SHIFT_BACK:
            return "shift_back"
        if self.code == EV_ACTION:
            return f"action({ACTION_NAMES.get(self.arg, self.arg)})"
        if self.code == EV_MARK:
            return f"mark({MARK_NAMES.get(self.arg, self.arg)})"
        if self.code == EV_PAGE:
            return f"page({self.arg})"
        if self.code == EV_SUBPAGE:
            return f"subpage({self.arg})"
        if self.code == EV_MENU_ITEM:
            return f"menu_item({self.arg})"
        return self.name


@dataclass
class Hold:
    """One press-and-release of a button, and what came of it."""

    screen: int
    button: int
    t_press: int
    duration_ms: int
    outcome: str
    #: When the long-press threshold fired, if it did.
    armed_ms: int | None = None
    #: Scroll-backs performed during this hold (Shift is repeatable).
    shift_backs: int = 0

    @property
    def armed(self) -> bool:
        return self.armed_ms is not None


@dataclass
class ScreenStats:
    """Everything observed while one screen was on display.

    A screen can be visited more than once - via the menu, "AGAIN", or scrolling
    back - so `visits` counts entries and `total_ms` sums their durations.
    """

    page: int
    visits: int = 0
    total_ms: int = 0
    presses: dict[str, int] = field(default_factory=dict)
    #: Milliseconds from entering the screen to the first button press, per
    #: visit. High values mean the user stopped to read or hesitated.
    hesitations: list[int] = field(default_factory=list)
    #: Left-button holds that happened here.
    holds: list[Hold] = field(default_factory=list)
    #: Successful scroll-backs performed with Shift held.
    shift_backs: int = 0
    #: Hold-to-confirm released before it completed.
    hold_aborted: int = 0
    #: Highest sub-page reached, so `1` means the text needed two screens.
    max_subpage: int = 0
    #: Times the selection moved in a choice carousel (the context menu).
    menu_item_moves: int = 0

    @property
    def name(self) -> str:
        if self.page in SYNTHETIC_SCREEN_NAMES:
            return SYNTHETIC_SCREEN_NAMES[self.page]
        if 0 <= self.page < len(SCREEN_NAMES):
            return SCREEN_NAMES[self.page]
        return f"page {self.page}"

    @property
    def total_presses(self) -> int:
        return sum(self.presses.values())

    def holds_with(self, outcome: str) -> list[Hold]:
        return [h for h in self.holds if h.outcome == outcome]

    @property
    def shift_armed(self) -> int:
        return sum(1 for h in self.holds if h.armed)

    @property
    def shift_abandoned(self) -> int:
        return len(self.holds_with(HOLD_ABANDONED))

    @property
    def shift_missed(self) -> int:
        return len(self.holds_with(HOLD_TOO_SHORT))

    @property
    def held_in_vain(self) -> int:
        return len(self.holds_with(HOLD_HELD_IN_VAIN))

    @property
    def touches_shift(self) -> bool:
        return bool(
            self.shift_armed
            or self.shift_backs
            or self.shift_missed
            or self.held_in_vain
        )


@dataclass
class Session:
    events: list[Event]
    dropped: int
    screens: dict[int, ScreenStats]
    status: str | None = None
    #: Event codes the decoder did not recognise (firmware/analysis mismatch).
    unknown_codes: frozenset[int] = frozenset()

    @property
    def duration_ms(self) -> int:
        return self.events[-1].t_ms if self.events else 0

    @property
    def truncated(self) -> bool:
        return self.dropped > 0

    @property
    def ordered_screens(self) -> list[ScreenStats]:
        return sorted(self.screens.values(), key=lambda s: s.page)

    @property
    def all_holds(self) -> list[Hold]:
        return [h for s in self.ordered_screens for h in s.holds]

    @property
    def discovered_shift(self) -> bool:
        return any(h.outcome == HOLD_USED for h in self.all_holds)

    def marks(self) -> list[tuple[int, str]]:
        return [
            (ev.t_ms, MARK_NAMES.get(ev.arg, str(ev.arg)))
            for ev in self.events
            if ev.code == EV_MARK
        ]

    def shift_summary(self) -> dict[str, t.Any]:
        """Aggregate the Shift interaction across the whole walkthrough."""
        holds = self.all_holds
        used = [h for h in holds if h.outcome == HOLD_USED]
        abandoned = [h for h in holds if h.outcome == HOLD_ABANDONED]
        too_short = [h for h in holds if h.outcome == HOLD_TOO_SHORT]
        in_vain = [h for h in holds if h.outcome == HOLD_HELD_IN_VAIN]

        # An "attempt" is a hold where Shift was on offer: either it engaged, or
        # the user let go too early.
        armed = [h for h in holds if h.armed]
        attempts = len(armed) + len(too_short)

        # How long it took to get the first scroll-back after arriving on the
        # screen that needs it.
        time_to_first = None
        first_used = next((h for h in used), None)
        if first_used is not None:
            screen = self.screens.get(first_used.screen)
            if screen is not None and screen.visits:
                # Approximate the screen's first entry from the earliest event
                # attributed to it: the press that began the successful hold
                # minus the accumulated hesitation is not knowable exactly, so
                # report the absolute timestamp of the first success instead.
                time_to_first = first_used.t_press

        return {
            "discovered": self.discovered_shift,
            "attempts": attempts,
            "armed": len(armed),
            "used": len(used),
            "abandoned": len(abandoned),
            "released_too_early": len(too_short),
            "held_where_unavailable": len(in_vain),
            "scroll_backs": sum(s.shift_backs for s in self.screens.values()),
            "max_scroll_backs_in_one_hold": max(
                (h.shift_backs for h in holds), default=0
            ),
            "success_rate": (len(armed) / attempts) if attempts else None,
            "first_success_at_ms": time_to_first,
            "hold_ms": {
                "used": {
                    "mean": _mean([h.duration_ms for h in used]),
                    "median": _median([h.duration_ms for h in used]),
                },
                "released_too_early": {
                    "mean": _mean([h.duration_ms for h in too_short]),
                    "median": _median([h.duration_ms for h in too_short]),
                    "max": max((h.duration_ms for h in too_short), default=None),
                },
                "held_where_unavailable": {
                    "mean": _mean([h.duration_ms for h in in_vain]),
                    "max": max((h.duration_ms for h in in_vain), default=None),
                },
            },
        }

    def to_dict(self) -> dict[str, t.Any]:
        """JSON-friendly form, for aggregating several test participants."""
        return {
            "status": self.status,
            "duration_ms": self.duration_ms,
            "dropped_events": self.dropped,
            "truncated": self.truncated,
            "shift": self.shift_summary(),
            "marks": [{"t_ms": t_ms, "mark": name} for t_ms, name in self.marks()],
            "screens": [
                {
                    "page": s.page,
                    "name": s.name,
                    "visits": s.visits,
                    "total_ms": s.total_ms,
                    "presses": s.presses,
                    "total_presses": s.total_presses,
                    "hesitation_ms": s.hesitations,
                    "shift_armed": s.shift_armed,
                    "shift_backs": s.shift_backs,
                    "shift_abandoned": s.shift_abandoned,
                    "shift_released_too_early": s.shift_missed,
                    "held_where_unavailable": s.held_in_vain,
                    "hold_aborted": s.hold_aborted,
                    "max_subpage": s.max_subpage,
                    "menu_item_moves": s.menu_item_moves,
                    "holds": [
                        {
                            "t_ms": h.t_press,
                            "duration_ms": h.duration_ms,
                            "outcome": h.outcome,
                            "armed_ms": h.armed_ms,
                            "shift_backs": h.shift_backs,
                        }
                        for h in s.holds
                    ],
                }
                for s in self.ordered_screens
            ],
            "events": [{"t_ms": ev.t_ms, "event": ev.describe()} for ev in self.events],
        }


def parse_events(log: str) -> tuple[list[Event], int]:
    """Split an encoded log into events and the dropped-event count."""
    parts = log.strip().split("|")
    if len(parts) != 3 or parts[0] != LOG_VERSION:
        raise ValueError(f"not a {LOG_VERSION} log")
    dropped = int(parts[1])
    events = []
    for chunk in parts[2].split(";"):
        if not chunk:
            continue
        t_ms, code, arg = (int(x) for x in chunk.split(","))
        events.append(Event(t_ms, code, arg))
    return events, dropped


def parse_serial(text: str) -> list[list[Event]]:
    """Extract event streams from a captured serial/debug-console transcript.

    The device also streams every event to its USB serial port as
    ``NAVTEL <t_ms> <code> <arg>``, which lets a session be recovered even if it
    was interrupted before the tutorial returned its log. Lines that are not
    ours are ignored, so a transcript containing other log output is fine.

    Returns one list of events per recorded session (the timestamps restart from
    zero each time the tutorial is launched). Console output is best-effort, so a
    transcript may be missing lines that the returned log would have contained.
    """
    sessions: list[list[Event]] = []
    for line in text.splitlines():
        index = line.find(SERIAL_TAG)
        if index < 0:
            continue
        fields = line[index + len(SERIAL_TAG) :].split()
        if len(fields) < 3:
            continue
        try:
            t_ms, code, arg = (int(x) for x in fields[:3])
        except ValueError:
            continue
        if code == EV_SESSION_START or not sessions:
            sessions.append([])
        sessions[-1].append(Event(t_ms, code, arg))
    return sessions


class _Decoder:
    """Walks the event stream, attributing everything to the screen on display."""

    def __init__(self, events: list[Event], threshold_ms: int) -> None:
        self.events = events
        self.threshold_ms = threshold_ms
        self.screens: dict[int, ScreenStats] = {}
        self.screen: int | None = None
        self.entered_at = 0
        self.pressed_in_visit = False
        # A left hold in progress: press time, whether Shift was on offer, when
        # it armed, and how many scroll-backs it produced.
        self.press_t: dict[int, int] = {}
        self.press_screen: dict[int, int] = {}
        self.armed_at: int | None = None
        self.shift_backs_in_hold = 0
        self.shift_offered = False
        self.unknown_codes: set[int] = set()

    def stats(self, page: int) -> ScreenStats:
        return self.screens.setdefault(page, ScreenStats(page=page))

    def enter(self, page: int, t_ms: int) -> None:
        """Close the current screen's visit and open one for `page`."""
        self.leave(t_ms)
        self.screen = page
        self.entered_at = t_ms
        self.pressed_in_visit = False
        self.stats(page).visits += 1

    def leave(self, t_ms: int) -> None:
        if self.screen is not None:
            self.stats(self.screen).total_ms += t_ms - self.entered_at

    def run(self) -> dict[int, ScreenStats]:
        for ev in self.events:
            if ev.code == EV_PAGE:
                self.enter(ev.arg, ev.t_ms)
                self.shift_offered = False
            elif ev.code == EV_SUBPAGE:
                cur = self.current()
                if cur is not None:
                    cur.max_subpage = max(cur.max_subpage, ev.arg)
            elif ev.code == EV_SHIFT_AVAIL:
                # The firmware reports this directly, so we never have to infer
                # whether a hold could have done anything on this screen.
                self.shift_offered = bool(ev.arg)
            elif ev.code == EV_MARK:
                self._on_mark(ev)
            elif ev.code == EV_PRESS:
                self._on_press(ev)
            elif ev.code == EV_RELEASE:
                self._on_release(ev)
            elif ev.code == EV_LONG_PRESS:
                if ev.arg == POS_LEFT:
                    self.armed_at = ev.t_ms
            elif ev.code == EV_SHIFT_BACK:
                self.shift_backs_in_hold += 1
                cur = self.current()
                if cur is not None:
                    cur.shift_backs += 1
            elif ev.code == EV_HTC_ABORT:
                cur = self.current()
                if cur is not None:
                    cur.hold_aborted += 1
            elif ev.code == EV_MENU_ITEM:
                cur = self.current()
                if cur is not None:
                    cur.menu_item_moves += 1
            elif ev.code not in EVENT_NAMES:
                # A code this decoder has no name for means the firmware and the
                # analysis disagree. Surface it rather than dropping it silently.
                # Known codes without a branch here (session_start, shift_end)
                # need no handling - they are read from the event list directly.
                self.unknown_codes.add(ev.code)

        if self.events:
            self.leave(self.events[-1].t_ms)
        return self.screens

    def current(self) -> ScreenStats:
        if self.screen is None:
            # No screen has announced itself yet. Keep the data anyway - losing
            # it silently would look exactly like "the user did nothing".
            return self.stats(SCREEN_UNATTRIBUTED)
        return self.stats(self.screen)

    def _on_mark(self, ev: Event) -> None:
        # Screens that are their own layout - the info screen, the context menu,
        # the address - are announced by a mark rather than a page event, since
        # only the tutorial's Flow has page indices.
        screen = MARK_SCREENS.get(ev.arg)
        if screen is not None:
            self.enter(screen, ev.t_ms)
            # A new screen starts without Shift until the firmware says so.
            self.shift_offered = False

    def _on_press(self, ev: Event) -> None:
        cur = self.current()
        if cur is not None:
            name = POS_NAMES.get(ev.arg, str(ev.arg))
            cur.presses[name] = cur.presses.get(name, 0) + 1
            if not self.pressed_in_visit:
                cur.hesitations.append(ev.t_ms - self.entered_at)
                self.pressed_in_visit = True
        self.press_t[ev.arg] = ev.t_ms
        if self.screen is not None:
            self.press_screen[ev.arg] = self.screen
        if ev.arg == POS_LEFT:
            self.armed_at = None
            self.shift_backs_in_hold = 0

    def _on_release(self, ev: Event) -> None:
        t_press = self.press_t.pop(ev.arg, None)
        screen = self.press_screen.pop(ev.arg, None)
        if t_press is None or ev.arg != POS_LEFT:
            return
        duration = ev.t_ms - t_press
        if self.armed_at is not None:
            outcome = HOLD_USED if self.shift_backs_in_hold else HOLD_ABANDONED
        elif self.shift_offered:
            # Let go before Shift could engage, so this opened the menu even
            # though scrolling back was probably the intent.
            outcome = HOLD_TOO_SHORT
        elif duration >= self.threshold_ms:
            # Deliberately held where Shift is not on offer - a sign the user
            # expected the modifier to work here.
            outcome = HOLD_HELD_IN_VAIN
        else:
            outcome = HOLD_TAP
        # Charge the hold to the screen it started on.
        target = self.stats(screen) if screen is not None else self.current()
        if target is not None:
            target.holds.append(
                Hold(
                    screen=target.page,
                    button=ev.arg,
                    t_press=t_press,
                    duration_ms=duration,
                    outcome=outcome,
                    armed_ms=(
                        self.armed_at - t_press if self.armed_at is not None else None
                    ),
                    shift_backs=self.shift_backs_in_hold,
                )
            )
        self.armed_at = None
        self.shift_backs_in_hold = 0


def decode(
    log: str,
    status: str | None = None,
    threshold_ms: int = SHIFT_THRESHOLD_MS,
) -> Session:
    """Decode a log and derive per-screen usability statistics."""
    events, dropped = parse_events(log)
    decoder = _Decoder(events, threshold_ms)
    screens = decoder.run()
    return Session(
        events=events,
        dropped=dropped,
        screens=screens,
        status=status,
        unknown_codes=frozenset(decoder.unknown_codes),
    )


def decode_serial(
    text: str,
    status: str | None = None,
    threshold_ms: int = SHIFT_THRESHOLD_MS,
) -> list[Session]:
    """Decode every session found in a captured serial transcript."""
    return [
        Session(
            events=events,
            dropped=0,
            screens=_Decoder(events, threshold_ms).run(),
            status=status,
        )
        for events in parse_serial(text)
    ]


def _fmt_ms(value: float | None) -> str:
    return "-" if value is None else f"{value:.0f}ms"


def format_report(session: Session) -> str:
    """Render a human-readable summary of one walkthrough."""
    lines = []
    lines.append(
        f"Tutorial {session.status or 'result'} - took "
        f"{session.duration_ms / 1000:.1f}s"
    )
    if session.truncated:
        lines.append(f"WARNING: log full, {session.dropped} later events were dropped")
    if not session.events:
        lines.append(
            "WARNING: the log is empty - the device recorded nothing. Check that "
            "the firmware on the device is the one that was built with this "
            "checkout (see `--raw` for the log as returned)."
        )
    elif session.unknown_codes:
        codes = ", ".join(f"{c:#04x}" for c in sorted(session.unknown_codes))
        lines.append(
            f"WARNING: the log contains event codes this decoder does not know "
            f"({codes}). The firmware and this analysis are out of step - "
            f"rebuild and reflash from the same checkout."
        )
    elif SCREEN_UNATTRIBUTED in session.screens:
        lines.append(
            "WARNING: the device reported button presses but never said which "
            "screen was on display, so they could not be attributed. This means "
            "the firmware is older than the analysis - reflash and retest."
        )
    lines.append("")

    header = (
        f"{'screen':<22}{'time':>8}{'visits':>7}{'wait':>8}  {'presses':<24}{'notes'}"
    )
    lines.append(header)
    lines.append("-" * len(header))
    for s in session.ordered_screens:
        presses = ", ".join(f"{k} x{v}" for k, v in sorted(s.presses.items()))
        wait = _median(s.hesitations)
        notes = []
        if s.max_subpage:
            notes.append(f"{s.max_subpage + 1} sub-pages")
        if s.menu_item_moves:
            notes.append(f"{s.menu_item_moves} item moves")
        if s.hold_aborted:
            notes.append(f"{s.hold_aborted} hold aborted")
        lines.append(
            f"{s.name[:21]:<22}{s.total_ms / 1000:>7.1f}s{s.visits:>7}"
            f"{_fmt_ms(wait):>8}  {presses:<24}{', '.join(notes)}"
        )
    lines.append("")
    lines.append('"wait" is the median pause before the first press on a visit.')

    shift = session.shift_summary()
    lines.append("")
    lines.append("Shift (hold left) and scroll back")
    lines.append("-" * 33)
    if not shift["attempts"] and not shift["held_where_unavailable"]:
        lines.append("  The user never tried holding the left button.")
    else:
        verdict = "yes" if shift["discovered"] else "NO"
        lines.append(f"  Ever used it successfully: {verdict}")
        rate = shift["success_rate"]
        lines.append(
            f"  Hold attempts reaching the {SHIFT_THRESHOLD_MS}ms threshold: "
            f"{shift['armed']}/{shift['attempts']}"
            + (f" ({100 * rate:.0f}%)" if rate is not None else "")
        )
        lines.append(
            f"  Released too early (opened the menu instead): "
            f"{shift['released_too_early']}"
            f"  [held {_fmt_ms(shift['hold_ms']['released_too_early']['median'])} "
            f"median, longest "
            f"{_fmt_ms(shift['hold_ms']['released_too_early']['max'])}]"
        )
        lines.append(
            f"  Armed but released without scrolling: {shift['abandoned']}"
        )
        lines.append(
            f"  Scroll-backs performed: {shift['scroll_backs']}"
            f" (up to {shift['max_scroll_backs_in_one_hold']} in a single hold)"
        )
        if shift["held_where_unavailable"]:
            lines.append(
                f"  Held the left button where Shift is not offered: "
                f"{shift['held_where_unavailable']}"
                f"  [up to {_fmt_ms(shift['hold_ms']['held_where_unavailable']['max'])}]"
                " - they expected it to work there"
            )
        if shift["first_success_at_ms"] is not None:
            lines.append(
                f"  First successful scroll-back at "
                f"{shift['first_success_at_ms'] / 1000:.1f}s into the session"
            )

    per_screen = [s for s in session.ordered_screens if s.touches_shift]
    if per_screen:
        lines.append("")
        lines.append("  by screen:")
        for s in per_screen:
            lines.append(
                f"    {s.name[:21]:<22} armed {s.shift_armed}, "
                f"scrolled back {s.shift_backs}, "
                f"unused {s.shift_abandoned}, "
                f"too early {s.shift_missed}, "
                f"in vain {s.held_in_vain}"
            )

    marks = session.marks()
    if marks:
        lines.append("")
        lines.append("Milestones")
        lines.append("-" * 10)
        for t_ms, name in marks:
            lines.append(f"  {t_ms / 1000:>7.1f}s  {name}")

    return "\n".join(lines)


def format_events(session: Session) -> str:
    """Render the raw event timeline, one event per line."""
    return "\n".join(
        f"{ev.t_ms / 1000:>8.2f}s  {ev.describe()}" for ev in session.events
    )
