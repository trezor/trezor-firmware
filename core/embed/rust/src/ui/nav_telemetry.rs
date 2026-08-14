//! Debug-only recorder for the caesar navigation user study.
//!
//! `trezorctl debug nav-tutorial` starts the recorder, the UI appends
//! timestamped events while the user walks through the tutorial, and the log is
//! returned to the host at the end for offline analysis.
//!
//! The recorder is a global because the tutorial destroys and re-creates its
//! whole layout every time the context menu is opened, so per-component state
//! would not survive. Recording is off until `start()` is called, so ordinary
//! firmware use records nothing.
//!
//! Event codes are part of the wire format - keep them in sync with the decoder
//! in `python/src/trezorlib/nav_telemetry.py`.

/// Line prefix used when streaming events to the debug console, so they can be
/// picked out of a serial capture that also carries other log output.
pub const SERIAL_TAG: &str = "NAVTEL";

/// Recording began (arg: unused).
pub const EV_SESSION_START: u8 = 0x01;
/// The flow moved to a tutorial page (arg: page index).
pub const EV_PAGE: u8 = 0x02;
/// The flow moved to a sub-page of the current page (arg: sub-page index).
pub const EV_SUBPAGE: u8 = 0x03;
/// Whether the left button currently offers "Shift" (arg: 1 available, 0 not).
/// Recorded whenever it changes, so the decoder never has to guess whether a
/// hold could have done anything.
pub const EV_SHIFT_AVAIL: u8 = 0x04;

/// A physical button went down (arg: `POS_*`).
pub const EV_PRESS: u8 = 0x10;
/// A physical button came up (arg: `POS_*`).
pub const EV_RELEASE: u8 = 0x11;
/// A button was held past its long-press threshold, so "Shift" became available
/// (arg: `POS_*`). Not every press reaches this.
pub const EV_LONG_PRESS: u8 = 0x12;
/// The secondary ("scroll back") action fired while Shift was held (arg:
/// `POS_*`).
pub const EV_SHIFT_BACK: u8 = 0x13;
/// Shift was let go, leaving shift mode (arg: unused).
pub const EV_SHIFT_END: u8 = 0x14;
/// A button release actually triggered its action (arg: `POS_*`).
pub const EV_TRIGGER: u8 = 0x15;
/// A hold-to-confirm button was released before confirming (arg: `POS_*`).
pub const EV_HTC_ABORT: u8 = 0x16;

/// The flow performed a navigation action (arg: `ACT_*`).
pub const EV_ACTION: u8 = 0x20;
/// A different item became selected in a choice carousel, e.g. the context menu
/// (arg: item index).
pub const EV_MENU_ITEM: u8 = 0x21;
/// A milestone marked from Python (arg: caller-defined, see `nav_tutorial.py`).
pub const EV_MARK: u8 = 0x30;

// Button positions, used as the `arg` of the button events.
pub const POS_LEFT: u8 = 0;
pub const POS_MIDDLE: u8 = 1;
pub const POS_RIGHT: u8 = 2;
pub const POS_OTHER: u8 = 3;

// Navigation actions, used as the `arg` of `EV_ACTION`.
pub const ACT_NEXT_PAGE: u8 = 0;
pub const ACT_PREV_PAGE: u8 = 1;
pub const ACT_FIRST_PAGE: u8 = 2;
pub const ACT_LAST_PAGE: u8 = 3;
pub const ACT_CONFIRM: u8 = 4;
pub const ACT_CANCEL: u8 = 5;
pub const ACT_INFO: u8 = 6;

#[cfg(feature = "ui_debug")]
pub use imp::{dropped, events, record, start, stop, Event};

#[cfg(feature = "ui_debug")]
mod imp {
    use crate::trezorhal::time;

    /// How many events fit in the log. Anything beyond is counted as dropped so
    /// the decoder can tell a truncated session from a complete one.
    const MAX_EVENTS: usize = 256;

    #[derive(Copy, Clone)]
    pub struct Event {
        /// Milliseconds since `start()`.
        pub t_ms: u32,
        pub code: u8,
        pub arg: u8,
    }

    struct Recorder {
        events: [Event; MAX_EVENTS],
        len: usize,
        dropped: u16,
        start_ms: u32,
        enabled: bool,
    }

    static mut RECORDER: Recorder = Recorder {
        events: [Event {
            t_ms: 0,
            code: 0,
            arg: 0,
        }; MAX_EVENTS],
        len: 0,
        dropped: 0,
        start_ms: 0,
        enabled: false,
    };

    fn recorder() -> &'static mut Recorder {
        // SAFETY: single-threaded access
        unsafe { &mut *core::ptr::addr_of_mut!(RECORDER) }
    }

    /// Discard any previous log and begin recording.
    pub fn start() {
        let rec = recorder();
        rec.len = 0;
        rec.dropped = 0;
        rec.start_ms = time::ticks_ms();
        rec.enabled = true;
        record(super::EV_SESSION_START, 0);
    }

    /// Stop recording. The log is kept so it can still be read.
    pub fn stop() {
        recorder().enabled = false;
    }

    /// Append an event, unless recording is off or the log is full.
    ///
    /// The event is also printed to the debug console, so a moderator can watch
    /// the walkthrough live over the USB serial port without any host tooling -
    /// and still have a transcript if the session is interrupted before the
    /// tutorial returns its log. Console output is best-effort: it is
    /// non-blocking, so lines can be dropped if nothing is reading the port.
    pub fn record(code: u8, arg: u8) {
        let rec = recorder();
        if !rec.enabled {
            return;
        }
        let t_ms = time::ticks_ms().wrapping_sub(rec.start_ms);
        dbg_println!("{} {} {} {}", super::SERIAL_TAG, t_ms, code, arg);
        if rec.len >= MAX_EVENTS {
            rec.dropped = rec.dropped.saturating_add(1);
            return;
        }
        rec.events[rec.len] = Event { t_ms, code, arg };
        rec.len += 1;
    }

    pub fn events() -> &'static [Event] {
        let rec = recorder();
        &rec.events[..rec.len]
    }

    pub fn dropped() -> u16 {
        recorder().dropped
    }
}

#[cfg(not(feature = "ui_debug"))]
pub fn start() {}

#[cfg(not(feature = "ui_debug"))]
pub fn stop() {}

#[cfg(not(feature = "ui_debug"))]
pub fn record(_code: u8, _arg: u8) {}
