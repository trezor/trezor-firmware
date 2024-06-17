use crate::{
    strutil::TString,
    translations::TR,
    ui::{
        component::{
            base::ComponentExt, text::common::TextBox, Child, Component, Event, EventCtx, Label,
            Maybe, Never, Swipe, SwipeDirection,
        },
        display,
        geometry::{Alignment, Grid, Insets, Offset, Rect},
        model_mercury::component::{
            button::{Button, ButtonContent, ButtonMsg},
            keyboard::common::{render_pending_marker, MultiTapKeyboard},
            theme,
        },
        shape,
        shape::Renderer,
        util::long_line_content_with_ellipsis,
    },
};

use core::cell::Cell;
use num_traits::ToPrimitive;

pub enum PassphraseKeyboardMsg {
    Confirmed,
    Cancelled,
}

/// Enum keeping track of which keyboard is shown and which comes next. Keep the
/// number of values and the constant PAGE_COUNT in synch.
#[repr(u32)]
#[derive(Copy, Clone, ToPrimitive)]
enum KeyboardLayout {
    LettersLower = 0,
    LettersUpper = 1,
    Numeric = 2,
    Special = 3,
}

impl KeyboardLayout {
    fn next(self) -> Self {
        match self {
            Self::LettersLower => Self::LettersUpper,
            Self::LettersUpper => Self::Numeric,
            Self::Numeric => Self::Special,
            Self::Special => Self::LettersLower,
        }
    }

    fn prev(self) -> Self {
        match self {
            Self::LettersLower => Self::Special,
            Self::LettersUpper => Self::LettersLower,
            Self::Numeric => Self::LettersUpper,
            Self::Special => Self::Numeric,
        }
    }
}

impl From<KeyboardLayout> for ButtonContent {
    /// Used to get content for the "next keyboard" button
    fn from(kl: KeyboardLayout) -> Self {
        match kl {
            KeyboardLayout::LettersLower => ButtonContent::Text("abc".into()),
            KeyboardLayout::LettersUpper => ButtonContent::Text("ABC".into()),
            KeyboardLayout::Numeric => ButtonContent::Text("123".into()),
            KeyboardLayout::Special => ButtonContent::Icon(theme::ICON_ASTERISK),
        }
    }
}

pub struct PassphraseKeyboard {
    page_swipe: Swipe,
    input: Child<Input>,
    input_prompt: Child<Label<'static>>,
    erase_btn: Child<Maybe<Button>>,
    cancel_btn: Child<Maybe<Button>>,
    confirm_btn: Child<Button>,
    next_btn: Child<Button>,
    keys: [Child<Button>; KEY_COUNT],
    active_layout: KeyboardLayout,
    fade: Cell<bool>,
}

const PAGE_COUNT: usize = 4;
const KEY_COUNT: usize = 10;
#[rustfmt::skip]
const KEYBOARD: [[&str; KEY_COUNT]; PAGE_COUNT] = [
    ["abc", "def", "ghi", "jkl", "mno", "pq", "rst", "uvw", "xyz", " *#"],
    ["ABC", "DEF", "GHI", "JKL", "MNO", "PQ", "RST", "UVW", "XYZ", " *#"],
    ["1", "2", "3", "4", "5", "6", "7", "8", "9", "0"],
    ["_<>", ".:@", "/|\\", "!()", "+%&", "-[]", "?{}", ",'`", ";\"~", "$^="],
    ];

const MAX_LENGTH: usize = 50;

