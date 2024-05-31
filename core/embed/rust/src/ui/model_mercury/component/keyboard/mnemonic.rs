use crate::{
    strutil::TString,
    ui::{
        component::{
            maybe::paint_overlapping, Child, Component, Event, EventCtx, Label, Maybe, Swipe,
            SwipeDirection,
        },
        geometry::{Alignment, Grid, Insets, Rect},
        model_mercury::{
            component::{Button, ButtonMsg},
            theme,
        },
        shape::Renderer,
    },
};

pub const MNEMONIC_KEY_COUNT: usize = 9;
const BACK_BUTTON_RIGHT_EXPAND: i16 = 24;

pub enum MnemonicKeyboardMsg {
    Confirmed,
    Previous,
}

pub struct MnemonicKeyboard<T> {
    /// Initial prompt, displayed on empty input.
    prompt: Child<Maybe<Label<'static>>>,
    /// Delete a char button.
    erase: Child<Maybe<Button>>,
    /// Go to previous word button
    back: Child<Maybe<Button>>,
    /// Input area, acting as the auto-complete and confirm button.
    input: Child<Maybe<T>>,
    /// Key buttons.
    keys: [Child<Button>; MNEMONIC_KEY_COUNT],
    /// Swipe controller - allowing for going to the previous word.
    swipe: Swipe,
    /// Whether going back is allowed (is not on the very first word).
    can_go_back: bool,
}

impl<T> MnemonicKeyboard<T>
where
    T: MnemonicInput,
{
    pub fn new(input: T, prompt: TString<'static>, can_go_back: bool) -> Self {
        // Input might be already pre-filled
        let prompt_visible = input.is_empty();
        let erase_btn = Button::with_icon(theme::ICON_DELETE)
            .styled(theme::button_default())
            .with_expanded_touch_area(Insets::right(BACK_BUTTON_RIGHT_EXPAND))
            .with_long_press(theme::ERASE_HOLD_DURATION);
        let back_btn = Button::with_icon(theme::ICON_CHEVRON_LEFT)
            .styled(theme::button_default())
            .with_expanded_touch_area(Insets::right(BACK_BUTTON_RIGHT_EXPAND));
        Self {
            prompt: Child::new(Maybe::new(
                theme::BG,
                Label::centered(prompt, theme::TEXT_MAIN_GREY_LIGHT).vertically_centered(),
                prompt_visible,
            )),
            erase: Child::new(Maybe::new(theme::BG, erase_btn, !prompt_visible)),
            back: Child::new(Maybe::new(
                theme::BG,
                back_btn,
                prompt_visible && can_go_back,
            )),
            input: Child::new(Maybe::new(theme::BG, input, !prompt_visible)),
            keys: T::keys()
                .map(|t| {
                    Button::with_text(t.into())
                        .styled(theme::button_keyboard())
                        .with_text_align(Alignment::Center)
                })
                .map(Child::new),
            swipe: Swipe::new().right(),
            can_go_back,
        }
    }

    fn on_input_change(&mut self, ctx: &mut EventCtx) {
        self.toggle_key_buttons(ctx);
        self.toggle_prompt_or_input(ctx);
    }

    /// Either enable or disable the key buttons, depending on the dictionary
    /// completion mask and the pending key.
    fn toggle_key_buttons(&mut self, ctx: &mut EventCtx) {
        for (key, btn) in self.keys.iter_mut().enumerate() {
            let enabled = self
                .input
                .inner()
                .inner()
                .can_key_press_lead_to_a_valid_word(key);
            btn.mutate(ctx, |ctx, b| b.enable_if(ctx, enabled));
        }
    }

    /// After edit operations, we need to either show or hide the prompt, the
    /// input, the erase button and the back button.
    fn toggle_prompt_or_input(&mut self, ctx: &mut EventCtx) {
        let prompt_visible = self.input.inner().inner().is_empty();
        self.prompt
            .mutate(ctx, |ctx, p| p.show_if(ctx, prompt_visible));
        self.input
            .mutate(ctx, |ctx, i| i.show_if(ctx, !prompt_visible));
        self.erase
            .mutate(ctx, |ctx, b| b.show_if(ctx, !prompt_visible));
        self.back.mutate(ctx, |ctx, b| {
            b.show_if(ctx, prompt_visible && self.can_go_back)
        });
    }

    pub fn mnemonic(&self) -> Option<&'static str> {
        self.input.inner().inner().mnemonic()
    }
}

