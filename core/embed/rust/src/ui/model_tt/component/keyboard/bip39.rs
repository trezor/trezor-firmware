use crate::{
    trezorhal::bip39,
    ui::{
        component::{text::common::TextBox, Component, Event, EventCtx},
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
    },
};

const MAX_LENGTH: usize = 8;

pub struct Bip39Input {
    button: Button<&'static str>,
    textbox: TextBox<MAX_LENGTH>,
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
        self.button.place(bounds)
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        if self.multi_tap.is_timeout_event(event) {
            self.on_timeout(ctx)
        } else if let Some(ButtonMsg::Clicked) = self.button.event(ctx, event) {
            self.on_input_click(ctx)
        } else {
            None
        }
    }

    fn paint(&mut self) {
        let area = self.button.area();
        let style = self.button.style();

        // First, paint the button background.
        self.button.paint_background(style);

        // Paint the entered content (the prefix of the suggested word).
        let text = self.textbox.content();
        let width = style.font.text_width(text);
        // Content starts in the left-center point, offset by 16px to the right and 8px
        // to the bottom.
        let text_baseline = area.top_left().center(area.bottom_left()) + Offset::new(16, 8);
        display::text_left(
            text_baseline,
            text,
            style.font,
            style.text_color,
            style.button_color,
        );

        // Paint the rest of the suggested dictionary word.
        if let Some(word) = self.suggested_word.and_then(|w| w.get(text.len()..)) {
            let word_baseline = text_baseline + Offset::new(width, 0);
            display::text_left(
                word_baseline,
                word,
                style.font,
                theme::GREY_LIGHT,
                style.button_color,
            );
        }

        // Paint the pending marker.
        if self.multi_tap.pending_key().is_some() {
            paint_pending_marker(text_baseline, text, style.font, style.text_color);
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

impl Bip39Input {
    pub fn new() -> Self {
        Self {
            button: Button::empty(),
            textbox: TextBox::empty(),
            multi_tap: MultiTapKeyboard::new(),
            options_num: None,
            suggested_word: None,
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

    /// Input button was clicked.  If the content matches the suggested word,
    /// let's confirm it, otherwise just auto-complete.
    fn on_input_click(&mut self, ctx: &mut EventCtx) -> Option<MnemonicInputMsg> {
        if let (Some(word), Some(num)) = (self.suggested_word, self.options_num) {
            return if num == 1 && word.starts_with(self.textbox.content())
                || num > 1 && word.eq(self.textbox.content())
            {
                // Confirm button.
                self.textbox.clear(ctx);
                Some(MnemonicInputMsg::Confirmed)
            } else {
                // Auto-complete button.
                self.textbox.replace(ctx, word);
                self.complete_word_from_dictionary(ctx);
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
        if let (Some(word), Some(num)) = (self.suggested_word, self.options_num) {
            if num == 1 && word.starts_with(self.textbox.content())
                || num > 1 && word.eq(self.textbox.content())
            {
                // Confirm button.
                self.button.enable(ctx);
                self.button.set_stylesheet(ctx, theme::button_pin_confirm());
                self.button
                    .set_content(ctx, ButtonContent::Icon(theme::ICON_LIST_CHECK));
            } else {
                // Auto-complete button.
                self.button.enable(ctx);
                self.button
                    .set_stylesheet(ctx, theme::button_pin_autocomplete());
                self.button
                    .set_content(ctx, ButtonContent::Icon(theme::ICON_CLICK));
            }
        } else {
            // Disabled button.
            self.button.disable(ctx);
            self.button.set_stylesheet(ctx, theme::button_pin());
            self.button.set_content(ctx, ButtonContent::Text(""));
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
