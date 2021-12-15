use core::time::Duration;

use heapless::Vec;

use crate::ui::{
    component::{Child, Component, Event, EventCtx, Never, TimerToken},
    display,
    geometry::{Grid, Rect},
};

use super::{
    button::{Button, ButtonContent, ButtonMsg::Clicked},
    swipe::{Swipe, SwipeDirection},
    theme,
};

pub enum PassphraseKeyboardMsg {
    Confirmed,
    Cancelled,
}

pub struct PassphraseKeyboard {
    page_swipe: Swipe,
    textbox: Child<TextBox>,
    back_btn: Child<Button>,
    confirm_btn: Child<Button>,
    key_btns: [[Child<Button>; KEYS]; PAGES],
    key_page: usize,
    pending: Option<Pending>,
}

struct Pending {
    key: usize,
    char: usize,
    timer: TimerToken,
}

const MAX_LENGTH: usize = 50;
const STARTING_PAGE: usize = 1;
const PAGES: usize = 4;
const KEYS: usize = 10;
const PENDING_DEADLINE: Duration = Duration::from_secs(1);

impl PassphraseKeyboard {
    pub fn new(area: Rect) -> Self {
        let textbox_area = Grid::new(area, 5, 1).row_col(0, 0);
        let confirm_btn_area = Grid::new(area, 5, 3).cell(14);
        let back_btn_area = Grid::new(area, 5, 3).cell(12);
        let key_grid = Grid::new(area, 5, 3);

        let text = Vec::new();
        let page_swipe = Swipe::horizontal(area);
        let textbox = Child::new(TextBox::new(textbox_area, text));
        let confirm_btn = Child::new(Button::with_text(
            confirm_btn_area,
            b"Confirm",
            theme::button_confirm(),
        ));
        let back_btn = Child::new(Button::with_text(
            back_btn_area,
            b"Back",
            theme::button_clear(),
        ));
        let key_btns = Self::generate_keyboard(&key_grid);

        Self {
            textbox,
            page_swipe,
            confirm_btn,
            back_btn,
            key_btns,
            key_page: STARTING_PAGE,
            pending: None,
        }
    }

    fn generate_keyboard(grid: &Grid) -> [[Child<Button>; KEYS]; PAGES] {
        [
            Self::generate_key_page(grid, 0),
            Self::generate_key_page(grid, 1),
            Self::generate_key_page(grid, 2),
            Self::generate_key_page(grid, 3),
        ]
    }

    fn generate_key_page(grid: &Grid, page: usize) -> [Child<Button>; KEYS] {
        [
            Self::generate_key(grid, page, 0),
            Self::generate_key(grid, page, 1),
            Self::generate_key(grid, page, 2),
            Self::generate_key(grid, page, 3),
            Self::generate_key(grid, page, 4),
            Self::generate_key(grid, page, 5),
            Self::generate_key(grid, page, 6),
            Self::generate_key(grid, page, 7),
            Self::generate_key(grid, page, 8),
            Self::generate_key(grid, page, 9),
        ]
    }

    fn generate_key(grid: &Grid, page: usize, key: usize) -> Child<Button> {
        #[rustfmt::skip]
        const KEYBOARD: [[&str; KEYS]; PAGES] = [
            ["1", "2", "3", "4", "5", "6", "7", "8", "9", "0"],
            [" ", "abc", "def", "ghi", "jkl", "mno", "pqrs", "tuv", "wxyz", "*#"],
            [" ", "ABC", "DEF", "GHI", "JKL", "MNO", "PQRS", "TUV", "WXYZ", "*#"],
            ["_<>", ".:@", "/|\\", "!()", "+%&", "-[]", "?{}", ",'`", ";\"~", "$^="],
        ];

        // Assign the keys in each page to buttons on a 5x3 grid, starting from the
        // second row.
        let area = grid.cell(if key < 9 {
            // The grid has 3 columns, and we skip the first row.
            key + 3
        } else {
            // For the last key (the "0" position) we skip one cell.
            key + 1 + 3
        });
        let text = KEYBOARD[page][key].as_bytes();
        if text == b" " {
            let icon = theme::ICON_SPACE;
            Child::new(Button::with_icon(area, icon, theme::button_default()))
        } else {
            Child::new(Button::with_text(area, text, theme::button_default()))
        }
    }

    fn on_page_swipe(&mut self, swipe: SwipeDirection) {
        self.key_page = match swipe {
            SwipeDirection::Left => (self.key_page as isize + 1) as usize % PAGES,
            SwipeDirection::Right => (self.key_page as isize - 1) as usize % PAGES,
            _ => self.key_page,
        };
        self.pending.take();
    }

    fn on_backspace_click(&mut self, ctx: &mut EventCtx) {
        self.pending.take();
        self.textbox.mutate(ctx, |ctx, t| t.delete_last(ctx));
        self.after_edit(ctx);
    }

