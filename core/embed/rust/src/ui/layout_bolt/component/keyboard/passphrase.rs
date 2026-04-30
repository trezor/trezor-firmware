use crate::{
    strutil::{ShortString, TString},
    time::Duration,
    ui::{
        component::{
            base::ComponentExt,
            text::{
                common::TextBox,
                layout::{LayoutFit, LineBreaking},
                TextStyle,
            },
            Child, Component, Event, EventCtx, Never, Pad, Paginate, TextLayout, Timer,
        },
        display,
        event::TouchEvent,
        geometry::{Alignment, Grid, Insets, Offset, Rect},
        shape::{Bar, Renderer, Text},
        util::{DisplayStyle, Pager},
    },
};

use super::super::{
    super::constant::SCREEN,
    button::{Button, ButtonContent, ButtonMsg},
    keyboard::common::{render_pending_marker, MultiTapKeyboard},
    swipe::{Swipe, SwipeDirection},
    theme, ScrollBar,
};

use core::cell::Cell;

#[cfg_attr(feature = "debug", derive(ufmt::derive::uDebug))]
pub enum PassphraseKeyboardMsg {
    Confirmed,
    Cancelled,
}

pub struct PassphraseKeyboard {
    page_swipe: Swipe,
    input: Child<Input>,
    back: Child<Button>,
    confirm: Child<Button>,
    keys: [Child<Button>; KEY_COUNT],
    scrollbar: ScrollBar,
    fade: Cell<bool>,
    max_len: usize,
}

const STARTING_PAGE: usize = 1;
const PAGE_COUNT: usize = 4;
const KEY_COUNT: usize = 10;
#[rustfmt::skip]
const KEYBOARD: [[&str; KEY_COUNT]; PAGE_COUNT] = [
    ["1", "2", "3", "4", "5", "6", "7", "8", "9", "0"],
    [" ", "abc", "def", "ghi", "jkl", "mno", "pqrs", "tuv", "wxyz", "*#"],
    [" ", "ABC", "DEF", "GHI", "JKL", "MNO", "PQRS", "TUV", "WXYZ", "*#"],
    ["_<>", ".:@", "/|\\", "!()", "+%&", "-[]", "?{}", ",'`", ";\"~", "$^="],
    ];

/// Enum keeping track of which keyboard is shown and which comes next. Keep the
/// number of values and the constant PAGE_COUNT in sync.
#[repr(u32)]
#[derive(Copy, Clone, PartialEq)]
#[cfg_attr(feature = "ui_debug", derive(ufmt::derive::uDebug))]
pub(crate) enum KeyboardLayout {
    Numeric = 0,
    LettersLower = 1,
    LettersUpper = 2,
    Special = 3,
}

impl KeyboardLayout {
    /// Number of variants (kept in sync with the enum by using the last
    /// discriminant).
    pub const VARIANT_COUNT: usize = KeyboardLayout::Special as usize + 1;

    /// Map page index -> layout (bounds must be valid).
    pub const fn from_page_unchecked(page: usize) -> Self {
        // Order must match KEYBOARD rows.
        const MAP: [KeyboardLayout; KeyboardLayout::VARIANT_COUNT] = [
            KeyboardLayout::Numeric,
            KeyboardLayout::LettersLower,
            KeyboardLayout::LettersUpper,
            KeyboardLayout::Special,
        ];
        MAP[page]
    }
}

const INPUT_AREA_HEIGHT: i16 = ScrollBar::DOT_SIZE + 9;

impl PassphraseKeyboard {
    pub fn new(max_len: usize) -> Self {
        Self {
            page_swipe: Swipe::horizontal(),
            input: Input::new(max_len).into_child(),
            confirm: Button::with_icon(theme::ICON_CONFIRM)
                .styled(theme::button_confirm())
                .into_child(),
            back: Button::with_icon_blend(
                theme::IMAGE_BG_BACK_BTN,
                theme::ICON_BACK,
                Offset::new(30, 12),
            )
            .styled(theme::button_reset())
            .initially_enabled(false)
            .with_long_press(theme::ERASE_HOLD_DURATION)
            .into_child(),
            keys: KEYBOARD[STARTING_PAGE].map(|text| {
                Child::new(Button::new(Self::key_content(text)).styled(theme::button_pin()))
            }),
            scrollbar: ScrollBar::horizontal(),
            fade: Cell::new(false),
            max_len,
        }
    }