impl PassphraseKeyboard {
    pub fn new() -> Self {
        let active_layout = KeyboardLayout::LettersLower;

        let confirm_btn = Button::with_icon(theme::ICON_CONFIRM)
            .styled(theme::button_passphrase_confirm())
            .with_radius(15)
            .into_child();

        let next_btn = Button::new(active_layout.next().into())
            .styled(theme::button_passphrase_next())
            .with_text_align(Alignment::Center)
            .into_child();

        let erase_btn = Button::with_icon(theme::ICON_DELETE)
            .styled(theme::button_keyboard_erase())
            .with_long_press(theme::ERASE_HOLD_DURATION)
            .initially_enabled(false);
        let erase_btn = Maybe::hidden(theme::BG, erase_btn).into_child();

        let cancel_btn =
            Button::with_icon(theme::ICON_CLOSE).styled(theme::button_keyboard_cancel());
        let cancel_btn = Maybe::visible(theme::BG, cancel_btn).into_child();

        Self {
            page_swipe: Swipe::horizontal(),
            input: Input::new().into_child(),
            input_prompt: Label::left_aligned(
                TString::from_translation(TR::passphrase__title_enter),
                theme::label_keyboard(),
            )
            .into_child(),
            erase_btn,
            cancel_btn,
            confirm_btn,
            next_btn,
            keys: KEYBOARD[active_layout.to_usize().unwrap()].map(|text| {
                Child::new(
                    Button::new(Self::key_content(text))
                        .styled(theme::button_keyboard())
                        .with_text_align(Alignment::Center),
                )
            }),
            active_layout,
            fade: Cell::new(false),
        }
    }

    fn key_text(content: &ButtonContent) -> TString<'static> {
        match content {
            ButtonContent::Text(text) => *text,
            ButtonContent::Icon(theme::ICON_SPECIAL_CHARS_GROUP) => " *#".into(),
            ButtonContent::Icon(_) => " ".into(),
            ButtonContent::IconAndText(_) => " ".into(),
            ButtonContent::Empty => "".into(),
            ButtonContent::IconBlend(_, _, _) => "".into(),
        }
    }

    fn key_content(text: &'static str) -> ButtonContent {
        match text {
            " *#" => ButtonContent::Icon(theme::ICON_SPECIAL_CHARS_GROUP),
            t => ButtonContent::Text(t.into()),
        }
    }

    fn on_page_change(&mut self, ctx: &mut EventCtx, swipe: SwipeDirection) {
        // Change the keyboard layout.
        self.active_layout = match swipe {
            SwipeDirection::Left => self.active_layout.next(),
            SwipeDirection::Right => self.active_layout.prev(),
            _ => self.active_layout,
        };
        // Clear the pending state.
        self.input
            .mutate(ctx, |ctx, i| i.multi_tap.clear_pending_state(ctx));
        // Update keys.
        self.replace_keys_contents(ctx);
        // Reset backlight to normal level on next paint.
        self.fade.set(true);
        // So that swipe does not visually enable the input buttons when max length
        // reached
        self.update_input_btns_state(ctx);
    }

    fn replace_keys_contents(&mut self, ctx: &mut EventCtx) {
        self.next_btn.mutate(ctx, |ctx, b| {
            b.set_content(ctx, self.active_layout.next().into());
        });
        for (i, btn) in self.keys.iter_mut().enumerate() {
            let text = KEYBOARD[self.active_layout.to_usize().unwrap()][i];
            let content = Self::key_content(text);
            btn.mutate(ctx, |ctx, b| b.set_content(ctx, content));
            btn.request_complete_repaint(ctx);
        }
    }

    /// Possibly changing the buttons' state after change of the input.
    fn after_edit(&mut self, ctx: &mut EventCtx) {
        // When the input is empty, enable cancel button. Otherwise show erase and
        // confirm button.
        let is_empty = self.input.inner().textbox.is_empty();
        self.erase_btn.mutate(ctx, |ctx, btn| {
            btn.show_if(ctx, !is_empty);
            btn.inner_mut().enable_if(ctx, !is_empty);
        });
        self.cancel_btn.mutate(ctx, |ctx, btn| {
            btn.show_if(ctx, is_empty);
            btn.inner_mut().enable_if(ctx, is_empty);
        });

        self.update_input_btns_state(ctx);
    }

    /// When the input has reached max length, disable all the input buttons.
    fn update_input_btns_state(&mut self, ctx: &mut EventCtx) {
        let active_states = self.get_buttons_active_states();
        for (key, btn) in self.keys.iter_mut().enumerate() {
            btn.mutate(ctx, |ctx, b| {
                if active_states[key] {
                    b.enable(ctx);
                } else {
                    b.disable(ctx);
                }
            });
        }
    }

    /// Precomputing the active states not to overlap borrows in
    /// `self.keys.iter_mut` loop.
    fn get_buttons_active_states(&self) -> [bool; KEY_COUNT] {
        let mut active_states: [bool; KEY_COUNT] = [false; KEY_COUNT];
        for (key, state) in active_states.iter_mut().enumerate() {
            *state = self.is_button_active(key);
        }
        active_states
    }

    /// We should disable the input when the passphrase has reached maximum
    /// length and we are not cycling through the characters.
    fn is_button_active(&self, key: usize) -> bool {
        let textbox_not_full = self.input.inner().textbox.len() < MAX_LENGTH;
        let key_is_pending = {
            if let Some(pending) = self.input.inner().multi_tap.pending_key() {
                pending == key
            } else {
                false
            }
        };
        textbox_not_full || key_is_pending
    }

    pub fn passphrase(&self) -> &str {
        self.input.inner().textbox.content()
    }
}

