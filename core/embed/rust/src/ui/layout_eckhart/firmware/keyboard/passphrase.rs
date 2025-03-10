use crate::{
    strutil::{ShortString, TString},
    time::Duration,
    translations::TR,
    ui::{
        component::{
            swipe_detect::SwipeConfig,
            text::{
                common::TextBox,
                layout::{LayoutFit, LineBreaking},
                TextStyle,
            },
            Component, Event, EventCtx, Label, Swipe, TextLayout, Timer,
        },
        display::Icon,
        event::TouchEvent,
        flow::Swipable,
        geometry::{Alignment, Alignment2D, Direction, Insets, Offset, Rect},
        shape::{Bar, Renderer, Text, ToifImage},
        util::Pager,
    },
};

use super::super::{
    super::component::{Button, ButtonContent, ButtonMsg, ButtonStyleSheet},
    constant::SCREEN,
    keyboard::{
        common::{
            render_pending_marker, DisplayStyle, MultiTapKeyboard, FADING_ICON_COLORS,
            FADING_ICON_COUNT, INPUT_TOUCH_HEIGHT, KEYBOARD_INPUT_INSETS, KEYBOARD_INPUT_RADIUS,
            KEYPAD_VISIBLE_HEIGHT,
        },
        keypad::{ButtonState, Keypad, KeypadButton, KeypadMsg, KeypadState},
    },
    theme,
};

pub enum PassphraseKeyboardMsg {
    Confirmed(ShortString),
    Cancelled,
}

/// Enum keeping track of which keyboard is shown and which comes next. Keep the
/// number of values and the constant PAGE_COUNT in synch.
#[repr(u32)]
#[derive(Copy, Clone, PartialEq)]
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
    input: PassphraseInput,
    input_prompt: Label<'static>,
    keypad: Keypad,
    next_btn: Button,
    active_layout: KeyboardLayout,
    swipe_config: SwipeConfig,
    multi_tap: MultiTapKeyboard,
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

const MAX_LENGTH: usize = 50; // max length of the passphrase
const MAX_SHOWN_LEN: usize = 14; // max number of icons per line
const LAST_DIGIT_TIMEOUT_S: u32 = 1;

const NEXT_BTN_WIDTH: i16 = 103;
const NEXT_BTN_PADDING: i16 = 14;
const NEXT_BTN_INSETS: Insets =
    Insets::new(NEXT_BTN_PADDING, NEXT_BTN_PADDING, 0, NEXT_BTN_PADDING);

impl PassphraseKeyboard {
    pub fn new() -> Self {
        let active_layout = KeyboardLayout::LettersLower;
        let layout: &[&str; KEY_COUNT] = &KEYBOARD[active_layout as usize];
        let keypad_content: [ButtonContent; KEY_COUNT] =
            core::array::from_fn(|idx| Self::key_content(layout[idx]));

        let next_btn = Button::new(active_layout.next().into())
            .styled(theme::button_keyboard_next())
            .with_radius(12)
            .with_text_align(Alignment::Center)
            .with_expanded_touch_area(NEXT_BTN_INSETS);

        Self {
            page_swipe: Swipe::horizontal(),
            input: PassphraseInput::new(),
            input_prompt: Label::left_aligned(
                TString::from_translation(TR::passphrase__title_enter),
                theme::TEXT_SMALL,
            )
            .vertically_centered(),
            next_btn,
            keypad: Keypad::new_shown().with_keys_content(&keypad_content),
            active_layout,
            swipe_config: SwipeConfig::new(),
            multi_tap: MultiTapKeyboard::new(),
        }
    }