    fn key_text(content: &ButtonContent) -> TString<'static> {
        match content {
            ButtonContent::Text(text) => *text,
            ButtonContent::Icon(_) => " ".into(),
            ButtonContent::IconAndText(_) => " ".into(),
            ButtonContent::Empty => "".into(),
            ButtonContent::IconBlend(_, _, _) => "".into(),
        }
    }

    fn key_content(text: &'static str) -> ButtonContent {
        match text {
            " " => ButtonContent::Icon(theme::ICON_SPACE),
            t => ButtonContent::Text(t.into()),
        }
    }

    fn on_page_swipe(&mut self, ctx: &mut EventCtx, swipe: SwipeDirection) {
        // Change the page number.
        let mut pager = self.scrollbar.pager();
        match swipe {
            SwipeDirection::Left => pager.goto_next(),
            SwipeDirection::Right => pager.goto_prev(),
            _ => false,
        };

        self.scrollbar.set_pager(pager);
        // Clear the pending state. If there was a pending character, it has been
        // committed; show it briefly then hide.
        self.input.mutate(ctx, |ctx, i| {
            if i.multi_tap.pending_key().is_some() {
                i.multi_tap.clear_pending_state(ctx);
                i.display_style = DisplayStyle::LastOnly;
                i.last_char_timer.start(ctx, Input::LAST_DIGIT_TIMEOUT);
            }
        });
        // Update buttons.
        self.replace_button_content(ctx, pager.current().into());
        // Reset backlight to normal level on next paint.
        self.fade.set(true);
        // So that swipe does not visually enable the input buttons when max length
        // reached
        self.update_input_btns_state(ctx);
    }

    fn replace_button_content(&mut self, ctx: &mut EventCtx, page: usize) {
        for (i, btn) in self.keys.iter_mut().enumerate() {
            let text = KEYBOARD[page][i];
            let content = Self::key_content(text);
            btn.mutate(ctx, |ctx, b| b.set_content(ctx, content));
            btn.request_complete_repaint(ctx);
        }
    }

    /// Possibly changing the buttons' state after change of the input.
    fn after_edit(&mut self, ctx: &mut EventCtx) {
        self.update_back_btn_state(ctx);
        self.update_input_btns_state(ctx);
    }

    /// When the input is empty, disable the back button.
    fn update_back_btn_state(&mut self, ctx: &mut EventCtx) {
        if self.input.inner().textbox.is_empty() {
            self.back.mutate(ctx, |ctx, b| b.disable(ctx));
        } else {
            self.back.mutate(ctx, |ctx, b| b.enable(ctx));
        }
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
        let textbox_not_full = self.input.inner().textbox.len() < self.max_len;
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
        let bounds = bounds.inset(theme::borders());

        let (top_area, key_grid_area) =
            bounds.split_bottom(4 * theme::PIN_BUTTON_HEIGHT + 3 * theme::BUTTON_SPACING);

        let (input_area, scroll_area) = top_area.split_bottom(INPUT_AREA_HEIGHT);
        let (scroll_area, _) = scroll_area.split_top(ScrollBar::DOT_SIZE);

        let key_grid = Grid::new(key_grid_area, 4, 3).with_spacing(theme::BUTTON_SPACING);
        let confirm_btn_area = key_grid.cell(11);
        let back_btn_area = key_grid.cell(9);

        self.page_swipe.place(key_grid_area);
        self.input.place(input_area);
        self.input.inner().reveal_area.set(top_area);
        self.confirm.place(confirm_btn_area);
        self.back.place(back_btn_area);
        self.scrollbar.place(scroll_area);
        self.scrollbar
            .set_pager(Pager::new(PAGE_COUNT as u16).with_current(STARTING_PAGE as u16));

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
        // Handle multi-tap timeout: commit the pending character and show it briefly
        let multitap_timeout = self.input.mutate(ctx, |ctx, i| {
            if i.multi_tap.timeout_event(event) {
                i.multi_tap.clear_pending_state(ctx);
                i.display_style = DisplayStyle::LastOnly;
                i.last_char_timer.start(ctx, Input::LAST_DIGIT_TIMEOUT);
                true
            } else {
                false
            }
        });
        if multitap_timeout {
            // Disable keypad when the passphrase reached the max length
            if self.input.inner().textbox.len() >= self.max_len {
                self.update_input_btns_state(ctx);
            }
            return None;
        }

        self.input.event(ctx, event);

        // When passphrase is shown in full, disable all keypad interaction
        if self.input.inner().display_style == DisplayStyle::Shown {
            return None;
        }

        if let Some(swipe) = self.page_swipe.event(ctx, event) {
            // We have detected a horizontal swipe. Change the keyboard page.
            self.on_page_swipe(ctx, swipe);
            return None;
        }
        if let Some(ButtonMsg::Clicked) = self.confirm.event(ctx, event) {
            // Confirm button was clicked, we're done.
            return Some(PassphraseKeyboardMsg::Confirmed);
        }

        match self.back.event(ctx, event) {
            Some(ButtonMsg::Clicked) => {
                // Backspace button was clicked. If we have any content in the textbox, let's
                // delete the last character. Otherwise cancel.
                return if self.input.inner().textbox.is_empty() {
                    Some(PassphraseKeyboardMsg::Cancelled)
                } else {
                    self.input.mutate(ctx, |ctx, i| {
                        i.multi_tap.clear_pending_state(ctx);
                        i.textbox.delete_last(ctx);
                        i.display_style = DisplayStyle::Hidden;
                    });
                    self.after_edit(ctx);
                    None
                };
            }
            Some(ButtonMsg::LongPressed) => {
                self.input.mutate(ctx, |ctx, i| {
                    i.multi_tap.clear_pending_state(ctx);
                    i.textbox.clear(ctx);
                    i.display_style = DisplayStyle::Hidden;
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
                    if text.len() == 1 {
                        // Single-char key: immediately applied, show last char briefly
                        i.display_style = DisplayStyle::LastOnly;
                        i.last_char_timer.start(ctx, Input::LAST_DIGIT_TIMEOUT);
                    } else {
                        // Multi-tap key: pending state, show char with marker
                        i.last_char_timer.stop();
                        i.display_style = DisplayStyle::LastWithMarker;
                    }
                });
                self.after_edit(ctx);
                return None;
            }
        }
        None
    }

    fn render<'s>(&'s self, target: &mut impl Renderer<'s>) {
        if self.input.inner().display_style == DisplayStyle::Shown {
            // When passphrase is revealed, render only the shown overlay
            self.input.render(target);
        } else {
            self.input.render(target);
            self.scrollbar.render(target);
            self.confirm.render(target);
            self.back.render(target);
            for btn in &self.keys {
                btn.render(target);
            }
            if self.fade.take() {
                // Note that this is blocking and takes some time.
                display::fade_backlight(theme::backlight::get_backlight_normal());
            }
        }
    }
}

