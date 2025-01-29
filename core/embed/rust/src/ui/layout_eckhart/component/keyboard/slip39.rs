use crate::{
    strutil::ShortString,
    trezorhal::slip39,
    ui::{
        component::{
            text::common::{TextBox, TextEdit},
            Component, Event, EventCtx,
        },
        display::Icon,
        geometry::{Alignment, Alignment2D, Offset, Rect},
        shape::{Renderer, Text, ToifImage},
        util::ResultExt,
    },
};

use super::super::super::{
    component::{
        keyboard::{
            common::{render_pending_marker, MultiTapKeyboard},
            mnemonic::{MnemonicInput, MnemonicInputMsg, MNEMONIC_KEY_COUNT},
        },
        Button, ButtonMsg,
    },
    theme,
};

const MAX_LENGTH: usize = 8;

pub struct Slip39Input {
    button: Button,
    textbox: TextBox,
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

    fn can_be_confirmed(&self) -> bool {
        self.final_word.is_some()
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

    fn on_confirm_click(&mut self, ctx: &mut EventCtx) -> Option<MnemonicInputMsg> {
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
        self.final_word
    }
}

impl Component for Slip39Input {
    type Msg = MnemonicInputMsg;

    fn place(&mut self, bounds: Rect) -> Rect {
        self.button.place(bounds)
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        if self.multi_tap.timeout_event(event) {
            // Timeout occurred. Reset the pending key.
            self.multi_tap.clear_pending_state(ctx);
            return Some(MnemonicInputMsg::TimedOut);
        }
        if let Some(ButtonMsg::Clicked) = self.button.event(ctx, event) {
            // Input button was clicked.  If the whole word is totally identified, let's
            // confirm it, otherwise don't do anything.
            return self.on_input_click(ctx);
        }
        None
    }

    fn render<'s>(&'s self, target: &mut impl Renderer<'s>) {
        let area = self.button.area();
        let style = self.button.style();

        if let Some(word) = self.final_word {
            // print the final mnemonic
            Text::new(
                area.center() + Offset::y(style.font.allcase_text_height() / 2),
                word,
                style.font,
            )
            .with_fg(style.text_color)
            .with_align(Alignment::Center)
            .render(target);
        } else {
            let input_len = self.textbox.content().len();

            // Get last pending character, if any.
            let last = if let (Some(key), Some(press)) =
                (self.multi_tap.pending_key(), self.multi_tap.pending_press())
            {
                Some(&Self::keys()[key][press..(press + 1)])
            } else {
                None
            };

            // Initial position for drawing the icons
            let mut cursor = area.center().ofs(Offset::x(-self.size() / 2));
            let visible_icons = input_len.saturating_sub(last.is_some() as usize);

            if input_len > 0 {
                for _ in 0..visible_icons {
                    ToifImage::new(cursor, Self::ICON.toif)
                        .with_align(Alignment2D::TOP_LEFT)
                        .with_fg(style.text_color)
                        .render(target);
                    cursor.x += Self::ICON_SPACE + Self::ICON_WIDTH;
                }

                if let Some(last) = last {
                    // Adapt a and y positions for the character
                    cursor.y += style.font.allcase_text_height() / 2;
                    cursor.x -= Self::ICON_WIDTH;

                    // Paint the last character
                    Text::new(cursor, last, style.font)
                        .with_align(Alignment::Start)
                        .with_fg(style.text_color)
                        .render(target);

                    render_pending_marker(target, cursor, last, style.font, style.text_color);
                }
            }
        }
    }
}

impl Slip39Input {
    const ICON: Icon = theme::ICON_DASH_VERTICAL;
    const ICON_WIDTH: i16 = Self::ICON.toif.width();
    const ICON_SPACE: i16 = 12;

    pub fn new() -> Self {
        Self {
            button: Button::empty().styled(theme::input_mnemonic()),
            textbox: TextBox::empty(MAX_LENGTH),
            multi_tap: MultiTapKeyboard::new(),
            final_word: None,
            input_mask: Slip39Mask::full(),
        }
    }

    pub fn prefilled_word(word: &str) -> Self {
        // Word may be empty string, fallback to normal input
        if word.is_empty() {
            return Self::new();
        }

        let (buff, input_mask, final_word) = Self::setup_from_prefilled_word(word);

        Self {
            button: Button::empty().styled(theme::input_mnemonic()),
            textbox: TextBox::new(&buff, MAX_LENGTH),
            multi_tap: MultiTapKeyboard::new(),
            final_word,
            input_mask,
        }
    }

    fn on_input_click(&mut self, _ctx: &mut EventCtx) -> Option<MnemonicInputMsg> {
        if self.final_word.is_some() {
            return Some(MnemonicInputMsg::Confirmed);
        }
        None
    }

    fn setup_from_prefilled_word(word: &str) -> (ShortString, Slip39Mask, Option<&'static str>) {
        let mut buff = ShortString::new();

        // Gradually appending encoded key digits to the buffer and checking if
        // have not already formed a final word.
        for ch in word.chars() {
            let mut index = 0;
            for (i, key) in Self::keys().iter().enumerate() {
                if key.contains(ch) {
                    index = i;
                    break;
                }
            }
            buff.push(Self::key_digit(index))
                .assert_if_debugging_ui("Text buffer is too small");

            let sequence: Option<u16> = buff.parse().ok();
            let input_mask = sequence
                .and_then(slip39::word_completion_mask)
                .map(Slip39Mask)
                .unwrap_or_else(Slip39Mask::full);
            let final_word = if input_mask.is_final() {
                sequence.and_then(slip39::button_sequence_to_word)
            } else {
                None
            };

            // As soon as we have a final word, we can stop.
            if final_word.is_some() {
                return (buff, input_mask, final_word);
            }
        }
        (buff, Slip39Mask::full(), None)
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
            self.button.set_stylesheet(theme::input_mnemonic_confirm());
        } else {
            // Disabled button.
            self.button.disable(ctx);
            self.button.set_stylesheet(theme::input_mnemonic());
        }
        ctx.request_paint();
    }

    fn input_sequence(&self) -> Option<u16> {
        self.textbox.content().parse().ok()
    }

    fn size(&self) -> i16 {
        let ndots = self.textbox.content().len();
        let mut width = Self::ICON_WIDTH * (ndots as i16);
        width += Self::ICON_SPACE * (ndots.saturating_sub(1) as i16);
        width
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
