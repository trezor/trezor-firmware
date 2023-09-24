use crate::{
    time::Duration,
    ui::{
        component::{text::common::TextEdit, Event, EventCtx, TimerToken},
        display::{self, Color, Font},
        geometry::{Offset, Point, Rect},
        shape,
        shape::Renderer,
    },
};

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
        // reset the pending state after it elapses.
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

/// Create a visible "underscoring" of the last letter of a text.
pub fn render_pending_marker<'s>(
    target: &mut impl Renderer<'s>,
    text_baseline: Point,
    text: &str,
    font: Font,
    color: Color,
) {
    // Measure the width of the last character of input.
    if let Some(last) = text.chars().last() {
        let width = font.text_width(text);
        let last_width = font.char_width(last);
        // Draw the marker 2px under the start of the baseline of the last character.
        let marker_origin = text_baseline + Offset::new(width - last_width, 2);
        // Draw the marker 1px longer than the last character, and 3px thick.
        let marker_rect =
            Rect::from_top_left_and_size(marker_origin, Offset::new(last_width + 1, 3));
        shape::Bar::new(marker_rect).with_bg(color).render(target);
    }
}
