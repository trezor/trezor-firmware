use staticvec::StaticVec;

use crate::ui::{
    geometry::{Grid, Rect},
    theme,
};

use super::{button::Button, component::Widget, label::Label};

const STARTING_PAGE: usize = 1;
const PAGES: usize = 4;
const KEYS: usize = 10;
const KEYBOARD: [[&str; KEYS]; PAGES] = [
    ["1", "2", "3", "4", "5", "6", "7", "8", "9", "0"],
    [
        " ", "abc", "def", "ghi", "jkl", "mno", "pqrs", "tuv", "wxyz", "*#",
    ],
    [
        " ", "ABC", "DEF", "GHI", "JKL", "MNO", "PQRS", "TUV", "WXYZ", "*#",
    ],
    [
        "_<>", ".:@", "/|\\", "!()", "+%&", "-[]", "?{}", ",'`", ";\"~", "$^=",
    ],
];
const MAX_LENGTH: usize = 50;

pub struct PassphraseKeyboard {
    widget: Widget,
    input: Input,
    back_btn: Button,
    enter_btn: Button,
    key_btns: [[Button; KEYS]; PAGES],
    key_page: usize,
}

impl PassphraseKeyboard {
    fn new(prompt: &'static [u8]) -> Self {
        let grid = Grid::screen(5, 1);
        let input = Input::new(grid.row_col(0, 0), prompt);
        let grid = Grid::screen(5, 3);
        let back_content = "Back".as_bytes();
        let enter_content = "Enter".as_bytes();
        let back_btn = Button::with_text(grid.cell(12), back_content, theme::button_clear());
        let enter_btn = Button::with_text(grid.cell(14), enter_content, theme::button_confirm());
        Self {
            widget: Widget::new(grid.area),
            input,
            back_btn,
            enter_btn,
            key_btns: Self::generate_keyboard(),
            key_page: STARTING_PAGE,
        }
    }

    fn generate_keyboard() -> [[Button; KEYS]; PAGES] {
        [
            Self::generate_key_page(0),
            Self::generate_key_page(1),
            Self::generate_key_page(2),
            Self::generate_key_page(3),
        ]
    }

    fn generate_key_page(page: usize) -> [Button; KEYS] {
        [
            Self::generate_key(page, 0),
            Self::generate_key(page, 1),
            Self::generate_key(page, 2),
            Self::generate_key(page, 3),
            Self::generate_key(page, 4),
            Self::generate_key(page, 5),
            Self::generate_key(page, 6),
            Self::generate_key(page, 7),
            Self::generate_key(page, 8),
            Self::generate_key(page, 9),
        ]
    }

    fn generate_key(page: usize, key: usize) -> Button {
        // Assign the keys in each page to buttons on a 5x3 grid, starting from the
        // second row.
        let grid = Grid::screen(5, 3);
        let area = grid.cell(if key < 9 {
            // The grid has 3 columns, and we skip the first row.
            key + 3
        } else {
            // For the last key (the "0" position) we skip one cell.
            key + 1 + 3
        });
        let text = KEYBOARD[page][key].as_bytes();
        Button::with_text(area, text, theme::button_default())
    }
}

struct Input {
    content: StaticVec<u8, MAX_LENGTH>,

    prompt: Label<'static>,
}

impl Input {
    fn new(area: Rect, prompt: &'static [u8]) -> Self {
        let prompt = Label::centered(prompt, theme::label_default(), area.midpoint());
        Self {
            content: StaticVec::new(),
            prompt,
        }
    }
}