struct Input {
    area: Rect,
    textbox: TextBox,
    multi_tap: MultiTapKeyboard,
    display_style: DisplayStyle,
    last_char_timer: Timer,
    pad: Pad,
    /// Area in which a touch start triggers the passphrase reveal
    reveal_area: Cell<Rect>,
    /// Area in which the passphrase reveal window appears
    shown_area: Rect,
}

impl Input {
    const TWITCH: i16 = 4;
    const LAST_DIGIT_TIMEOUT: Duration = Duration::from_secs(1);
    const STYLE: TextStyle =
        theme::label_keyboard().with_line_breaking(LineBreaking::BreakWordsNoHyphen);
    const SHOWN_INSETS: Insets = Insets::new(8, 10, 8, 10);

    fn new(max_len: usize) -> Self {
        Self {
            area: Rect::zero(),
            reveal_area: Cell::new(Rect::zero()),
            textbox: TextBox::empty(max_len),
            multi_tap: MultiTapKeyboard::new(),
            display_style: DisplayStyle::Hidden,
            last_char_timer: Timer::new(),
            pad: Pad::with_background(theme::BG),
            shown_area: Rect::zero(),
        }
    }

    fn update_shown_area(&mut self) {
        let line_height = Self::STYLE.text_font.line_height();

        // Start with full screen width, positioned at the input area top
        let initial_height = line_height + Self::SHOWN_INSETS.top + Self::SHOWN_INSETS.bottom;
        let mut shown_area = SCREEN.inset(Self::SHOWN_INSETS).with_height(initial_height);

        // Extend the shown area until the text fits
        while let LayoutFit::OutOfBounds { .. } = TextLayout::new(Self::STYLE)
            .with_align(Alignment::Start)
            .with_bounds(shown_area.inset(Self::SHOWN_INSETS))
            .fit_text(self.textbox.content())
        {
            shown_area = shown_area.outset(Insets::bottom(line_height));
        }

        self.shown_area = shown_area;
    }