    fn key_text(content: &ButtonContent) -> TString<'static> {
        match content {
            ButtonContent::Text(text) => *text,
            ButtonContent::TextAndSubtext(_, _) => "".into(),
            ButtonContent::Icon(theme::ICON_SPECIAL_CHARS) => " *#".into(),
            ButtonContent::Icon(_) => " ".into(),
            ButtonContent::IconAndText(_) => " ".into(),
            ButtonContent::Empty => "".into(),
        }
    }

    fn key_content(text: &'static str) -> ButtonContent {
        match text {
            " *#" => ButtonContent::Icon(theme::ICON_SPECIAL_CHARS),
            t => ButtonContent::Text(t.into()),
        }
    }

    fn key_style(layout: KeyboardLayout) -> ButtonStyleSheet {
        if layout == KeyboardLayout::Numeric {
            theme::button_keyboard_numeric()
        } else {
            theme::button_keyboard()
        }
    }

    fn on_page_change(&mut self, ctx: &mut EventCtx, swipe: Direction) {
        // Change the keyboard layout.
        self.active_layout = match swipe {
            Direction::Left => self.active_layout.next(),
            Direction::Right => self.active_layout.prev(),
            _ => self.active_layout,
        };
        if self.multi_tap.pending_key().is_some() {
            // Clear the pending state.
            self.multi_tap.clear_pending_state(ctx);
            self.input.marker = false;
            // the character has been added, show it for a bit and then hide it
            self.input
                .last_char_timer
                .start(ctx, Duration::from_secs(LAST_DIGIT_TIMEOUT_S));
        }
        // Update keys.
        self.replace_keys_contents();
    }

    fn replace_keys_contents(&mut self) {
        self.next_btn.set_content(self.active_layout.next().into());
        let layout = self.active_layout as usize;
        let styles = Self::key_style(self.active_layout);

        for idx in 0..KEY_COUNT {
            let text = KEYBOARD[layout][idx];
            let content = Self::key_content(text);
            self.keypad.set_key_content(idx, content);
            self.keypad
                .set_button_stylesheet(KeypadButton::Key(idx), styles);
        }
    }

    fn update_keypad_state(&mut self, ctx: &mut EventCtx) {
        let keypad_state = match self.input.display_style {
            DisplayStyle::Shown => {
                // Disable the entire active keypad
                KeypadState {
                    back: ButtonState::Hidden,
                    erase: ButtonState::Disabled,
                    cancel: ButtonState::Hidden,
                    confirm: ButtonState::Disabled,
                    keys: ButtonState::Disabled,
                }
            }
            _ => {
                if self.passphrase().len() == MAX_LENGTH {
                    // Disable all except of confirm and erase buttons
                    KeypadState {
                        back: ButtonState::Hidden,
                        erase: ButtonState::Enabled,
                        cancel: ButtonState::Hidden,
                        confirm: ButtonState::Enabled,
                        keys: ButtonState::Disabled,
                    }
                } else if self.input.textbox.is_empty() {
                    // Disable all except of confirm and erase buttons
                    KeypadState {
                        back: ButtonState::Hidden,
                        erase: ButtonState::Hidden,
                        cancel: ButtonState::Hidden,
                        confirm: ButtonState::Enabled,
                        keys: ButtonState::Enabled,
                    }
                } else {
                    KeypadState {
                        back: ButtonState::Hidden,
                        erase: ButtonState::Enabled,
                        cancel: ButtonState::Hidden,
                        confirm: ButtonState::Enabled,
                        keys: ButtonState::Enabled,
                    }
                }
            }
        };

        self.keypad.set_state(keypad_state, ctx);
    }

    pub fn passphrase(&self) -> &str {
        self.input.textbox.content()
    }
}

impl Component for PassphraseKeyboard {
    type Msg = PassphraseKeyboardMsg;

