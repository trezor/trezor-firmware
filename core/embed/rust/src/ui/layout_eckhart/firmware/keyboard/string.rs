use crate::{
    strutil::TString,
    ui::{
        component::{
            swipe_detect::SwipeConfig,
            text::{
                common::TextBox,
                layout::{LayoutFit, LineBreaking},
                TextStyle,
            },
            Component, Event, EventCtx, Label, Swipe, TextLayout,
        },
        display::Icon,
        event::TouchEvent,
        flow::Swipable,
        geometry::{Alignment, Direction, Insets, Offset, Rect},
        shape::{Bar, Renderer, Text},
        util::{long_line_content_with_ellipsis, Pager},
    },
};

use super::super::{
    super::component::{Button, ButtonContent, ButtonMsg, ButtonStyleSheet},
    constant::SCREEN,
    keyboard::{
        common::{
            render_pending_marker, KeyboardLayout, MultiTapKeyboard, INPUT_TOUCH_HEIGHT,
            KEYBOARD_INPUT_INSETS, KEYBOARD_INPUT_RADIUS, KEYPAD_VISIBLE_HEIGHT,
        },
        keypad::{ButtonState, Keypad, KeypadButton, KeypadMsg, KeypadState},
    },
    theme,
};

#[derive(PartialEq, Debug, Copy, Clone)]
#[cfg_attr(feature = "ui_debug", derive(ufmt::derive::uDebug))]
enum DisplayStyle {
    /// A part that fits on one line
    OneLine,
    /// One line with the last pending character.
    OneLineWithMarker,
    /// The complete string is shown in the input area.
    Complete,
}

pub enum StringKeyboardMsg {
    Confirmed,
    Cancelled,
}

pub struct StringKeyboard {
    page_swipe: Swipe,
    input: StringInput,
    input_prompt: Label<'static>,
    keypad: Keypad,
    next_btn: Button,
    active_layout: KeyboardLayout,
    swipe_config: SwipeConfig,
    multi_tap: MultiTapKeyboard,
    max_len: usize,
    allow_empty: bool,
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

const NEXT_BTN_WIDTH: i16 = 103;
const NEXT_BTN_PADDING: i16 = 14;
const NEXT_BTN_INSETS: Insets =
    Insets::new(NEXT_BTN_PADDING, NEXT_BTN_PADDING, 0, NEXT_BTN_PADDING);

impl StringKeyboard {
    pub fn new(
        prompt: TString<'static>,
        max_len: usize,
        allow_empty: bool,
        prefill: Option<TString<'static>>,
    ) -> Self {
        let active_layout = KeyboardLayout::LettersLower;
        let layout: &[&str; KEY_COUNT] = &KEYBOARD[active_layout as usize];
        let keypad_content: [ButtonContent; KEY_COUNT] =
            core::array::from_fn(|idx| Self::key_content(layout[idx]));

        let next_btn = Button::new(active_layout.next().into())
            .styled(theme::button_keyboard_next())
            .with_radius(12)
            .with_text_align(Alignment::Center)
            .with_expanded_touch_area(NEXT_BTN_INSETS);

        if let Some(prefill) = prefill {
            debug_assert!(prefill.len() <= max_len);
        }

        Self {
            page_swipe: Swipe::horizontal(),
            input: StringInput::new(max_len, prefill),
            input_prompt: Label::left_aligned(prompt, theme::firmware::TEXT_SMALL)
                .vertically_centered(),
            next_btn,
            keypad: Keypad::new_shown().with_keys_content(&keypad_content),
            active_layout,
            swipe_config: SwipeConfig::new(),
            multi_tap: MultiTapKeyboard::new(),
            max_len,
            allow_empty,
        }
    }

    fn key_text(content: &ButtonContent) -> Option<TString<'static>> {
        match content {
            ButtonContent::Text { text, .. } => Some(*text),
            ButtonContent::Icon(theme::ICON_SPECIAL_CHARS) => Some(" *#".into()),
            ButtonContent::Icon(_) => Some(" ".into()),
            _ => None,
        }
    }