    fn render_shown<'s>(&self, target: &mut impl Renderer<'s>) {
        debug_assert_eq!(self.display_style, DisplayStyle::Shown);

        Bar::new(self.shown_area)
            .with_bg(theme::GREY_DARK)
            .with_radius(theme::RADIUS as i16)
            .render(target);

        TextLayout::new(Self::STYLE)
            .with_bounds(self.shown_area.inset(Self::SHOWN_INSETS))
            .with_align(Alignment::Start)
            .render_text(self.textbox.content(), target, true);
    }

    fn render_hidden<'s>(&self, target: &mut impl Renderer<'s>) {
        debug_assert_ne!(self.display_style, DisplayStyle::Shown);

        let style = theme::label_keyboard();
        let pp_len = self.textbox.count();
        if pp_len == 0 {
            return;
        }

        let last_char_visible = self.display_style == DisplayStyle::LastOnly
            || self.display_style == DisplayStyle::LastWithMarker;

        // Compute how many characters fit in the available width. Account for the
        // pending marker, which draws itself one pixel longer than the last char.
        let available_width = self.area.width() - 1;
        let asterisk_width = style.text_font.char_width('*').max(1);
        let max_visible = (available_width / asterisk_width).max(1) as usize;
        let visible_count = pp_len.min(max_visible);
        let asterisk_count = visible_count.saturating_sub(last_char_visible as usize);

        // Build asterisks string
        let mut asterisks = ShortString::new();
        for _ in 0..asterisk_count {
            let _ = asterisks.push('*');
        }

        let mut text_baseline = self.area.top_left() + Offset::y(style.text_font.text_height())
            - Offset::y(style.text_font.text_baseline());

        // Twitch when overflowed (alternates so user sees feedback when typing past
        // what fits)
        if pp_len > max_visible && pp_len % 2 == 1 {
            text_baseline.x += Self::TWITCH;
        }

        // Render asterisks in GREY_LIGHT
        if !asterisks.is_empty() {
            Text::new(text_baseline, &asterisks, style.text_font)
                .with_align(Alignment::Start)
                .with_fg(theme::GREY_LIGHT)
                .render(target);
        }

        // Render the visible last character in the regular text color
        if last_char_visible {
            if let Some(last) = self.textbox.last_char_str() {
                let last_baseline =
                    text_baseline + Offset::x(style.text_font.text_width(&asterisks));

                Text::new(last_baseline, last, style.text_font)
                    .with_align(Alignment::Start)
                    .with_fg(style.text_color)
                    .render(target);

                if self.display_style == DisplayStyle::LastWithMarker {
                    render_pending_marker(
                        target,
                        last_baseline,
                        last,
                        style.text_font,
                        style.text_color,
                    );
                }
            }
        }
    }
}

impl Component for Input {
    type Msg = Never;

    fn place(&mut self, bounds: Rect) -> Rect {
        self.pad.place(bounds);
        self.area = bounds;
        self.reveal_area.set(bounds);
        self.area
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        if self.textbox.is_empty() {
            return None;
        }

        match event {
            // Reveal on touch start within the extended input area
            Event::Touch(TouchEvent::TouchStart(pos)) if self.reveal_area.get().contains(pos) => {
                self.multi_tap.clear_pending_state(ctx);
                self.last_char_timer.stop();
                self.display_style = DisplayStyle::Shown;
                self.update_shown_area();
                self.pad.clear();
                ctx.request_paint();
            }
            // Hide on touch end anywhere on the screen
            Event::Touch(TouchEvent::TouchEnd(_)) if self.display_style == DisplayStyle::Shown => {
                self.display_style = DisplayStyle::Hidden;
                self.pad.clear();
                ctx.request_paint();
            }
            // Timeout for showing the last char
            Event::Timer(_) if self.last_char_timer.expire(event) => {
                self.display_style = DisplayStyle::Hidden;
                self.request_complete_repaint(ctx);
                ctx.request_paint();
            }
            _ => {}
        }
        None
    }

    fn render<'s>(&'s self, target: &mut impl Renderer<'s>) {
        self.pad.render(target);

        if self.textbox.is_empty() {
            return;
        }

        match self.display_style {
            DisplayStyle::Shown => self.render_shown(target),
            _ => self.render_hidden(target),
        }
    }
}

#[cfg(feature = "ui_debug")]
impl crate::trace::Trace for PassphraseKeyboard {
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        let page = self.scrollbar.pager().current();
        debug_assert!(page < PAGE_COUNT as u16);
        let active_layout = uformat!("{:?}", KeyboardLayout::from_page_unchecked(page.into()));
        let display_style = uformat!("{:?}", self.input.inner().display_style);
        t.component("PassphraseKeyboard");
        t.string("active_layout", active_layout.as_str().into());
        t.string("passphrase", self.passphrase().into());
        t.string("display_style", display_style.as_str().into());
    }
}