impl<T> Component for MnemonicKeyboard<T>
where
    T: MnemonicInput,
{
    type Msg = MnemonicKeyboardMsg;

    fn place(&mut self, bounds: Rect) -> Rect {
        let height_input_area: i16 = 38;
        let padding_top: i16 = 6;
        let back_btn_area_width: i16 = 32;
        let (remaining, keyboard_area) =
            bounds.split_bottom(3 * theme::MNEMONIC_BUTTON_HEIGHT + 2 * theme::KEYBOARD_SPACING);
        let prompt_area = remaining
            .split_top(padding_top)
            .1
            .split_top(height_input_area)
            .0;
        assert!(prompt_area.height() == height_input_area);

        let (back_btn_area, input_area) = prompt_area.split_left(back_btn_area_width);
        let input_area = input_area.inset(Insets::left(BACK_BUTTON_RIGHT_EXPAND));
        let keyboard_grid = Grid::new(keyboard_area, 3, 3).with_spacing(theme::KEYBOARD_SPACING);

        self.swipe.place(bounds);
        self.prompt.place(prompt_area);
        self.erase.place(back_btn_area);
        self.back.place(back_btn_area);
        self.input.place(input_area);

        for (key, btn) in self.keys.iter_mut().enumerate() {
            btn.place(keyboard_grid.cell(key));
        }
        bounds
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        // Back button or swipe will cause going back to the previous word when allowed.
        if self.can_go_back {
            if let Some(ButtonMsg::Clicked) = self.back.event(ctx, event) {
                return Some(MnemonicKeyboardMsg::Previous);
            }
            if let Some(SwipeDirection::Right) = self.swipe.event(ctx, event) {
                return Some(MnemonicKeyboardMsg::Previous);
            }
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

        match self.erase.event(ctx, event) {
            Some(ButtonMsg::Clicked) => {
                self.input
                    .mutate(ctx, |ctx, i| i.inner_mut().on_backspace_click(ctx));
                self.on_input_change(ctx);
                return None;
            }
            Some(ButtonMsg::LongPressed) => {
                self.input
                    .mutate(ctx, |ctx, i| i.inner_mut().on_backspace_long_press(ctx));
                self.on_input_change(ctx);
                return None;
            }
            _ => {}
        }
        for (key, btn) in self.keys.iter_mut().enumerate() {
            if let Some(ButtonMsg::Clicked) = btn.event(ctx, event) {
                self.input
                    .mutate(ctx, |ctx, i| i.inner_mut().on_key_click(ctx, key));
                self.on_input_change(ctx);
                return None;
            }
        }
        None
    }

    fn paint(&mut self) {
        paint_overlapping(&mut [&mut self.prompt, &mut self.input, &mut self.erase]);
        for btn in &mut self.keys {
            btn.paint();
        }
    }

    fn render<'s>(&'s self, target: &mut impl Renderer<'s>) {
        if self.input.inner().inner().is_empty() {
            self.prompt.render(target);
            if self.can_go_back {
                self.back.render(target);
            }
        } else {
            self.input.render(target);
            self.erase.render(target);
        }

        for btn in &self.keys {
            btn.render(target);
        }
    }

    #[cfg(feature = "ui_bounds")]
    fn bounds(&self, sink: &mut dyn FnMut(Rect)) {
        self.prompt.bounds(sink);
        self.input.bounds(sink);
        self.erase.bounds(sink);
        self.back.bounds(sink);
        for btn in &self.keys {
            btn.bounds(sink)
        }
    }
}

pub trait MnemonicInput: Component<Msg = MnemonicInputMsg> {
    fn keys() -> [&'static str; MNEMONIC_KEY_COUNT];
    fn can_key_press_lead_to_a_valid_word(&self, key: usize) -> bool;
    fn on_key_click(&mut self, ctx: &mut EventCtx, key: usize);
    fn on_backspace_click(&mut self, ctx: &mut EventCtx);
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
