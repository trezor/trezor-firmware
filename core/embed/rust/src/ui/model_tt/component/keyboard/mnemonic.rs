use crate::ui::{
    component::{maybe::paint_overlapping, Child, Component, Event, EventCtx, Label, Maybe},
    geometry::{Alignment2D, Grid, Offset, Rect},
    model_tt::{
        component::{Button, ButtonMsg, Swipe, SwipeDirection},
        theme,
    },
};

pub const MNEMONIC_KEY_COUNT: usize = 9;

pub enum MnemonicKeyboardMsg {
    Confirmed,
    Previous,
}

pub struct MnemonicKeyboard<T, U> {
    /// Initial prompt, displayed on empty input.
    prompt: Child<Maybe<Label<U>>>,
    /// Backspace button.
    back: Child<Maybe<Button<&'static str>>>,
    /// Input area, acting as the auto-complete and confirm button.
    input: Child<Maybe<T>>,
    /// Key buttons.
    keys: [Child<Button<&'static str>>; MNEMONIC_KEY_COUNT],
    /// Swipe controller - allowing for going to the previous word.
    swipe: Swipe,
    /// Whether going back is allowed (is not on the very first word).
    can_go_back: bool,
}

impl<T, U> MnemonicKeyboard<T, U>
where
    T: MnemonicInput,
    U: AsRef<str>,
{
    pub fn new(input: T, prompt: U, can_go_back: bool) -> Self {
        // Input might be already pre-filled
        let prompt_visible = input.is_empty();

        Self {
            prompt: Child::new(Maybe::new(
                theme::BG,
                Label::centered(prompt, theme::label_keyboard_prompt()),
                prompt_visible,
            )),
            back: Child::new(Maybe::new(
                theme::BG,
                Button::with_icon_blend(
                    theme::IMAGE_BG_BACK_BTN_TALL,
                    theme::ICON_BACK,
                    Offset::new(30, 17),
                )
                .styled(theme::button_reset())
                .with_long_press(theme::ERASE_HOLD_DURATION),
                !prompt_visible,
            )),
            input: Child::new(Maybe::new(theme::BG, input, !prompt_visible)),
            keys: T::keys()
                .map(|t| Button::with_text(t).styled(theme::button_pin()))
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
    /// input, and the back button.
    fn toggle_prompt_or_input(&mut self, ctx: &mut EventCtx) {
        let prompt_visible = self.input.inner().inner().is_empty();
        self.prompt
            .mutate(ctx, |ctx, p| p.show_if(ctx, prompt_visible));
        self.input
            .mutate(ctx, |ctx, i| i.show_if(ctx, !prompt_visible));
        self.back
            .mutate(ctx, |ctx, b| b.show_if(ctx, !prompt_visible));
    }

    pub fn mnemonic(&self) -> Option<&'static str> {
        self.input.inner().inner().mnemonic()
    }
}

impl<T, U> Component for MnemonicKeyboard<T, U>
where
    T: MnemonicInput,
    U: AsRef<str>,
{
    type Msg = MnemonicKeyboardMsg;

    fn place(&mut self, bounds: Rect) -> Rect {
        let (_, bounds) = bounds
            .inset(theme::borders())
            .split_bottom(4 * theme::MNEMONIC_BUTTON_HEIGHT + 3 * theme::KEYBOARD_SPACING);
        let grid = Grid::new(bounds, 4, 3).with_spacing(theme::KEYBOARD_SPACING);
        let back_area = grid.row_col(0, 0);
        let input_area = grid.row_col(0, 1).union(grid.row_col(0, 3));

        let prompt_center = grid.row_col(0, 0).union(grid.row_col(0, 3)).center();
        let prompt_size = self.prompt.inner().inner().max_size();
        let prompt_area = Rect::snap(prompt_center, prompt_size, Alignment2D::CENTER);

        self.swipe.place(bounds);
        self.prompt.place(prompt_area);
        self.back.place(back_area);
        self.input.place(input_area);
        for (key, btn) in self.keys.iter_mut().enumerate() {
            btn.place(grid.cell(key + grid.cols)); // Start in the second row.
        }
        bounds
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        // Swipe will cause going back to the previous word when allowed.
        if self.can_go_back {
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

        match self.back.event(ctx, event) {
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
        paint_overlapping(&mut [&mut self.prompt, &mut self.input, &mut self.back]);
        for btn in &mut self.keys {
            btn.paint();
        }
    }

    #[cfg(feature = "ui_bounds")]
    fn bounds(&self, sink: &mut dyn FnMut(Rect)) {
        self.prompt.bounds(sink);
        self.input.bounds(sink);
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
impl<T, U> crate::trace::Trace for MnemonicKeyboard<T, U>
where
    T: MnemonicInput + crate::trace::Trace,
    U: AsRef<str>,
{
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.component("MnemonicKeyboard");
        t.child("prompt", &self.prompt);
        t.child("input", &self.input);
    }
}
