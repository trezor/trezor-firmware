use crate::{
    trezorhal::bip39,
    ui::{
        component::{text::common::TextBox, Component, Event, EventCtx},
        geometry::{Alignment, Offset, Point, Rect},
        shape::{Renderer, Text},
    },
};

use super::super::super::{
    component::{Button, ButtonMsg},
    constant::WIDTH,
    firmware::keyboard::{
        common::{render_pending_marker, MultiTapKeyboard},
        mnemonic::{MnemonicInput, MnemonicInputMsg, MNEMONIC_KEY_COUNT},
    },
    theme,
};

const MAX_LENGTH: usize = 8;

pub struct Bip39Input {
    button: Button,
    // used only to keep track of suggestion text color
    button_suggestion: Button,
    textbox: TextBox,
    multi_tap: MultiTapKeyboard,
    options_num: Option<usize>,
    suggested_word: Option<&'static str>,
}

impl MnemonicInput for Bip39Input {
    /// Return the key set. Keys are further specified as indices into this
    /// array.
    fn keys() -> [&'static str; MNEMONIC_KEY_COUNT] {
        ["abc", "def", "ghi", "jkl", "mno", "pqr", "stu", "vwx", "yz"]
    }

    fn can_be_confirmed(&self) -> bool {
        self.is_choice_unambiguous()
    }

    /// Returns `true` if given key index can continue towards a valid mnemonic
    /// word, `false` otherwise.
    fn can_key_press_lead_to_a_valid_word(&self, key: usize) -> bool {
        // Currently pending key is always enabled.
        let key_is_pending = self.multi_tap.pending_key() == Some(key);
        // Keys that contain letters from the completion mask are enabled as well.
        let key_matches_mask =
            bip39::word_completion_mask(self.textbox.content()) & Self::key_mask(key) != 0;
        key_is_pending || key_matches_mask
    }

    /// Key button was clicked. If this button is pending, let's cycle the
    /// pending character in textbox. If not, let's just append the first
    /// character.
    fn on_key_click(&mut self, ctx: &mut EventCtx, key: usize) {
        let edit = self.multi_tap.click_key(ctx, key, Self::keys()[key]);
        self.textbox.apply(ctx, edit);
        self.complete_word_from_dictionary(ctx);
    }

    /// Backspace button was clicked, let's delete the last character of input
    /// and clear the pending marker.
    fn on_backspace_click(&mut self, ctx: &mut EventCtx) {
        self.multi_tap.clear_pending_state(ctx);
        self.textbox.delete_last(ctx);
        self.complete_word_from_dictionary(ctx);
    }

    fn on_confirm_click(&mut self, ctx: &mut EventCtx) -> Option<MnemonicInputMsg> {
        // same action as clicking on the input
        self.on_input_click(ctx)
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
        self.suggested_word
    }
}

impl Component for Bip39Input {
    type Msg = MnemonicInputMsg;

    fn place(&mut self, bounds: Rect) -> Rect {
        self.button.place(bounds);
        self.button_suggestion.place(bounds)
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        if let Event::Attach(_) = event {
            // Catch up with the prefilled word
            if !self.textbox.is_empty() {
                self.complete_word_from_dictionary(ctx);
                return Some(MnemonicInputMsg::Completed);
            }
        }

        _ = self.button_suggestion.event(ctx, event);

        if self.multi_tap.timeout_event(event) {
            self.on_timeout(ctx)
        } else if let Some(ButtonMsg::Clicked) = self.button.event(ctx, event) {
            self.on_input_click(ctx)
        } else {
            None
        }
    }

    fn render<'s>(&'s self, target: &mut impl Renderer<'s>) {
        let area = self.button.area();
        let style = self.button.style();
        let suggestion_style = self.button_suggestion.style();

        // Paint the entered content (the prefix of the suggested word).
        let text = self.textbox.content();
        let width = style.font.text_width(text);

        // User input together with suggestion is centered vertically in the input area
        // and centered horizontally on the screen
        let text_base_y = area.left_center().y + style.font.allcase_text_height() / 2;
        let text_base_x = if let Some(word) = self.suggested_word {
            style.font.horz_center(0, WIDTH, word)
        } else {
            style.font.horz_center(0, WIDTH, text)
        };
        let text_base = Point::new(text_base_x, text_base_y);

        self.button.render(target);

