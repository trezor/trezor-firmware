use core::ops::Deref;

use crate::ui::{
    component::{Child, Component, Event, EventCtx, Label, Maybe},
    geometry::{Alignment, Grid, Rect},
    model_tt::{
        component::{Button, ButtonMsg},
        theme,
    },
};

pub const MNEMONIC_KEY_COUNT: usize = 9;

pub enum MnemonicKeyboardMsg {
    Confirmed,
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
}

impl<T, U> MnemonicKeyboard<T, U>
where
    T: MnemonicInput,
    U: Deref<Target = str>,
{
    pub fn new(input: T, prompt: U) -> Self {
        Self {
            prompt: Child::new(Maybe::visible(
                theme::BG,
                Label::centered(prompt, theme::label_keyboard()),
            )),
            back: Child::new(Maybe::hidden(
                theme::BG,
                Button::with_icon(theme::ICON_BACK).styled(theme::button_clear()),
            )),
            input: Child::new(Maybe::hidden(theme::BG, input)),
            keys: T::keys().map(Button::with_text).map(Child::new),
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
    U: Deref<Target = str>,
{
    type Msg = MnemonicKeyboardMsg;

    fn place(&mut self, bounds: Rect) -> Rect {
        let grid =
            Grid::new(bounds.inset(theme::borders()), 4, 3).with_spacing(theme::KEYBOARD_SPACING);
        let back_area = grid.row_col(0, 0);
        let input_area = grid.row_col(0, 1).union(grid.row_col(0, 3));

        let prompt_center = grid.row_col(0, 0).union(grid.row_col(0, 3)).center();
        let prompt_size = self.prompt.inner().inner().size();
        let prompt_top_left = prompt_size.snap(prompt_center, Alignment::Center, Alignment::Center);
        let prompt_area = Rect::from_top_left_and_size(prompt_top_left, prompt_size);

        self.prompt.place(prompt_area);
        self.back.place(back_area);
        self.input.place(input_area);
        for (key, btn) in self.keys.iter_mut().enumerate() {
            btn.place(grid.cell(key + grid.cols)); // Start in the second row.
        }
        bounds
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
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
        if let Some(ButtonMsg::Clicked) = self.back.event(ctx, event) {
            self.input
                .mutate(ctx, |ctx, i| i.inner_mut().on_backspace_click(ctx));
            self.on_input_change(ctx);
            return None;
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
        self.prompt.paint();
        self.input.paint();
        self.back.paint();
        for btn in &mut self.keys {
            btn.paint();
        }
    }

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
    fn is_empty(&self) -> bool;
    fn mnemonic(&self) -> Option<&'static str>;
}

pub enum MnemonicInputMsg {
    Confirmed,
    Completed,
    TimedOut,
}

#[cfg(feature = "ui_debug")]
impl<T, U> crate::trace::Trace for MnemonicKeyboard<T, U> {
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.open("MnemonicKeyboard");
        t.close();
    }
}
