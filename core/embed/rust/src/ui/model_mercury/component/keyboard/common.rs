use crate::{
    time::Duration,
    ui::{
        component::{text::common::TextEdit, Event, EventCtx, Timer},
        display::{Color, Font},
        geometry::{Alignment2D, Offset, Point, Rect},
        shape::{self, Renderer},
    },
};

use super::super::ButtonStyle;

/// Contains state commonly used in implementations multi-tap keyboards.
pub struct MultiTapKeyboard {
    /// Configured timeout after which we cancel currently pending key.
    timeout: Duration,
    /// The currently pending state.
    pending: Option<Pending>,
    /// Timer for clearing the pending state.
    timer: Timer,
}

struct Pending {
    /// Index of the pending key.
    key: usize,
    /// Index of the key press (how many times the `key` was pressed, minus
    /// one).
    press: usize,
}

impl MultiTapKeyboard {
    /// Create a new, empty, multi-tap state.
    pub fn new() -> Self {
        Self {
            timeout: Duration::from_secs(1),
            pending: None,
            timer: Timer::new(),
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

    /// Returns `true` if `event` is an `Event::Timer` for the currently pending
    /// timer.
    pub fn timeout_event(&mut self, event: Event) -> bool {
        self.timer.expire(event)
    }

    /// Reset to the empty state. Takes `EventCtx` to request a paint pass (to
    /// either hide or show any pending marker our caller might want to draw
    /// later).
    pub fn clear_pending_state(&mut self, ctx: &mut EventCtx) {
        self.timer.stop();
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
        // reset the pending state after a timeout.
        //
        // Note: It might seem that we should make sure to `request_paint` in case we
        // progress into a pending state (to display the pending marker), but such
        // transition only happens as a result of an append op, so the painting should
        // be requested by handling the `TextEdit`.
        self.pending = if key_text.len() > 1 {
            self.timer.start(ctx, self.timeout);
            Some(Pending { key, press })
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

/// Create a pill-shaped button around a text.
pub fn render_pill_shape<'s>(
    target: &mut impl Renderer<'s>,
    base_point: Point,
    text: &str,
    style: &ButtonStyle,
    expand_area: Option<Rect>,
) {
    let pill_radius = 18;
    let pill_bearing_x = 17;
    let pill_bearing_y = 12;
    let pill_height = 2 * pill_radius + 4; // adding 4px looks better, if the height is just 2*r it does not look like a
                                           // perfect half-circle but there is a visible narrowing of the pill shape
    let pill_width = style.font.text_width(text) + 2 * pill_bearing_x;

    let pill_baseline = base_point + Offset::new(-pill_bearing_x, pill_bearing_y);
    let mut pill_area = Rect::snap(
        pill_baseline,
        Offset::new(pill_width, pill_height),
        Alignment2D::BOTTOM_LEFT,
    );
    if let Some(area) = expand_area {
        // "dummy" rectangle to use in the `union` call
        let expander = Rect::snap(
            area.bottom_right(),
            Offset::uniform(1),
            Alignment2D::BOTTOM_RIGHT,
        );
        pill_area = pill_area.union(expander);
    }
    shape::Bar::new(pill_area)
        .with_bg(style.background_color)
        .with_fg(style.button_color)
        .with_radius(pill_radius)
        .with_thickness(2)
        .render(target);
}
