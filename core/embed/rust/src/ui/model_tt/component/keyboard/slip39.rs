use core::iter;

use heapless::String;

use crate::{
    trezorhal::slip39,
    ui::{
        component::{
            text::common::{TextBox, TextEdit},
            Component, Event, EventCtx,
        },
        display,
        geometry::{Alignment2D, Offset, Rect},
        model_tt::{
            component::{
                keyboard::{
                    common::{paint_pending_marker, MultiTapKeyboard},
                    mnemonic::{MnemonicInput, MnemonicInputMsg, MNEMONIC_KEY_COUNT},
                },
                Button, ButtonContent, ButtonMsg,
            },
            theme,
        },
        util::ResultExt,
    },
};

const MAX_LENGTH: usize = 8;

pub struct Slip39Input {
    button: Button<&'static str>,
    textbox: TextBox<MAX_LENGTH>,
    multi_tap: MultiTapKeyboard,
    final_word: Option<&'static str>,
    input_mask: Slip39Mask,
}

impl MnemonicInput for Slip39Input {
    /// Return the key set. Keys are further specified as indices into this
    /// array.
    fn keys() -> [&'static str; MNEMONIC_KEY_COUNT] {
        ["ab", "cd", "ef", "ghij", "klm", "nopq", "rs", "tuv", "wxyz"]
    }

    /// Returns `true` if given key index can continue towards a valid mnemonic
    /// word, `false` otherwise.
    fn can_key_press_lead_to_a_valid_word(&self, key: usize) -> bool {
        if self.input_mask.is_final() {
            false
        } else {
            // Currently pending key is always enabled.
            // Keys that mach the completion mask are enabled as well.
            self.multi_tap.pending_key() == Some(key) || self.input_mask.contains_key(key)
        }
    }

    /// Key button was clicked. If this button is pending, let's cycle the
    /// pending character in textbox. If not, let's just append the first
    /// character.
    fn on_key_click(&mut self, ctx: &mut EventCtx, key: usize) {
        let edit = self.multi_tap.click_key(ctx, key, Self::keys()[key]);
        if let TextEdit::Append(_) = edit {
            // This key press wasn't just a pending key rotation, so let's push the key
            // digit to the buffer.
            self.textbox.append(ctx, Self::key_digit(key));
        } else {
            // Ignore the pending char rotation. We use the pending key to paint
            // the last character, but the mnemonic word computation depends
            // only on the pressed key, not on the specific character inside it.
            // Request paint of pending char.
            ctx.request_paint();
        }
        self.complete_word_from_dictionary(ctx);
    }

    /// Backspace button was clicked, let's delete the last character of input
    /// and clear the pending marker.
    fn on_backspace_click(&mut self, ctx: &mut EventCtx) {
        self.multi_tap.clear_pending_state(ctx);
        self.textbox.delete_last(ctx);
        self.complete_word_from_dictionary(ctx);
    }

    /// Backspace button was long pressed, let's delete all characters of input
    /// and clear the pending marker.
    fn on_backspace_long_press(&mut self, ctx: &mut EventCtx) {
        self.multi_tap.clear_pending_state(ctx);
        self.textbox.clear(ctx);
        self.complete_word_from_dictionary(ctx);
    }

    fn is_empty(&self) -> bool {
        self.textbox.is_empty()
    }

    fn mnemonic(&self) -> Option<&'static str> {
        self.final_word
    }
}

impl Component for Slip39Input {
    type Msg = MnemonicInputMsg;

    fn place(&mut self, bounds: Rect) -> Rect {
        self.button.place(bounds)
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        if self.multi_tap.is_timeout_event(event) {
            // Timeout occurred. Reset the pending key.
            self.multi_tap.clear_pending_state(ctx);
            return Some(MnemonicInputMsg::TimedOut);
        }
        if let Some(ButtonMsg::Clicked) = self.button.event(ctx, event) {
            // Input button was clicked.  If the whole word is totally identified, let's
            // confirm it, otherwise don't do anything.
            if self.input_mask.is_final() {
                return Some(MnemonicInputMsg::Confirmed);
            }
        }
        None
    }

