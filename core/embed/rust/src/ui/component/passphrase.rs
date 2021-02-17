use core::time::Duration;

use staticvec::StaticVec;

use crate::ui::{
    display,
    math::{Grid, Rect},
    theme,
};

use super::{
    button::{Button, ButtonContent, ButtonMsg::Clicked},
    component::{Component, Event, EventCtx, TimerToken, Widget},
    swipe::{Swipe, SwipeDirection},
};

pub enum PassphraseKeyboardMsg {
    Confirmed,
    Cancelled,
}

pub struct PassphraseKeyboard {
    widget: Widget,
    textbox: TextBox,
    page_swipe: Swipe,
    back_btn: Button,
    confirm_btn: Button,
    key_btns: [[Button; KEYS]; PAGES],
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

        let text = StaticVec::new();
        let textbox = TextBox::new(textbox_area, text);
        let page_swipe = Swipe::horizontal(area);
        let confirm_btn = Button::with_text(
            confirm_btn_area,
            "Confirm".as_bytes(),
            theme::button_confirm(),
        );
        let back_btn = Button::with_text(back_btn_area, "Back".as_bytes(), theme::button_clear());
        let key_btns = Self::generate_keyboard(&key_grid);

        Self {
            widget: Widget::new(area),
            textbox,
            page_swipe,
            confirm_btn,
            back_btn,
            key_btns,
            key_page: STARTING_PAGE,
            pending: None,
        }
    }

    fn generate_keyboard(grid: &Grid) -> [[Button; KEYS]; PAGES] {
        [
            Self::generate_key_page(grid, 0),
            Self::generate_key_page(grid, 1),
            Self::generate_key_page(grid, 2),
            Self::generate_key_page(grid, 3),
        ]
    }

    fn generate_key_page(grid: &Grid, page: usize) -> [Button; KEYS] {
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

    fn generate_key(grid: &Grid, page: usize, key: usize) -> Button {
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
        if text == " ".as_bytes() {
            todo!()
        } else {
            Button::with_text(area, text, theme::button_default())
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

    fn on_backspace_click(&mut self) {
        self.pending.take();
        self.textbox.delete_last();
        self.after_edit();
    }

    fn on_key_click(&mut self, ctx: &mut EventCtx, key: usize) {
        let content = self.key_content(self.key_page, key);

        let char = match &self.pending {
            Some(pending) if pending.key == key => {
                // This key is pending. Cycle the last inserted character through the
                // key content.
                let char = (pending.char + 1) % content.len();
                self.textbox.replace_last(content[char]);
                char
            }
            _ => {
                // This key is not pending. Append the first character in the key.
                let char = 0;
                self.textbox.append(content[char]);
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
        self.textbox.toggle_pending_marker(self.pending.is_some());

        self.after_edit();
    }

    fn on_timeout(&mut self) {
        self.pending.take();
    }

    fn key_content(&self, page: usize, key: usize) -> &'static [u8] {
        match self.key_btns[page][key].content() {
            ButtonContent::Text(text) => text,
            ButtonContent::Image(_) => " ".as_bytes(),
        }
    }

    fn after_edit(&mut self) {
        if self.textbox.is_empty() {
            self.back_btn.disable();
        } else {
            self.back_btn.enable();
        }
    }
}

impl Component for PassphraseKeyboard {
    type Msg = PassphraseKeyboardMsg;

    fn widget(&mut self) -> &mut Widget {
        &mut self.widget
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        match (event, &self.pending) {
            (Event::Timer(timer), Some(pending)) if pending.timer == timer => {
                // Our pending timer triggered, reset the pending state.
                self.on_timeout();
                return None;
            }
            _ => {}
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
            if self.textbox.is_empty() {
                return Some(PassphraseKeyboardMsg::Cancelled);
            } else {
                self.on_backspace_click();
                return None;
            }
        }
        let mut clicked_key = None;
        for (i, btn) in self.key_btns[self.key_page].iter_mut().enumerate() {
            if let Some(Clicked) = btn.event(ctx, event) {
                clicked_key.replace(i);
                break;
            }
        }
        if let Some(key) = clicked_key {
            // Key button was clicked. If this button is pending, let's cycle the pending
            // character in textbox. If not, let's just append the first character.
            self.on_key_click(ctx, key);
            return None;
        }
        None
    }

    fn paint(&mut self) {
        self.textbox.paint_if_requested();
        self.confirm_btn.paint_if_requested();
        self.back_btn.paint_if_requested();
        for btn in &mut self.key_btns[self.key_page] {
            btn.paint_if_requested();
        }
    }
}

struct TextBox {
    widget: Widget,
    text: StaticVec<u8, MAX_LENGTH>,
    pending: bool,
}

impl TextBox {
    fn new(area: Rect, text: StaticVec<u8, MAX_LENGTH>) -> Self {
        Self {
            widget: Widget::new(area),
            text,
            pending: false,
        }
    }

    fn toggle_pending_marker(&mut self, pending: bool) {
        self.pending = pending;
    }

    fn is_empty(&self) -> bool {
        self.text.is_empty()
    }

    fn delete_last(&mut self) {
        self.text.pop();
    }

    fn replace_last(&mut self, char: u8) {
        self.text.pop();
        self.text.push(char);
    }

    fn append(&mut self, char: u8) {
        self.text.push(char);
    }
}

impl Component for TextBox {
    type Msg = !;

    fn widget(&mut self) -> &mut Widget {
        &mut self.widget
    }

    fn event(&mut self, _ctx: &mut EventCtx, _event: Event) -> Option<Self::Msg> {
        None
    }

    fn paint(&mut self) {
        let style = theme::label_default();

        display::text(
            self.area().top_left(),
            &self.text,
            style.font,
            style.text_color,
            style.background_color,
        );
    }
}