impl Component for PassphraseKeyboard {
    type Msg = PassphraseKeyboardMsg;

    fn place(&mut self, bounds: Rect) -> Rect {
        const CONFIRM_BTN_WIDTH: i16 = 78;
        const INPUT_INSETS: Insets = Insets::new(10, 2, 10, 4);
        const CONFIRM_BTN_INSETS: Insets = Insets::new(5, 0, 5, 0);

        let bounds = bounds.inset(theme::borders());
        let (top_area, key_grid_area) =
            bounds.split_bottom(4 * theme::PASSPHRASE_BUTTON_HEIGHT + 3 * theme::BUTTON_SPACING);
        let (input_area, confirm_btn_area) = top_area.split_right(CONFIRM_BTN_WIDTH);

        let top_area = top_area.inset(INPUT_INSETS);
        let input_area = input_area.inset(INPUT_INSETS);
        let confirm_btn_area = confirm_btn_area.inset(CONFIRM_BTN_INSETS);

        let key_grid = Grid::new(key_grid_area, 4, 3).with_spacing(theme::BUTTON_SPACING);
        let next_btn_area = key_grid.cell(11);
        let erase_cancel_area = key_grid.cell(9);

        self.page_swipe.place(bounds);
        self.input.place(input_area);
        self.input_prompt.place(top_area);

        // control buttons
        self.confirm_btn.place(confirm_btn_area);
        self.next_btn.place(next_btn_area);
        self.erase_btn.place(erase_cancel_area);
        self.cancel_btn.place(erase_cancel_area);

        // Place all the character buttons.
        for (key, btn) in &mut self.keys.iter_mut().enumerate() {
            // Assign the keys in each page to buttons on a 5x3 grid, starting
            // from the second row.
            let area = key_grid.cell(if key < 9 {
                // The grid has 3 columns, and we skip the first row.
                key
            } else {
                // For the last key (the "0" position) we skip one cell.
                key + 1
            });
            btn.place(area);
        }

        bounds
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        if self.input.inner().multi_tap.is_timeout_event(event) {
            self.input
                .mutate(ctx, |ctx, i| i.multi_tap.clear_pending_state(ctx));
            return None;
        }
        if let Some(swipe) = self.page_swipe.event(ctx, event) {
            // We have detected a horizontal swipe. Change the keyboard page.
            self.on_page_change(ctx, swipe);
            return None;
        }
        if let Some(ButtonMsg::Clicked) = self.next_btn.event(ctx, event) {
            self.on_page_change(ctx, SwipeDirection::Left);
        }
        if let Some(ButtonMsg::Clicked) = self.confirm_btn.event(ctx, event) {
            // Confirm button was clicked, we're done.
            return Some(PassphraseKeyboardMsg::Confirmed);
        }
        if let Some(ButtonMsg::Clicked) = self.cancel_btn.event(ctx, event) {
            // Cancel button is visible and clicked, cancel
            return Some(PassphraseKeyboardMsg::Cancelled);
        }

        match self.erase_btn.event(ctx, event) {
            Some(ButtonMsg::Clicked) => {
                self.input.mutate(ctx, |ctx, i| {
                    i.multi_tap.clear_pending_state(ctx);
                    i.textbox.delete_last(ctx);
                });
                self.after_edit(ctx);
                return None;
            }
            Some(ButtonMsg::LongPressed) => {
                self.input.mutate(ctx, |ctx, i| {
                    i.multi_tap.clear_pending_state(ctx);
                    i.textbox.clear(ctx);
                });
                self.after_edit(ctx);
                return None;
            }
            _ => {}
        }

        // Process key button events in case we did not reach maximum passphrase length.
        // (All input buttons should be disallowed in that case, this is just a safety
        // measure.)
        // Also we need to allow for cycling through the last character.
        let active_states = self.get_buttons_active_states();
        for (key, btn) in self.keys.iter_mut().enumerate() {
            if !active_states[key] {
                // Button is not active
                continue;
            }
            if let Some(ButtonMsg::Clicked) = btn.event(ctx, event) {
                // Key button was clicked. If this button is pending, let's cycle the pending
                // character in textbox. If not, let's just append the first character.
                let text = Self::key_text(btn.inner().content());
                self.input.mutate(ctx, |ctx, i| {
                    let edit = text.map(|c| i.multi_tap.click_key(ctx, key, c));
                    i.textbox.apply(ctx, edit);
                });
                self.after_edit(ctx);
                return None;
            }
        }
        None
    }