    fn place(&mut self, bounds: Rect) -> Rect {
        // assert full screen
        debug_assert_eq!(bounds.height(), SCREEN.height());
        debug_assert_eq!(bounds.width(), SCREEN.width());

        // Enable swiping over the entire screen.
        self.page_swipe.place(bounds);

        // Keypad and input areas are overlapped
        let (_, keypad_area) = bounds.split_bottom(KEYPAD_VISIBLE_HEIGHT);
        let (top_area, _) = bounds.split_top(INPUT_TOUCH_HEIGHT);

        let (input_area, next_btn_area) =
            top_area.split_right(NEXT_BTN_WIDTH + 2 * NEXT_BTN_PADDING);

        let next_btn_area = next_btn_area.inset(NEXT_BTN_INSETS);

        self.input.place(input_area);
        self.input_prompt
            .place(top_area.inset(KEYBOARD_INPUT_INSETS));
        self.keypad.place(keypad_area);
        self.next_btn.place(next_btn_area);

        bounds
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        match event {
            Event::Attach(_) => {
                // Update the keypad state in the first event
                self.update_keypad_state(ctx);
            }
            Event::Timer(_) if self.multi_tap.timeout_event(event) => {
                self.multi_tap.clear_pending_state(ctx);
                self.input
                    .last_char_timer
                    .start(ctx, Duration::from_secs(LAST_DIGIT_TIMEOUT_S));
                self.input.marker = false;
                return None;
            }

            _ => {}
        }

        if let Some(swipe) = self.page_swipe.event(ctx, event) {
            // We have detected a horizontal swipe. Change the keyboard page.
            self.on_page_change(ctx, swipe);
            return None;
        }

        if let Some(ButtonMsg::Clicked) = self.next_btn.event(ctx, event) {
            self.on_page_change(ctx, Direction::Left);
        }

        match self.keypad.event(ctx, event) {
            Some(KeypadMsg::Key(idx)) => {
                let text = Self::key_text(self.keypad.get_key_content(idx));
                let edit = text.map(|c| self.multi_tap.click_key(ctx, idx, c));
                self.input.textbox.apply(ctx, edit);
                if text.len() == 1 {
                    // If the key has just one character, it is immediately applied and the last
                    // digit timer should be started
                    self.input.marker = false;
                    self.input
                        .last_char_timer
                        .start(ctx, Duration::from_secs(LAST_DIGIT_TIMEOUT_S));
                } else {
                    // multi tap timer is runnig, the last digit timer should be stopped
                    self.input.last_char_timer.stop();
                    self.input.marker = true;
                }
                self.input.display_style = DisplayStyle::LastOnly;
                self.update_keypad_state(ctx);
                return None;
            }
            Some(KeypadMsg::EraseShort) => {
                self.multi_tap.clear_pending_state(ctx);
                self.input.textbox.delete_last(ctx);
                self.input.display_style = DisplayStyle::Hidden;
                self.update_keypad_state(ctx);
                return None;
            }
            Some(KeypadMsg::EraseLong) => {
                self.multi_tap.clear_pending_state(ctx);
                self.input.textbox.clear(ctx);
                self.input.display_style = DisplayStyle::Hidden;
                self.update_keypad_state(ctx);
                return None;
            }
            Some(KeypadMsg::Cancel) => {
                return Some(PassphraseKeyboardMsg::Cancelled);
            }
            Some(KeypadMsg::Confirm) => {
                return Some(PassphraseKeyboardMsg::Confirmed(unwrap!(
                    ShortString::try_from(self.passphrase())
                )));
            }
            _ => {}
        }

        match self.input.event(ctx, event) {
            Some(PassphraseInputMsg::TouchStart) => {
                self.multi_tap.clear_pending_state(ctx);
                // Disable keypad.
                self.update_keypad_state(ctx);
                return None;
            }
            Some(PassphraseInputMsg::TouchEnd) => {
                // Enable keypad.
                self.update_keypad_state(ctx);
                return None;
            }
            _ => {}
        }

        None
    }

    fn render<'s>(&'s self, target: &mut impl Renderer<'s>) {
        let empty = self.passphrase().is_empty();

        // Render prompt when the pin is empty
        if empty {
            self.input_prompt.render(target);
        }

