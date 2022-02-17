use crate::ui::{
    component::{Child, Component, Event, EventCtx, Label, Maybe},
    geometry::{Grid, Rect},
    model_tt::{
        component::{keyboard::common::array_map_enumerate, Button, ButtonMsg},
        theme,
    },
};

pub const MNEMONIC_KEY_COUNT: usize = 9;

pub enum MnemonicKeyboardMsg {
    Confirmed,
}

pub struct MnemonicKeyboard<T> {
    /// Initial prompt, displayed on empty input.
    prompt: Child<Maybe<Label<&'static [u8]>>>,
    /// Backspace button.
    back: Child<Maybe<Button<&'static [u8]>>>,
    /// Input area, acting as the auto-complete and confirm button.
    input: Child<Maybe<T>>,
    /// Key buttons.
    keys: [Child<Button<&'static [u8]>>; MNEMONIC_KEY_COUNT],
}

impl<T> MnemonicKeyboard<T>
where
    T: MnemonicInput,
{
    pub fn new(area: Rect, prompt: &'static [u8]) -> Self {
        let grid = Grid::new(area, 3, 4);
        let back_area = grid.row_col(0, 0);
        let input_area = grid.row_col(0, 1).union(grid.row_col(0, 3));
        let prompt_area = grid.row_col(0, 0).union(grid.row_col(0, 3));
        let prompt_origin = prompt_area.top_left();

        let input = T::new(input_area);
        let keys = T::keys();

        Self {
            prompt: Child::new(Maybe::visible(
                prompt_area,
                theme::BG,
                Label::left_aligned(prompt_origin, prompt, theme::label_default()),
            )),
            back: Child::new(Maybe::hidden(
                back_area,
                theme::BG,
                Button::with_icon(back_area, theme::ICON_BACK).styled(theme::button_clear()),
            )),
            input: Child::new(Maybe::hidden(input_area, theme::BG, input)),
            keys: Self::key_buttons(keys, &grid, grid.cols), // Start in the second row.
        }
    }

    fn key_buttons(
        keys: [&'static str; MNEMONIC_KEY_COUNT],
        grid: &Grid,
        offset: usize,
    ) -> [Child<Button<&'static [u8]>>; MNEMONIC_KEY_COUNT] {
        array_map_enumerate(keys, |index, text| {
            Child::new(Button::with_text(
                grid.cell(offset + index),
                text.as_bytes(),
            ))
        })
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
            btn.mutate(ctx, |ctx, b| b.enabled(ctx, enabled));
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
}

impl<T> Component for MnemonicKeyboard<T>
where
    T: MnemonicInput,
{
    type Msg = MnemonicKeyboardMsg;

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
}

pub trait MnemonicInput: Component<Msg = MnemonicInputMsg> {
    fn new(area: Rect) -> Self;
    fn keys() -> [&'static str; MNEMONIC_KEY_COUNT];
    fn can_key_press_lead_to_a_valid_word(&self, key: usize) -> bool;
    fn on_key_click(&mut self, ctx: &mut EventCtx, key: usize);
    fn on_backspace_click(&mut self, ctx: &mut EventCtx);
    fn is_empty(&self) -> bool;
}

pub enum MnemonicInputMsg {
    Confirmed,
    Completed,
    TimedOut,
}