    fn key_content(text: &'static str) -> ButtonContent {
        match text {
            " *#" => ButtonContent::Icon(theme::ICON_SPECIAL_CHARS),
            t => ButtonContent::single_line_text(t.into()),
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
            self.input.display_style = DisplayStyle::OneLine;
        }
        // Update keys.
        self.replace_keys_contents();
        self.update_keypad_state(ctx);
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

    /// Update the keypad state based on the current string and input state
    /// Can be used only when no key is pressed
    fn update_keypad_state(&mut self, ctx: &mut EventCtx) {
        let keypad_state = match self.input.display_style {
            DisplayStyle::Complete => {
                // Disable the entire active keypad
                KeypadState {
                    back: ButtonState::Hidden,
                    erase: ButtonState::Disabled,
                    cancel: ButtonState::Hidden,
                    confirm: ButtonState::Disabled,
                    keys: ButtonState::Disabled,
                    override_key: None,
                }
            }
            _ => {
                if self.string().len() == self.max_len {
                    if let Some(pending_key) = self.multi_tap.pending_key() {
                        // Disable all except of confirm, erase and the pending key
                        KeypadState {
                            back: ButtonState::Hidden,
                            erase: ButtonState::Enabled,
                            cancel: ButtonState::Hidden,
                            confirm: ButtonState::Enabled,
                            keys: ButtonState::Disabled,
                            override_key: Some((pending_key, ButtonState::Enabled)),
                        }
                    } else {
                        // Disable all except of confirm and erase buttons
                        KeypadState {
                            back: ButtonState::Hidden,
                            erase: ButtonState::Enabled,
                            cancel: ButtonState::Hidden,
                            confirm: ButtonState::Enabled,
                            keys: ButtonState::Disabled,
                            override_key: None,
                        }
                    }
                } else if self.input.textbox.is_empty() {
                    // Disable all except of confirm and erase buttons
                    KeypadState {
                        back: ButtonState::Hidden,
                        erase: ButtonState::Hidden,
                        cancel: ButtonState::Enabled,
                        confirm: if self.allow_empty {
                            ButtonState::Enabled
                        } else {
                            ButtonState::Disabled
                        },
                        keys: ButtonState::Enabled,
                        override_key: None,
                    }
                } else {
                    KeypadState {
                        back: ButtonState::Hidden,
                        erase: ButtonState::Enabled,
                        cancel: ButtonState::Hidden,
                        confirm: ButtonState::Enabled,
                        keys: ButtonState::Enabled,
                        override_key: None,
                    }
                }
            }
        };

        self.keypad.set_state(keypad_state, ctx);
    }

    pub fn string(&self) -> &str {
        self.input.textbox.content()
    }
}

impl Component for StringKeyboard {
    type Msg = StringKeyboardMsg;

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
                self.input.display_style = DisplayStyle::OneLine;
                // Disable keypad when the string reached the max length
                if self.string().len() == self.max_len {
                    self.update_keypad_state(ctx);
                }
                return None;
            }