        // When the entire passphrase is shown, the input area might overlap the keypad
        // so it has to be render later
        match self.input.display_style {
            DisplayStyle::Shown => {
                self.keypad.render(target);
                self.input.render(target);
            }
            _ => {
                // When the next button is shown, the input area might overlap the keypad so it
                // has to be render later
                self.input.render(target);

                if self.next_btn.is_pressed() {
                    self.keypad.render(target);
                    self.next_btn.render(target);
                } else {
                    self.next_btn.render(target);
                    self.keypad.render(target);
                }
            }
        }
    }
}

#[derive(PartialEq, Debug, Copy, Clone)]
#[cfg_attr(feature = "ui_debug", derive(ufmt::derive::uDebug))]
pub enum PassphraseInputMsg {
    TouchStart,
    TouchEnd,
}

struct PassphraseInput {
    area: Rect,
    textbox: TextBox,
    display_style: DisplayStyle,
    marker: bool,
    last_char_timer: Timer,
    shown_area: Rect,
}

impl PassphraseInput {
    const TWITCH: i16 = 4;
    const SHOWN_PADDING: i16 = 24;
    const SHOWN_STYLE: TextStyle =
        theme::TEXT_MEDIUM.with_line_breaking(LineBreaking::BreakWordsNoHyphen);
    const ICON: Icon = theme::ICON_DASH_VERTICAL;
    const ICON_WIDTH: i16 = Self::ICON.toif.width();
    const ICON_SPACE: i16 = 12;

    fn new() -> Self {
        Self {
            area: Rect::zero(),
            textbox: TextBox::empty(MAX_LENGTH),
            display_style: DisplayStyle::LastOnly,
            marker: false,
            last_char_timer: Timer::new(),
            shown_area: Rect::zero(),
        }
    }

    fn passphrase(&self) -> &str {
        &self.textbox.content()
    }

    fn update_shown_area(&mut self) {
        // The area where the passphrase is shown
        let mut shown_area = Rect::from_top_left_and_size(
            self.area.top_left(),
            Offset::new(SCREEN.width(), self.area.height()),
        )
        .inset(KEYBOARD_INPUT_INSETS);

        // Extend the shown area until the text fits
        while let LayoutFit::OutOfBounds { .. } = TextLayout::new(Self::SHOWN_STYLE)
            .with_align(Alignment::Start)
            .with_bounds(shown_area.inset(Insets::uniform(Self::SHOWN_PADDING)))
            .fit_text(self.passphrase())
        {
            shown_area = shown_area.outset(Insets::bottom(32));
        }

        self.shown_area = shown_area;
    }

    fn render_shown<'s>(&self, target: &mut impl Renderer<'s>) {
        // Make sure the pin should be shown
        debug_assert_eq!(self.display_style, DisplayStyle::Shown);

        Bar::new(self.shown_area)
            .with_bg(theme::GREY_SUPER_DARK)
            .with_radius(KEYBOARD_INPUT_RADIUS)
            .render(target);

        TextLayout::new(Self::SHOWN_STYLE)
            .with_bounds(self.shown_area.inset(Insets::uniform(Self::SHOWN_PADDING)))
            .with_align(Alignment::Start)
            .render_text(self.passphrase(), target);
    }

    fn render_hidden<'s>(&self, target: &mut impl Renderer<'s>) {
        debug_assert_ne!(self.display_style, DisplayStyle::Shown);

        let hidden_area: Rect = self.area.inset(KEYBOARD_INPUT_INSETS);
        let style = theme::TEXT_MEDIUM;
        let pp_len = self.passphrase().len();
        let last_char = self.display_style == DisplayStyle::LastOnly;

        let mut cursor = hidden_area.left_center().ofs(Offset::x(12));

        // Render only when there are characters
        if pp_len > 0 {
            // Number of visible icons + characters
            let visible_len = pp_len.min(MAX_SHOWN_LEN);
            // Number of visible icons
            let visible_icons = visible_len - last_char as usize;

            // Jiggle when overflowed.
            if pp_len > visible_len && pp_len % 2 == 0 && self.display_style != DisplayStyle::Shown
            {
                cursor.x += Self::TWITCH;
            }

            let mut char_idx = 0;

            // Greyed out overflowing icons
            for (i, &fg_color) in FADING_ICON_COLORS.iter().enumerate() {
                if pp_len > visible_len + (FADING_ICON_COUNT - 1 - i) {
                    ToifImage::new(cursor, Self::ICON.toif)
                        .with_align(Alignment2D::TOP_LEFT)
                        .with_fg(fg_color)
                        .render(target);
                    cursor.x += Self::ICON_SPACE + Self::ICON_WIDTH;
                    char_idx += 1;
                }
            }

            if visible_icons > 0 {
                // Classical dot(s)
                for _ in char_idx..visible_icons {
                    ToifImage::new(cursor, Self::ICON.toif)
                        .with_align(Alignment2D::TOP_LEFT)
                        .with_fg(style.text_color)
                        .render(target);
                    cursor.x += Self::ICON_SPACE + Self::ICON_WIDTH;
                }
            }

            if last_char {
                // This should not fail because pp_len > 0
                let last = &self.passphrase()[(pp_len - 1)..pp_len];

                // Adapt a and y positions for the character
                cursor.y = hidden_area.left_center().y + style.text_font.text_max_height() / 2;
                cursor.x -= Self::ICON_WIDTH;

                // Paint the last character
                Text::new(cursor, last, style.text_font)
                    .with_align(Alignment::Start)
                    .with_fg(style.text_color)
                    .render(target);

                // Paint the pending marker.
                if self.marker {
                    render_pending_marker(target, cursor, last, style.text_font, style.text_color);
                }
            }
        }
    }
}

