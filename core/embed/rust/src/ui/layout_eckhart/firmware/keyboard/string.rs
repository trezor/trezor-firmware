use crate::{
    strutil::{ShortString, TString},
    ui::{
        component::{swipe_detect::SwipeConfig, Component, Event, EventCtx, Label, Swipe},
        flow::Swipable,
        geometry::{Alignment, Direction, Insets, Rect},
        shape::Renderer,
        util::Pager,
    },
};

use super::super::{
    super::component::{Button, ButtonContent, ButtonMsg, ButtonStyleSheet},
    constant::SCREEN,
    keyboard::{
        common::{
            KeyboardLayout, INPUT_TOUCH_HEIGHT, KEYBOARD_PROMPT_INSETS, KEYPAD_VISIBLE_HEIGHT,
        },
        keypad::{Keypad, KeypadButton, KeypadMsg, KeypadState},
    },
    theme,
};

pub enum StringKeyboardMsg {
    Confirmed(ShortString),
    Cancelled,
}

pub struct StringKeyboard<I: StringInput> {
    page_swipe: Swipe,
    input: I,
    input_prompt: Label<'static>,
    keypad: Keypad,
    next_btn: Button,
    active_layout: KeyboardLayout,
    swipe_config: SwipeConfig,
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

impl<I: StringInput> StringKeyboard<I> {
    pub fn new(prompt: TString<'static>, input: I) -> Self {
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
            input,
            input_prompt: Label::left_aligned(prompt, theme::firmware::TEXT_SMALL)
                .vertically_centered(),
            next_btn,
            keypad: Keypad::new_shown().with_keys_content(&keypad_content),
            active_layout,
            swipe_config: SwipeConfig::new(),
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
        // Update keys.
        self.replace_keys_contents();
        self.update_keypad_state(ctx);
        // Update input state.
        self.input.on_page_change(ctx);
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

    /// Update the keypad state based on the current passphrase and input state
    /// Can be used only when no key is pressed
    fn update_keypad_state(&mut self, ctx: &mut EventCtx) {
        self.keypad.set_state(self.input.get_keypad_state(), ctx);
    }
}

impl<I: StringInput> Component for StringKeyboard<I> {
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
            .place(top_area.inset(KEYBOARD_PROMPT_INSETS));
        self.keypad.place(keypad_area);
        self.next_btn.place(next_btn_area);

        bounds
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        if let Event::Attach(_) = event {
            self.update_keypad_state(ctx);
            return None;
        }

        // Input event has to be handled before the swipe so that swipe in the input
        // area is not processed
        if let Some(StringInputMsg::UpdateKeypad) = self.input.event(ctx, event) {
            self.update_keypad_state(ctx);
            return None;
        }

        // Swipe event has to be handled before the individual button events
        if let Some(swipe @ (Direction::Left | Direction::Right)) =
            self.page_swipe.event(ctx, event)
        {
            // We have detected a horizontal swipe. Change the keyboard page.
            self.on_page_change(ctx, swipe);
            return None;
        }

        if let Some(ButtonMsg::Clicked) = self.next_btn.event(ctx, event) {
            self.on_page_change(ctx, Direction::Left);
            return None;
        }

        match self.keypad.event(ctx, event) {
            Some(KeypadMsg::Key(idx)) => {
                if let Some(text) = Self::key_text(self.keypad.get_key_content(idx)) {
                    self.input.on_key_click(ctx, idx, text);
                    self.update_keypad_state(ctx);
                }
                return None;
            }
            Some(KeypadMsg::EraseShort) => {
                self.input.on_erase(ctx, false);
                self.update_keypad_state(ctx);
                return None;
            }
            Some(KeypadMsg::EraseLong) => {
                self.input.on_erase(ctx, true);
                self.update_keypad_state(ctx);
                return None;
            }
            Some(KeypadMsg::Cancel) => {
                return Some(StringKeyboardMsg::Cancelled);
            }
            Some(KeypadMsg::Confirm) => {
                return Some(StringKeyboardMsg::Confirmed(unwrap!(
                    ShortString::try_from(self.input.content())
                )));
            }
            _ => {}
        }

        None
    }

    fn render<'s>(&'s self, target: &mut impl Renderer<'s>) {
        // Render prompt when the pin is empty
        if self.input.is_empty() {
            self.input_prompt.render(target);
        }

        // When the input area might overlap the keypad, it has to be rendered as the
        // second
        if self.input.might_overlap_keypad() {
            self.keypad.render(target);
            self.input.render(target);
        } else {
            // When the next button is pressed, it overlaps the keypad so it
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

#[cfg(feature = "micropython")]
impl<I: StringInput> Swipable for StringKeyboard<I> {
    fn get_swipe_config(&self) -> SwipeConfig {
        self.swipe_config
    }

    fn get_pager(&self) -> Pager {
        Pager::single_page()
    }
}

#[derive(PartialEq, Debug, Copy, Clone)]
#[cfg_attr(feature = "ui_debug", derive(ufmt::derive::uDebug))]
pub enum StringInputMsg {
    UpdateKeypad,
}

pub trait StringInput: Component<Msg = StringInputMsg> {
    // Actions
    fn on_page_change(&mut self, ctx: &mut EventCtx);
    fn get_keypad_state(&self) -> KeypadState;
    fn on_key_click(&mut self, ctx: &mut EventCtx, idx: usize, text: TString<'static>);
    fn on_erase(&mut self, ctx: &mut EventCtx, long_erase: bool);

    /// Basic input info.
    fn content(&self) -> &str;
    fn is_empty(&self) -> bool {
        self.content().is_empty()
    }
    fn is_full(&self) -> bool;

    // The information needed for the component render order
    fn might_overlap_keypad(&self) -> bool;
}

#[cfg(feature = "ui_debug")]
impl<I> crate::trace::Trace for StringKeyboard<I>
where
    I: StringInput + crate::trace::Trace,
{
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        let active_layout = uformat!("{:?}", self.active_layout);
        t.component("StringKeyboard");
        t.string("active_layout", active_layout.as_str().into());
        t.child("input", &self.input);
    }
}
