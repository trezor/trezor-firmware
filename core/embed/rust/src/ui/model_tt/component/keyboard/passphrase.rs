use crate::ui::{
    component::{base::ComponentExt, Child, Component, Event, EventCtx, Never},
    display,
    geometry::{Grid, Rect},
    model_tt::component::{
        button::{Button, ButtonContent, ButtonMsg::Clicked},
        keyboard::common::{array_map_enumerate, MultiTapKeyboard, TextBox},
        swipe::{Swipe, SwipeDirection},
        theme,
    },
};

pub enum PassphraseKeyboardMsg {
    Confirmed,
    Cancelled,
}

pub struct PassphraseKeyboard {
    page_swipe: Swipe,
    input: Child<Input>,
    back: Child<Button<&'static str>>,
    confirm: Child<Button<&'static str>>,
    keys: [[Child<Button<&'static str>>; KEY_COUNT]; PAGE_COUNT],
    key_page: usize,
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

const MAX_LENGTH: usize = 50;

impl PassphraseKeyboard {
    pub fn new(area: Rect) -> Self {
        let input_area = Grid::new(area, 5, 1).row_col(0, 0);
        let confirm_btn_area = Grid::new(area, 5, 3).cell(14);
        let back_btn_area = Grid::new(area, 5, 3).cell(12);
        let key_grid = Grid::new(area, 5, 3);

        Self {
            page_swipe: Swipe::horizontal(area),
            input: Input::new(input_area).into_child(),
            confirm: Button::with_text(confirm_btn_area, "Confirm")
                .styled(theme::button_confirm())
                .into_child(),
            back: Button::with_text(back_btn_area, "Back")
                .styled(theme::button_clear())
                .into_child(),
            keys: Self::generate_keyboard(&key_grid),
            key_page: STARTING_PAGE,
        }
    }

    fn generate_keyboard(grid: &Grid) -> [[Child<Button<&'static str>>; KEY_COUNT]; PAGE_COUNT] {
        array_map_enumerate(KEYBOARD, |_, page| {
            array_map_enumerate(page, |key, text| Self::generate_key(grid, key, text))
        })
    }

    fn generate_key(grid: &Grid, key: usize, text: &'static str) -> Child<Button<&'static str>> {
        // Assign the keys in each page to buttons on a 5x3 grid, starting from the
        // second row.
        let area = grid.cell(if key < 9 {
            // The grid has 3 columns, and we skip the first row.
            key + 3
        } else {
            // For the last key (the "0" position) we skip one cell.
            key + 1 + 3
        });
        if text == " " {
            let icon = theme::ICON_SPACE;
            Child::new(Button::with_icon(area, icon))
        } else {
            Child::new(Button::with_text(area, text))
        }
    }

    fn key_text(content: &ButtonContent<&'static str>) -> &'static str {
        match content {
            ButtonContent::Text(text) => text,
            ButtonContent::Icon(_) => " ",
            ButtonContent::Empty => "",
        }
    }

    fn on_page_swipe(&mut self, ctx: &mut EventCtx, swipe: SwipeDirection) {
        // Change the page number.
        self.key_page = match swipe {
            SwipeDirection::Left => (self.key_page as isize + 1) as usize % PAGE_COUNT,
            SwipeDirection::Right => (self.key_page as isize - 1) as usize % PAGE_COUNT,
            _ => self.key_page,
        };
        // Clear the pending state.
        self.input
            .mutate(ctx, |ctx, i| i.multi_tap.clear_pending_state(ctx));
        // Make sure to completely repaint the buttons.
        for btn in &mut self.keys[self.key_page] {
            btn.request_complete_repaint(ctx);
        }
    }

    fn after_edit(&mut self, ctx: &mut EventCtx) {
        if self.input.inner().textbox.is_empty() {
            self.back.mutate(ctx, |ctx, b| b.disable(ctx));
        } else {
            self.back.mutate(ctx, |ctx, b| b.enable(ctx));
        }
    }
}

impl Component for PassphraseKeyboard {
    type Msg = PassphraseKeyboardMsg;

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        if self.input.inner().multi_tap.is_timeout_event(event) {
            self.input
                .mutate(ctx, |ctx, i| i.multi_tap.clear_pending_state(ctx));
            return None;
        }
        if let Some(swipe) = self.page_swipe.event(ctx, event) {
            // We have detected a horizontal swipe. Change the keyboard page.
            self.on_page_swipe(ctx, swipe);
            return None;
        }
        if let Some(Clicked) = self.confirm.event(ctx, event) {
            // Confirm button was clicked, we're done.
            return Some(PassphraseKeyboardMsg::Confirmed);
        }
        if let Some(Clicked) = self.back.event(ctx, event) {
            // Backspace button was clicked. If we have any content in the textbox, let's
            // delete the last character. Otherwise cancel.
            return if self.input.inner().textbox.is_empty() {
                Some(PassphraseKeyboardMsg::Cancelled)
            } else {
                self.input.mutate(ctx, |ctx, i| {
                    i.multi_tap.clear_pending_state(ctx);
                    i.textbox.delete_last(ctx);
                });
                self.after_edit(ctx);
                None
            };
        }
        for (key, btn) in self.keys[self.key_page].iter_mut().enumerate() {
            if let Some(Clicked) = btn.event(ctx, event) {
                // Key button was clicked. If this button is pending, let's cycle the pending
                // character in textbox. If not, let's just append the first character.
                let text = Self::key_text(btn.inner().content());
                self.input.mutate(ctx, |ctx, i| {
                    let edit = i.multi_tap.click_key(ctx, key, text);
                    i.textbox.apply(ctx, edit);
                });
                self.after_edit(ctx);
                return None;
            }
        }
        None
    }

    fn paint(&mut self) {
        self.input.paint();
        self.confirm.paint();
        self.back.paint();
        for btn in &mut self.keys[self.key_page] {
            btn.paint();
        }
    }
}

struct Input {
    area: Rect,
    textbox: TextBox<MAX_LENGTH>,
    multi_tap: MultiTapKeyboard,
}

impl Input {
    fn new(area: Rect) -> Self {
        Self {
            area,
            textbox: TextBox::empty(),
            multi_tap: MultiTapKeyboard::new(),
        }
    }
}

impl Component for Input {
    type Msg = Never;

    fn event(&mut self, _ctx: &mut EventCtx, _event: Event) -> Option<Self::Msg> {
        None
    }

    fn paint(&mut self) {
        let style = theme::label_default();

        display::text(
            self.area.bottom_left(),
            self.textbox.content().as_bytes(),
            style.font,
            style.text_color,
            style.background_color,
        );
    }
}