impl Component for PassphraseInput {
    type Msg = PassphraseInputMsg;

    fn place(&mut self, bounds: Rect) -> Rect {
        self.area = bounds;
        bounds
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        // No touch events are handled when the textbox is empty
        if self.textbox.is_empty() {
            return None;
        }

        match event {
            // Return touch start if the touch is detected inside the touchable area
            Event::Touch(TouchEvent::TouchStart(pos)) if self.area.contains(pos) => {
                // Stop the last char timer
                self.last_char_timer.stop();
                // Show the entire passphrase on the touch start
                self.display_style = DisplayStyle::Shown;
                self.update_shown_area();
                return Some(PassphraseInputMsg::TouchStart);
            }
            // Return touch end if the touch end is detected inside the visible area
            Event::Touch(TouchEvent::TouchEnd(pos))
                if self.shown_area.contains(pos) && self.display_style == DisplayStyle::Shown =>
            {
                self.display_style = DisplayStyle::Hidden;
                return Some(PassphraseInputMsg::TouchEnd);
            }
            // Return touch end if the touch moves out of the visible area
            Event::Touch(TouchEvent::TouchMove(pos))
                if !self.shown_area.contains(pos) && self.display_style == DisplayStyle::Shown =>
            {
                self.display_style = DisplayStyle::Hidden;
                return Some(PassphraseInputMsg::TouchEnd);
            }
            // Timeout for showing the last char.
            Event::Timer(_) if self.last_char_timer.expire(event) => {
                self.display_style = DisplayStyle::Hidden;
                ctx.request_paint();
            }
            _ => {}
        };
        None
    }

    fn render<'s>(&'s self, target: &mut impl Renderer<'s>) {
        if !self.passphrase().is_empty() {
            match self.display_style {
                DisplayStyle::Shown => self.render_shown(target),
                _ => self.render_hidden(target),
            }
        }
    }
}

#[cfg(feature = "micropython")]
impl Swipable for PassphraseKeyboard {
    fn get_swipe_config(&self) -> SwipeConfig {
        self.swipe_config
    }

    fn get_pager(&self) -> Pager {
        Pager::single_page()
    }
}

#[cfg(feature = "ui_debug")]
impl crate::trace::Trace for PassphraseKeyboard {
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        let display_style = uformat!("{:?}", self.input.display_style);
        t.component("PassphraseKeyboard");
        t.string("passphrase", self.passphrase().into());
        t.string("display_style", display_style.as_str().into());
    }
}
