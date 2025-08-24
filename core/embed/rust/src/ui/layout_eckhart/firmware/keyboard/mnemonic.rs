use crate::{
    strutil::TString,
    translations::TR,
    ui::{
        component::{Component, Event, EventCtx, Label},
        geometry::Rect,
        shape::Renderer,
    },
};

use super::super::super::{
    component::ButtonContent,
    constant::SCREEN,
    firmware::keyboard::{
        common::{INPUT_TOUCH_HEIGHT, KEYBOARD_INPUT_INSETS, KEYPAD_VISIBLE_HEIGHT},
        keypad::{ButtonState, Keypad, KeypadButton, KeypadMsg},
    },
    theme,
};

pub const MNEMONIC_KEY_COUNT: usize = 9;

pub enum MnemonicKeyboardMsg {
    Confirmed,
    Previous,
}

pub struct MnemonicKeyboard<T> {
    /// Initial prompt, displayed on empty input.
    prompt: Label<'static>,
    word_prompt: Label<'static>,
    /// Input area, acting as the auto-complete.
    input: T,
    /// Key buttons.
    keypad: Keypad,
    /// Whether going back is allowed (is not on the very first word).
    can_go_back: bool,
}

impl<T> MnemonicKeyboard<T>
where
    T: MnemonicInput,
{
    pub const KEY_COUNT: usize = 9;
    // Ad hoc number that so that all languages can reasonably show the word number
    // prompt
    const WORD_PROMPT_WIDTH: i16 = 85;
    pub fn new(input: T, words: TString<'static>, can_go_back: bool) -> Self {
        let keypad_content: [_; MNEMONIC_KEY_COUNT] =
            core::array::from_fn(|idx| ButtonContent::single_line_text(T::keys()[idx].into()));

        Self {
            prompt: Label::left_aligned(
                TR::recovery__start_entering.into(),
                theme::firmware::TEXT_SMALL,
            )
            .vertically_centered(),
            word_prompt: Label::centered(words, theme::TEXT_SMALL_LIGHT).vertically_centered(),
            keypad: Keypad::new_hidden().with_keys_content(&keypad_content),
            can_go_back,
            input,
        }
    }

    fn on_input_change(&mut self, ctx: &mut EventCtx) {
        self.toggle_buttons(ctx);
    }

    /// Either enable or disable the key buttons, depending on the dictionary
    /// completion mask and the pending key.
    fn toggle_buttons(&mut self, ctx: &mut EventCtx) {
        // Enable/disable the key buttons based on the ability to form a valid word.
        for idx in 0..Self::KEY_COUNT {
            let state = if self.input.can_key_press_lead_to_a_valid_word(idx) {
                ButtonState::Enabled
            } else {
                ButtonState::Disabled
            };
            self.keypad
                .set_button_state(ctx, KeypadButton::Key(idx), &state);
        }

        // Determine states for erase and back buttons
        let (erase_state, back_state) = if self.input.is_empty() {
            (
                ButtonState::Hidden,
                if self.can_go_back {
                    ButtonState::Enabled
                } else {
                    ButtonState::Hidden
                },
            )
        } else {
            (ButtonState::Enabled, ButtonState::Hidden)
        };

        // Determine state and style for the confirm button based on input state
        let confirm_state = if self.input.is_empty() || self.input.mnemonic().is_none() {
            ButtonState::Hidden
        } else {
            ButtonState::Enabled
        };
        let confirm_style = if self.input.mnemonic().is_some() {
            let any_press_can_lead_to_valid_word = || {
                (0..Self::KEY_COUNT).any(|idx| self.input.can_key_press_lead_to_a_valid_word(idx))
            };
            if any_press_can_lead_to_valid_word() {
                theme::button_keyboard()
            } else {
                theme::button_keyboard_confirm()
            }
        } else {
            theme::button_keyboard()
        };

        // Apply all button states
        self.keypad
            .set_button_state(ctx, KeypadButton::Erase, &erase_state);
        self.keypad
            .set_button_state(ctx, KeypadButton::Back, &back_state);
        self.keypad
            .set_button_state(ctx, KeypadButton::Confirm, &confirm_state);

        // Apply the stylesheet for the confirm button
        self.keypad
            .set_button_stylesheet(KeypadButton::Confirm, confirm_style);
    }

    fn render_prompt_or_input<'s>(&'s self, target: &mut impl Renderer<'s>) {
        if self.input.is_empty() {
            self.prompt.render(target);
            self.word_prompt.render(target);
        } else {
            self.input.render(target);
        }
    }

    pub fn mnemonic(&self) -> Option<&'static str> {
        self.input.mnemonic()
    }
}