            _ => {}
        }

        // Input event has to be handled before the swipe so that swipe in the input
        // area is not processed
        match self.input.event(ctx, event) {
            Some(StringInputMsg::TouchStart) => {
                self.multi_tap.clear_pending_state(ctx);
                // Disable keypad.
                self.update_keypad_state(ctx);
                return None;
            }
            Some(StringInputMsg::TouchEnd) => {
                // Enable keypad.
                self.update_keypad_state(ctx);
                return None;
            }
            _ => {}
        }

        // Swipe event has to be handled before the individual button events
        if let Some(swipe) = self.page_swipe.event(ctx, event) {
            match swipe {
                Direction::Left | Direction::Right => {
                    // We have detected a horizontal swipe. Change the keyboard page.
                    self.on_page_change(ctx, swipe);
                    return None;
                }
                _ => {}
            }
        }

        if let Some(ButtonMsg::Clicked) = self.next_btn.event(ctx, event) {
            self.on_page_change(ctx, Direction::Left);
        }

        match self.keypad.event(ctx, event) {
            Some(KeypadMsg::Key(idx)) => {
                if let Some(text) = Self::key_text(self.keypad.get_key_content(idx)) {
                    let edit = text.map(|c| self.multi_tap.click_key(ctx, idx, c));
                    self.input.textbox.apply(ctx, edit);
                    if text.len() == 1 {
                        // If the key has just one character, it is immediately applied
                        self.input.display_style = DisplayStyle::OneLine;
                    } else {
                        // multi tap timer is running, the last digit timer should be stopped
                        self.input.display_style = DisplayStyle::OneLineWithMarker;
                    }
                    self.update_keypad_state(ctx);
                }
                return None;
            }
            Some(KeypadMsg::EraseShort) => {
                self.multi_tap.clear_pending_state(ctx);
                self.input.textbox.delete_last(ctx);
                self.input.display_style = DisplayStyle::OneLine;
                self.update_keypad_state(ctx);
                return None;
            }
            Some(KeypadMsg::EraseLong) => {
                self.multi_tap.clear_pending_state(ctx);
                self.input.textbox.clear(ctx);
                self.input.display_style = DisplayStyle::OneLine;
                self.update_keypad_state(ctx);
                return None;
            }
            Some(KeypadMsg::Cancel) => {
                return Some(StringKeyboardMsg::Cancelled);
            }
            Some(KeypadMsg::Confirm) => {
                return Some(StringKeyboardMsg::Confirmed);
            }
            _ => {}
        }

        None
    }

    fn render<'s>(&'s self, target: &mut impl Renderer<'s>) {
        let empty = self.string().is_empty();

        // Render prompt when the pin is empty
        if empty {
            self.input_prompt.render(target);
        }

        // When the entire string is shown, the input area might overlap the keypad
        // so it has to be render later
        match self.input.display_style {
            DisplayStyle::Complete => {
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
pub enum StringInputMsg {
    TouchStart,
    TouchEnd,
}

struct StringInput {
    area: Rect,
    textbox: TextBox,
    display_style: DisplayStyle,
    shown_area: Rect,
}

impl StringInput {
    const TWITCH: i16 = 4;
    const SHOWN_INSETS: Insets = Insets::new(12, 24, 12, 24);
    const SHOWN_STYLE: TextStyle =
        theme::TEXT_REGULAR.with_line_breaking(LineBreaking::BreakWordsNoHyphen);
    const SHOWN_TOUCH_OUTSET: Insets = Insets::bottom(200);
    const ICON: Icon = theme::ICON_DASH_VERTICAL;
    const ICON_WIDTH: i16 = Self::ICON.toif.width();
    const ICON_SPACE: i16 = 12;

    fn new(max_len: usize, prefill: Option<TString<'static>>) -> Self {
        let textbox = if let Some(prefill) = prefill {
            prefill.map(|s| TextBox::new(s, max_len))
        } else {
            TextBox::empty(max_len)
        };

        Self {
            area: Rect::zero(),
            textbox,
            display_style: DisplayStyle::OneLine,
            shown_area: Rect::zero(),
        }
    }

    fn string(&self) -> &str {
        self.textbox.content()
    }

    fn update_shown_area(&mut self) {
        // The area where the string is shown
        let mut shown_area = Rect::from_top_left_and_size(
            self.area.top_left(),
            Offset::new(SCREEN.width(), self.area.height()),
        )
        .inset(KEYBOARD_INPUT_INSETS);

        // Extend the shown area until the text fits
        while let LayoutFit::OutOfBounds { .. } = TextLayout::new(Self::SHOWN_STYLE)
            .with_align(Alignment::Start)
            .with_bounds(shown_area.inset(Self::SHOWN_INSETS))
            .fit_text(self.string())
        {
            shown_area =
                shown_area.outset(Insets::bottom(Self::SHOWN_STYLE.text_font.line_height()));
        }

        self.shown_area = shown_area;
    }

    fn render_complete<'s>(&self, target: &mut impl Renderer<'s>) {
        // Make sure the pin should be shown
        debug_assert_eq!(self.display_style, DisplayStyle::Complete);

        Bar::new(self.shown_area)
            .with_bg(theme::GREY_SUPER_DARK)
            .with_radius(KEYBOARD_INPUT_RADIUS)
            .render(target);

        TextLayout::new(Self::SHOWN_STYLE)
            .with_bounds(self.shown_area.inset(Self::SHOWN_INSETS))
            .with_align(Alignment::Start)
            .render_text(self.string(), target, true);
    }

    fn render_one_line<'s>(&self, target: &mut impl Renderer<'s>) {
        debug_assert_ne!(self.display_style, DisplayStyle::Complete);

        let insets = Insets::new(
            KEYBOARD_INPUT_INSETS.top,
            0,
            KEYBOARD_INPUT_INSETS.bottom,
            KEYBOARD_INPUT_INSETS.left,
        );

        let area: Rect = self.area.inset(insets);
        let style = theme::TEXT_REGULAR;

        // Find out how much text can fit into the textbox.
        // Accounting for the pending marker, which draws itself one pixel longer than
        // the last character
        let available_area_width = area.width() - 1;
        let text_to_display = long_line_content_with_ellipsis(
            self.string(),
            "...",
            style.text_font,
            available_area_width,
        );

        let cursor = area
            .left_center()
            .ofs(Offset::new(8, style.text_font.text_max_height() / 2 - 4));

        Text::new(cursor, &text_to_display, style.text_font)
            .with_fg(style.text_color)
            .render(target);

        // Paint the pending marker.
        if self.display_style == DisplayStyle::OneLineWithMarker {
            render_pending_marker(
                target,
                cursor,
                &text_to_display,
                style.text_font,
                style.text_color,
            );
        }
    }
}

