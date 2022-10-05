use heapless::String;

use crate::{
    time::Duration,
    ui::{
        component::{Event, EventCtx, TimerToken},
        display::{self, Color, Font},
        geometry::{Offset, Point, Rect},
        util::ResultExt,
    },
};

pub const HEADER_HEIGHT: i16 = 25;
pub const HEADER_PADDING_SIDE: i16 = 5;
pub const HEADER_PADDING_BOTTOM: i16 = 12;

/// Contains state commonly used in implementations multi-tap keyboards.
pub struct MultiTapKeyboard {
    /// Configured timeout after which we cancel currently pending key.
    timeout: Duration,
    /// The currently pending state.
    pending: Option<Pending>,
}

struct Pending {
    /// Index of the pending key.
    key: usize,
    /// Index of the key press (how many times the `key` was pressed, minus
    /// one).
    press: usize,
    /// Timer for clearing the pending state.
    timer: TimerToken,
}

impl MultiTapKeyboard {
    /// Create a new, empty, multi-tap state.
    pub fn new() -> Self {
        Self {
            timeout: Duration::from_secs(1),
            pending: None,
        }
    }

    /// Return the index of the currently pending key, if any.
    pub fn pending_key(&self) -> Option<usize> {
        self.pending.as_ref().map(|p| p.key)
    }

    /// Return the index of the pending key press.
    pub fn pending_press(&self) -> Option<usize> {
        self.pending.as_ref().map(|p| p.press)
    }

    /// Return the token for the currently pending timer.
    pub fn pending_timer(&self) -> Option<TimerToken> {
        self.pending.as_ref().map(|p| p.timer)
    }

    /// Returns `true` if `event` is an `Event::Timer` for the currently pending
    /// timer.
    pub fn is_timeout_event(&self, event: Event) -> bool {
        matches!((event, self.pending_timer()), (Event::Timer(t), Some(pt)) if pt == t)
    }

    /// Reset to the empty state. Takes `EventCtx` to request a paint pass (to
    /// either hide or show any pending marker our caller might want to draw
    /// later).
    pub fn clear_pending_state(&mut self, ctx: &mut EventCtx) {
        if self.pending.is_some() {
            self.pending = None;
            ctx.request_paint();
        }
    }

    /// Register a click to a key. `MultiTapKeyboard` itself does not have any
    /// concept of the key set, so both the key index and the key content is
    /// taken here. Returns a text editing operation the caller should apply on
    /// the output buffer. Takes `EventCtx` to request a timeout for cancelling
    /// the pending state. Caller is required to handle the timer event and
    /// call `Self::clear_pending_state` when the timer hits.
    pub fn click_key(&mut self, ctx: &mut EventCtx, key: usize, key_text: &str) -> TextEdit {
        let (is_pending, press) = match &self.pending {
            Some(pending) if pending.key == key => {
                // This key is pending. Cycle the last inserted character through the
                // key content.
                (true, pending.press.wrapping_add(1))
            }
            _ => {
                // This key is not pending. Append the first character in the key.
                (false, 0)
            }
        };

        // If the key has more then one character, we need to set it as pending, so we
        // can cycle through on the repeated clicks. We also request a timer so we can
        // reset the pending state after a deadline.
        //
        // Note: It might seem that we should make sure to `request_paint` in case we
        // progress into a pending state (to display the pending marker), but such
        // transition only happens as a result of an append op, so the painting should
        // be requested by handling the `TextEdit`.
        self.pending = if key_text.len() > 1 {
            Some(Pending {
                key,
                press,
                timer: ctx.request_timer(self.timeout),
            })
        } else {
            None
        };

        assert!(!key_text.is_empty());
        // Now we can be sure that a looped iterator will return a value
        let ch = unwrap!(key_text.chars().cycle().nth(press));
        if is_pending {
            TextEdit::ReplaceLast(ch)
        } else {
            TextEdit::Append(ch)
        }
    }
}

/// Reified editing operations of `TextBox`.
///
/// Note: This does not contain all supported editing operations, only the ones
/// we currently use.
pub enum TextEdit {
    ReplaceLast(char),
    Append(char),
}

/// Wraps a character buffer of maximum length `L` and provides text editing
/// operations over it. Text ops usually take a `EventCtx` to request a paint
/// pass in case of any state modification.
pub struct TextBox<const L: usize> {
    text: String<L>,
}

impl<const L: usize> TextBox<L> {
    /// Create a new `TextBox` with content `text`.
    pub fn new(text: String<L>) -> Self {
        Self { text }
    }

    /// Create an empty `TextBox`.
    pub fn empty() -> Self {
        Self::new(String::new())
    }

    pub fn content(&self) -> &str {
        &self.text
    }

    pub fn is_empty(&self) -> bool {
        self.text.is_empty()
    }

    pub fn is_full(&self) -> bool {
        self.text.len() == self.text.capacity()
    }

    /// Delete the last character of content, if any.
    pub fn delete_last(&mut self, ctx: &mut EventCtx) {
        let changed = self.text.pop().is_some();
        if changed {
            ctx.request_paint();
        }
    }

    /// Replaces the last character of the content with `ch`. If the content is
    /// empty, `ch` is appended.
    pub fn replace_last(&mut self, ctx: &mut EventCtx, ch: char) {
        let previous = self.text.pop();
        self.text
            .push(ch)
            .assert_if_debugging_ui("TextBox has zero capacity");
        let changed = previous != Some(ch);
        if changed {
            ctx.request_paint();
        }
    }

    /// Append `ch` at the end of the content.
    pub fn append(&mut self, ctx: &mut EventCtx, ch: char) {
        self.text.push(ch).assert_if_debugging_ui("TextBox is full");
        ctx.request_paint();
    }

    /// Replace the textbox content with `text`.
    pub fn replace(&mut self, ctx: &mut EventCtx, text: &str) {
        if self.text != text {
            self.text.clear();
            self.text
                .push_str(text)
                .assert_if_debugging_ui("TextBox is full");
            ctx.request_paint();
        }
    }

    /// Clear the textbox content.
    pub fn clear(&mut self, ctx: &mut EventCtx) {
        self.replace(ctx, "");
    }

    /// Apply a editing operation to the text buffer.
    pub fn apply(&mut self, ctx: &mut EventCtx, edit: TextEdit) {
        match edit {
            TextEdit::ReplaceLast(char) => self.replace_last(ctx, char),
            TextEdit::Append(char) => self.append(ctx, char),
        }
    }
}

/// Create a visible "underscoring" of the last letter of a text.
pub fn paint_pending_marker(text_baseline: Point, text: &str, font: Font, color: Color) {
    // Measure the width of the last character of input.
    if let Some(last) = text.chars().last() {
        let width = font.text_width(text);
        let last_width = font.char_width(last);
        // Draw the marker 2px under the start of the baseline of the last character.
        let marker_origin = text_baseline + Offset::new(width - last_width, 2);
        // Draw the marker 1px longer than the last character, and 3px thick.
        let marker_rect =
            Rect::from_top_left_and_size(marker_origin, Offset::new(last_width + 1, 3));
        display::rect_fill(marker_rect, color);
    }
}