impl<T> Component for MnemonicKeyboard<T>
where
    T: MnemonicInput,
{
    type Msg = MnemonicKeyboardMsg;

    fn place(&mut self, bounds: Rect) -> Rect {
        // assert full screen
        debug_assert_eq!(bounds.height(), SCREEN.height());
        debug_assert_eq!(bounds.width(), SCREEN.width());

        // Keypad and input areas are overlapped
        let (_, keypad_area) = bounds.split_bottom(KEYPAD_VISIBLE_HEIGHT);
        let (input_area, _) = bounds.split_top(INPUT_TOUCH_HEIGHT);

        let (prompt_area, word_prompt_area) = input_area
            .inset(KEYBOARD_INPUT_INSETS)
            .split_right(Self::WORD_PROMPT_WIDTH);
        let input_area = input_area.inset(KEYBOARD_INPUT_INSETS);

        // Prompt/input placement
        self.prompt.place(prompt_area);
        self.word_prompt.place(word_prompt_area);
        self.input.place(input_area);

        // Keypad placement
        self.keypad.place(keypad_area);

        bounds
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        if let Event::Attach(_) = event {
            self.on_input_change(ctx);
        }

        match self.input.event(ctx, event) {
            Some(MnemonicInputMsg::Confirmed) => {
                // Confirmed, bubble up.
                return Some(MnemonicKeyboardMsg::Confirmed);
            }
            Some(_) => {
                // Either a timeout or a completion.
                self.on_input_change(ctx);
                return None;
            }
            _ => {}
        }

        match self.keypad.event(ctx, event) {
            Some(KeypadMsg::Key(idx)) => {
                self.input.on_key_click(ctx, idx);
                self.on_input_change(ctx);
                return None;
            }
            Some(KeypadMsg::Back) => {
                // Back button will cause going back to the previous word when allowed.
                if self.can_go_back {
                    return Some(MnemonicKeyboardMsg::Previous);
                }
            }
            Some(KeypadMsg::EraseShort) => {
                self.input.on_backspace_click(ctx);
                self.on_input_change(ctx);
                return None;
            }
            Some(KeypadMsg::EraseLong) => {
                self.input.on_backspace_long_press(ctx);
                self.on_input_change(ctx);
                return None;
            }
            Some(KeypadMsg::Confirm) => {
                match self.input.on_confirm_click(ctx) {
                    Some(MnemonicInputMsg::Confirmed) => {
                        // Confirmed, bubble up.
                        return Some(MnemonicKeyboardMsg::Confirmed);
                    }
                    Some(_) => {
                        // Either a timeout or a completion.
                        self.on_input_change(ctx);
                        return None;
                    }
                    _ => {}
                }
            }
            _ => {}
        }

        None
    }

    fn render<'s>(&'s self, target: &mut impl Renderer<'s>) {
        if self.keypad.pressed() {
            self.render_prompt_or_input(target);
            self.keypad.render(target);
        } else {
            self.keypad.render(target);
            self.render_prompt_or_input(target);
        }
    }
}

pub trait MnemonicInput: Component<Msg = MnemonicInputMsg> {
    fn keys() -> [&'static str; MNEMONIC_KEY_COUNT];
    fn can_key_press_lead_to_a_valid_word(&self, key: usize) -> bool;
    fn can_be_confirmed(&self) -> bool;
    fn on_key_click(&mut self, ctx: &mut EventCtx, key: usize);
    fn on_backspace_click(&mut self, ctx: &mut EventCtx);
    fn on_confirm_click(&mut self, ctx: &mut EventCtx) -> Option<MnemonicInputMsg>;
    fn on_backspace_long_press(&mut self, ctx: &mut EventCtx);
    fn is_empty(&self) -> bool;
    fn mnemonic(&self) -> Option<&'static str>;
}

pub enum MnemonicInputMsg {
    Confirmed,
    Completed,
    TimedOut,
}

#[cfg(feature = "ui_debug")]
impl<T> crate::trace::Trace for MnemonicKeyboard<T>
where
    T: MnemonicInput + crate::trace::Trace,
{
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.component("MnemonicKeyboard");
        t.child("prompt", &self.prompt);
        t.child("input", &self.input);
    }
}