impl Component for StringInput {
    type Msg = StringInputMsg;

    fn place(&mut self, bounds: Rect) -> Rect {
        self.area = bounds;
        bounds
    }

    fn event(&mut self, _ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        // No touch events are handled when the textbox is empty
        if self.textbox.is_empty() {
            return None;
        }

        // Extend the string area downward to allow touch input without the finger
        // covering the string
        let extended_shown_area = self
            .shown_area
            .outset(Self::SHOWN_TOUCH_OUTSET)
            .clamp(SCREEN);

        match event {
            // Return touch start if the touch is detected inside the touchable area
            Event::Touch(TouchEvent::TouchStart(pos)) if self.area.contains(pos) => {
                // Show the entire string on the touch start
                self.display_style = DisplayStyle::Complete;
                self.update_shown_area();
                return Some(StringInputMsg::TouchStart);
            }
            // Return touch end if the touch end is detected inside the visible area
            Event::Touch(TouchEvent::TouchEnd(pos))
                if extended_shown_area.contains(pos)
                    && self.display_style == DisplayStyle::Complete =>
            {
                self.display_style = DisplayStyle::OneLine;
                return Some(StringInputMsg::TouchEnd);
            }
            // Return touch end if the touch moves out of the visible area
            Event::Touch(TouchEvent::TouchMove(pos))
                if !extended_shown_area.contains(pos)
                    && self.display_style == DisplayStyle::Complete =>
            {
                self.display_style = DisplayStyle::OneLine;
                return Some(StringInputMsg::TouchEnd);
            }
            _ => {}
        };
        None
    }

    fn render<'s>(&'s self, target: &mut impl Renderer<'s>) {
        if !self.string().is_empty() {
            match self.display_style {
                DisplayStyle::Complete => self.render_complete(target),
                _ => self.render_one_line(target),
            }
        }
    }
}

#[cfg(feature = "micropython")]
impl Swipable for StringKeyboard {
    fn get_swipe_config(&self) -> SwipeConfig {
        self.swipe_config
    }

    fn get_pager(&self) -> Pager {
        Pager::single_page()
    }
}

#[cfg(feature = "ui_debug")]
impl crate::trace::Trace for StringKeyboard {
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        let display_style = uformat!("{:?}", self.input.display_style);
        let active_layout = uformat!("{:?}", self.active_layout);
        t.component("StringKeyboard");
        t.string("string", self.string().into());
        t.string("display_style", display_style.as_str().into());
        t.string("active_layout", active_layout.as_str().into());
    }
}