    fn on_key_click(&mut self, ctx: &mut EventCtx, key: usize) {
        let content = self.key_content(self.key_page, key);

        let char = match &self.pending {
            Some(pending) if pending.key == key => {
                // This key is pending. Cycle the last inserted character through the
                // key content.
                let char = (pending.char + 1) % content.len();
                self.textbox
                    .mutate(ctx, |ctx, t| t.replace_last(ctx, content[char]));
                char
            }
            _ => {
                // This key is not pending. Append the first character in the key.
                let char = 0;
                self.textbox
                    .mutate(ctx, |ctx, t| t.append(ctx, content[char]));
                char
            }
        };

        // If the key has more then one character, we need to set it as pending, so we
        // can cycle through on the repeated clicks. We also request a timer so we can
        // reset the pending state after a deadline.
        self.pending = if content.len() > 1 {
            Some(Pending {
                key,
                char,
                timer: ctx.request_timer(PENDING_DEADLINE),
            })
        } else {
            None
        };
        let is_pending = self.pending.is_some();
        self.textbox
            .mutate(ctx, |ctx, t| t.toggle_pending_marker(ctx, is_pending));

        self.after_edit(ctx);
    }

    fn on_timeout(&mut self) {
        self.pending.take();
    }

    fn key_content(&self, page: usize, key: usize) -> &'static [u8] {
        match self.key_btns[page][key].inner().content() {
            ButtonContent::Text(text) => text,
            ButtonContent::Icon(_) => b" ",
        }
    }

    fn after_edit(&mut self, ctx: &mut EventCtx) {
        if self.textbox.inner().is_empty() {
            self.back_btn.mutate(ctx, |ctx, b| b.disable(ctx));
        } else {
            self.back_btn.mutate(ctx, |ctx, b| b.enable(ctx));
        }
    }
}

impl Component for PassphraseKeyboard {
    type Msg = PassphraseKeyboardMsg;

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        if matches!((event, &self.pending), (Event::Timer(t), Some(p)) if p.timer == t) {
            // Our pending timer triggered, reset the pending state.
            self.on_timeout();
            return None;
        }
        if let Some(swipe) = self.page_swipe.event(ctx, event) {
            // We have detected a horizontal swipe. Change the keyboard page.
            self.on_page_swipe(swipe);
            return None;
        }
        if let Some(Clicked) = self.confirm_btn.event(ctx, event) {
            // Confirm button was clicked, we're done.
            return Some(PassphraseKeyboardMsg::Confirmed);
        }
        if let Some(Clicked) = self.back_btn.event(ctx, event) {
            // Backspace button was clicked. If we have any content in the textbox, let's
            // delete the last character. Otherwise cancel.
            if self.textbox.inner().is_empty() {
                return Some(PassphraseKeyboardMsg::Cancelled);
            } else {
                self.on_backspace_click(ctx);
                return None;
            }
        }
        for (key, btn) in self.key_btns[self.key_page].iter_mut().enumerate() {
            if let Some(Clicked) = btn.event(ctx, event) {
                // Key button was clicked. If this button is pending, let's cycle the pending
                // character in textbox. If not, let's just append the first character.
                self.on_key_click(ctx, key);
                return None;
            }
        }
        None
    }

    fn paint(&mut self) {
        self.textbox.paint();
        self.confirm_btn.paint();
        self.back_btn.paint();
        for btn in &mut self.key_btns[self.key_page] {
            btn.paint();
        }
    }
}

struct TextBox {
    area: Rect,
    text: Vec<u8, MAX_LENGTH>,
    pending: bool,
}

impl TextBox {
    fn new(area: Rect, text: Vec<u8, MAX_LENGTH>) -> Self {
        Self {
            area,
            text,
            pending: false,
        }
    }

    fn is_empty(&self) -> bool {
        self.text.is_empty()
    }

    fn toggle_pending_marker(&mut self, ctx: &mut EventCtx, pending: bool) {
        self.pending = pending;
        ctx.request_paint();
    }

    fn delete_last(&mut self, ctx: &mut EventCtx) {
        self.text.pop();
        ctx.request_paint();
    }

    fn replace_last(&mut self, ctx: &mut EventCtx, char: u8) {
        self.text.pop();
        if self.text.push(char).is_err() {
            // Should not happen unless `self.text` has zero capacity.
            #[cfg(feature = "ui_debug")]
            panic!("Textbox has zero capacity");
        }
        ctx.request_paint();
    }

    fn append(&mut self, ctx: &mut EventCtx, char: u8) {
        if self.text.push(char).is_err() {
            // `self.text` is full, ignore this change.
            #[cfg(feature = "ui_debug")]
            panic!("Textbox is full");
        }
        ctx.request_paint();
    }
}

impl Component for TextBox {
    type Msg = Never;

    fn event(&mut self, _ctx: &mut EventCtx, _event: Event) -> Option<Self::Msg> {
        None
    }

    fn paint(&mut self) {
        let style = theme::label_default();

        display::text(
            self.area.bottom_left(),
            &self.text,
            style.font,
            style.text_color,
            style.background_color,
        );
    }
}