        // Render text input + suggested completion
        Text::new(text_base, text, style.font)
            .with_fg(style.text_color)
            .with_align(Alignment::Start)
            .render(target);
        if let Some(word) = self.suggested_word.and_then(|w| w.get(text.len()..)) {
            let word_baseline = text_base + Offset::x(width);
            Text::new(word_baseline, word, style.font)
                .with_fg(suggestion_style.text_color)
                .with_align(Alignment::Start)
                .render(target);
        }

        // Paint the pending marker.
        if self.multi_tap.pending_key().is_some() {
            render_pending_marker(target, text_base, text, style.font, style.text_color);
        }
    }
}

impl Bip39Input {
    pub fn new() -> Self {
        Self::prefilled_word("")
    }

    pub fn prefilled_word(word: &str) -> Self {
        // Word may be empty string, fallback to normal input
        let (options_num, suggested_word) = if word.is_empty() {
            (bip39::options_num(word), bip39::complete_word(word))
        } else {
            (None, None)
        };

        // Styling the input to reflect already filled word
        Self {
            button: Button::empty()
                .styled(theme::input_mnemonic())
                .with_radius(12),
            button_suggestion: Button::empty().styled(theme::input_mnemonic_suggestion()),
            textbox: TextBox::new(word, MAX_LENGTH),
            multi_tap: MultiTapKeyboard::new(),
            options_num,
            suggested_word,
        }
    }

    /// Compute a bitmask of all letters contained in given key text. Lowest bit
    /// is 'a', second lowest 'b', etc.
    fn key_mask(key: usize) -> u32 {
        let mut mask = 0;
        for ch in Self::keys()[key].as_bytes() {
            // We assume the key text is lower-case alphabetic ASCII, making the subtraction
            // and the shift panic-free.
            mask |= 1 << (ch - b'a');
        }
        mask
    }

    fn is_choice_unambiguous(&self) -> bool {
        if let (Some(word), Some(_num)) = (self.suggested_word, self.options_num) {
            return word.eq(self.textbox.content());
        }
        false
    }

    /// Input button was clicked.  If the content matches the suggested word,
    /// let's confirm it, otherwise just auto-complete.
    fn on_input_click(&mut self, ctx: &mut EventCtx) -> Option<MnemonicInputMsg> {
        if let (Some(word), Some(_num)) = (self.suggested_word, self.options_num) {
            return if word.eq(self.textbox.content()) {
                // Confirm button.
                self.textbox.clear(ctx);
                Some(MnemonicInputMsg::Confirmed)
            } else {
                // Auto-complete button.
                self.textbox.replace(ctx, word);
                self.complete_word_from_dictionary(ctx);
                ctx.request_paint();
                Some(MnemonicInputMsg::Completed)
            };
        }
        None
    }

    /// Timeout occurred.  If we can auto-complete current input, let's just
    /// reset the pending marker.  If not, input is invalid, let's backspace the
    /// last character.
    fn on_timeout(&mut self, ctx: &mut EventCtx) -> Option<MnemonicInputMsg> {
        self.multi_tap.clear_pending_state(ctx);
        if self.suggested_word.is_none() {
            self.textbox.delete_last(ctx);
            self.complete_word_from_dictionary(ctx);
        }
        Some(MnemonicInputMsg::TimedOut)
    }

    fn complete_word_from_dictionary(&mut self, ctx: &mut EventCtx) {
        self.options_num = bip39::options_num(self.textbox.content());
        self.suggested_word = bip39::complete_word(self.textbox.content());

        // Change the style of the button depending on the completed word.
        if let (Some(word), Some(_num)) = (self.suggested_word, self.options_num) {
            if word.eq(self.textbox.content()) {
                // Confirm button.
                self.button.enable(ctx);
                self.button.set_stylesheet(theme::input_mnemonic_confirm());
            } else {
                // Auto-complete button.
                self.button.enable(ctx);
                self.button.set_stylesheet(theme::input_mnemonic());
            }
        } else {
            // Disabled button.
            self.button.disable(ctx);
            self.button.set_stylesheet(theme::input_mnemonic());
        }
    }
}

// DEBUG-ONLY SECTION BELOW

#[cfg(feature = "ui_debug")]
impl crate::trace::Trace for Bip39Input {
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.component("Bip39Input");
        t.child("textbox", &self.textbox);
    }
}