    fn paint(&mut self) {
        todo!("remove when ui-t3t1 done")
    }

    fn render<'s>(&'s self, target: &mut impl Renderer<'s>) {
        self.input.render(target);
        self.next_btn.render(target);
        self.erase_btn.render(target);
        self.confirm_btn.render(target);
        if self.input.inner().textbox.is_empty() {
            self.cancel_btn.render(target);
            // FIXME: when prompt fixed in Figma
            // self.input_prompt.render(target);
        }
        for btn in &self.keys {
            btn.render(target);
        }
        if self.fade.take() {
            // Note that this is blocking and takes some time.
            display::fade_backlight(theme::backlight::get_backlight_normal());
        }
    }

    #[cfg(feature = "ui_bounds")]
    fn bounds(&self, sink: &mut dyn FnMut(Rect)) {
        self.input.bounds(sink);
        self.input_prompt.bounds(sink);
        self.confirm_btn.bounds(sink);
        self.erase_btn.bounds(sink);
        self.cancel_btn.bounds(sink);
        for btn in &self.keys {
            btn.bounds(sink)
        }
    }
}

struct Input {
    area: Rect,
    textbox: TextBox,
    multi_tap: MultiTapKeyboard,
}

impl Input {
    fn new() -> Self {
        Self {
            area: Rect::zero(),
            textbox: TextBox::empty(MAX_LENGTH),
            multi_tap: MultiTapKeyboard::new(),
        }
    }
}

impl Component for Input {
    type Msg = Never;

    fn place(&mut self, bounds: Rect) -> Rect {
        self.area = bounds;
        self.area
    }

    fn event(&mut self, _ctx: &mut EventCtx, _event: Event) -> Option<Self::Msg> {
        None
    }

    fn paint(&mut self) {
        todo!("remove when ui-t3t1 done");
    }

    fn render<'s>(&'s self, target: &mut impl Renderer<'s>) {
        let style = theme::label_keyboard();

        let text_baseline = self.area.top_left() + Offset::y(style.text_font.text_height())
            - Offset::y(style.text_font.text_baseline());

        let text = self.textbox.content();

        shape::Bar::new(self.area).with_bg(theme::BG).render(target);

        // Find out how much text can fit into the textbox.
        // Accounting for the pending marker, which draws itself one pixel longer than
        // the last character
        let available_area_width = self.area.width() - 1;
        let text_to_display =
            long_line_content_with_ellipsis(text, "...", style.text_font, available_area_width);

        shape::Text::new(text_baseline, &text_to_display)
            .with_font(style.text_font)
            .with_fg(style.text_color)
            .render(target);

        // Paint the pending marker.
        if self.multi_tap.pending_key().is_some() {
            render_pending_marker(
                target,
                text_baseline,
                &text_to_display,
                style.text_font,
                style.text_color,
            );
        }
    }

    #[cfg(feature = "ui_bounds")]
    fn bounds(&self, sink: &mut dyn FnMut(Rect)) {
        sink(self.area)
    }
}

#[cfg(feature = "ui_debug")]
impl crate::trace::Trace for PassphraseKeyboard {
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.component("PassphraseKeyboard");
        t.string("passphrase", self.passphrase().into());
    }
}