    fn paint(&mut self) {
        let area = self.button.area();
        let style = self.button.style();

        // First, paint the button background.
        self.button.paint_background(style);

        // Content starts in the left-center point, offset by 16px to the right and 8px
        // to the bottom.
        let text_baseline = area.top_left().center(area.bottom_left()) + Offset::new(16, 8);

        // To simplify things, we always copy the printed string here, even if it
        // wouldn't be strictly necessary.
        let mut text: String<MAX_LENGTH> = String::new();

        if let Some(word) = self.final_word {
            // We're done with input, paint the full word.
            text.push_str(word)
                .assert_if_debugging_ui("Text buffer is too small");
        } else {
            // Paint an asterisk for each letter of input.
            for ch in iter::repeat('*').take(self.textbox.content().len()) {
                text.push(ch)
                    .assert_if_debugging_ui("Text buffer is too small");
            }
            // If we're in the pending state, paint the pending character at the end.
            if let (Some(key), Some(press)) =
                (self.multi_tap.pending_key(), self.multi_tap.pending_press())
            {
                assert!(!Self::keys()[key].is_empty());
                // Now we can be sure that the looped iterator will return a value.
                let ch = unwrap!(Self::keys()[key].chars().cycle().nth(press));
                text.pop();
                text.push(ch)
                    .assert_if_debugging_ui("Text buffer is too small");
            }
        }
        display::text_left(
            text_baseline,
            text.as_str(),
            style.font,
            style.text_color,
            style.button_color,
        );

        // Paint the pending marker.
        if self.multi_tap.pending_key().is_some() && self.final_word.is_none() {
            paint_pending_marker(text_baseline, text.as_str(), style.font, style.text_color);
        }

        // Paint the icon.
        if let ButtonContent::Icon(icon) = self.button.content() {
            // Icon is painted in the right-center point, of expected size 16x16 pixels, and
            // 16px from the right edge.
            let icon_center = area.top_right().center(area.bottom_right()) - Offset::new(16 + 8, 0);
            icon.draw(
                icon_center,
                Alignment2D::CENTER,
                style.text_color,
                style.button_color,
            );
        }
    }

    #[cfg(feature = "ui_bounds")]
    fn bounds(&self, sink: &mut dyn FnMut(Rect)) {
        self.button.bounds(sink);
    }
}

impl Slip39Input {
    pub fn new() -> Self {
        Self {
            // Button has the same style the whole time
            button: Button::empty().styled(theme::button_pin_confirm()),
            textbox: TextBox::empty(),
            multi_tap: MultiTapKeyboard::new(),
            final_word: None,
            input_mask: Slip39Mask::full(),
        }
    }

    /// Convert a key index into the key digit. This is what we push into the
    /// input buffer.
    ///
    /// # Examples
    ///
    /// ```
    /// Self::key_digit(0) == '1';
    /// Self::key_digit(1) == '2';
    /// ```
    fn key_digit(key: usize) -> char {
        let index = key + 1;
        unwrap!(char::from_digit(index as u32, 10))
    }

    fn complete_word_from_dictionary(&mut self, ctx: &mut EventCtx) {
        let sequence = self.input_sequence();
        self.input_mask = sequence
            .and_then(slip39::word_completion_mask)
            .map(Slip39Mask)
            .unwrap_or_else(Slip39Mask::full);
        self.final_word = if self.input_mask.is_final() {
            sequence.and_then(slip39::button_sequence_to_word)
        } else {
            None
        };

        // Change the style of the button depending on the input.
        if self.final_word.is_some() {
            // Confirm button.
            self.button.enable(ctx);
            self.button
                .set_content(ctx, ButtonContent::Icon(theme::ICON_LIST_CHECK));
        } else {
            // Disabled button.
            self.button.disable(ctx);
            self.button.set_content(ctx, ButtonContent::Text(""));
        }
    }

    fn input_sequence(&self) -> Option<u16> {
        self.textbox.content().parse().ok()
    }
}

struct Slip39Mask(u16);

impl Slip39Mask {
    /// Return a mask with all keys allowed.
    fn full() -> Self {
        Self(0x1FF) // All buttons are allowed. 9-bit bitmap all set to 1.
    }

    /// Returns `true` if `key` can lead to a valid SLIP39 word with this mask.
    fn contains_key(&self, key: usize) -> bool {
        self.0 & (1 << key) != 0
    }

    /// Returns `true` if mask has exactly one bit set to 1, or is equal to 0.
    fn is_final(&self) -> bool {
        self.0.count_ones() <= 1
    }
}

// DEBUG-ONLY SECTION BELOW

#[cfg(feature = "ui_debug")]
impl crate::trace::Trace for Slip39Input {
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.component("Slip39Input");
        t.child("textbox", &self.textbox);
    }
}
