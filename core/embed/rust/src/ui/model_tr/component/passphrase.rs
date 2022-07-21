use crate::{
    time::Duration,
    ui::{
        component::{text::common::TextBox, Component, Event, EventCtx},
        geometry::{Point, Rect},
        util,
    },
};

use super::{
    common::{display_bold_center, ButtonDetails, ButtonLayout, MultilineStringChoiceItem},
    ChoicePage, ChoicePageMsg,
};
use heapless::{String, Vec};

pub enum PassphraseEntryMsg {
    Confirmed,
    Cancelled,
}

/// Defines the choices currently available on the screen
#[derive(PartialEq)]
enum ChoiceCategory {
    Menu,
    LowercaseLetter,
    UppercaseLetter,
    Digit,
    SpecialSymbol,
}

const PASSPHRASE_ROW: i32 = 40;

const MAX_LENGTH: usize = 50;
const MAX_VISIBLE_CHARS: usize = 18;
const HOLD_DURATION: Duration = Duration::from_secs(1);

const MAX_CHOICE_LENGTH: usize = 31; // accounting for MENU choice as well

const DIGITS: [char; 10] = ['0', '1', '2', '3', '4', '5', '6', '7', '8', '9'];
const LOWERCASE_LETTERS: [char; 26] = [
    'a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm', 'n', 'o', 'p', 'q', 'r', 's',
    't', 'u', 'v', 'w', 'x', 'y', 'z',
];
const UPPERCASE_LETTERS: [char; 26] = [
    'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S',
    'T', 'U', 'V', 'W', 'X', 'Y', 'Z',
];
const SPECIAL_SYMBOLS: [char; 30] = [
    '_', '<', '>', '.', ':', '@', '/', '|', '\\', '!', '(', ')', '+', '%', '&', '-', '[', ']', '?',
    '{', '}', ',', '\'', '`', ';', '"', '~', '$', '^', '=',
];
const MENU_LENGTH: usize = 6;
const DEL_INDEX: usize = MENU_LENGTH - 1;
const SHOW_INDEX: usize = MENU_LENGTH - 2;
const MENU: [&str; MENU_LENGTH] = ["abc", "ABC", "123", "*#_", "SHOW\nPASS", "DEL\nLAST\nCHAR"];

/// Component for entering a passphrase.
pub struct PassphraseEntry {
    // TODO: how to make ChoicePage accept both
    // StringChoiceItem and MultilineStringChoiceItem?
    choice_page: ChoicePage<MultilineStringChoiceItem, MAX_CHOICE_LENGTH>,
    show_plain_passphrase: bool,
    textbox: TextBox<MAX_LENGTH>,
    current_category: ChoiceCategory,
    menu_position: u8, // position in the menu so we can return back
}

impl PassphraseEntry {
    pub fn new() -> Self {
        let menu_choices = Self::get_menu_choices();

        Self {
            choice_page: ChoicePage::new(menu_choices),
            show_plain_passphrase: false,
            textbox: TextBox::empty(),
            current_category: ChoiceCategory::Menu,
            menu_position: 0,
        }
    }

    fn update_situation(&mut self) {
        if self.show_plain_passphrase {
            self.reveal_current_passphrase();
        } else {
            self.show_passphrase_length();
        }
    }

    fn show_passphrase_length(&self) {
        // Only showing the maximum visible length
        let char_amount = self.textbox.len();
        let dots_visible = char_amount.min(MAX_VISIBLE_CHARS);

        // String::repeat() is not available for heapless::String
        let mut dots: String<MAX_LENGTH> = String::new();
        for _ in 0..dots_visible {
            dots.push_str("*").unwrap();
        }

        // Giving some notion of change even for longer-than-visible passphrases
        // - slightly shifting the dots to the left and right after each new digit
        if char_amount > MAX_VISIBLE_CHARS && char_amount % 2 == 0 {
            display_bold_center(Point::new(61, PASSPHRASE_ROW), &dots);
        } else {
            display_bold_center(Point::new(64, PASSPHRASE_ROW), &dots);
        }
    }

    fn reveal_current_passphrase(&self) {
        let char_amount = self.textbox.len();

        if char_amount <= MAX_VISIBLE_CHARS {
            display_bold_center(Point::new(64, PASSPHRASE_ROW), self.passphrase());
        } else {
            // Show the last part with preceding ellipsis to show something is hidden
            let ellipsis = "...";
            let offset: usize = char_amount.saturating_sub(MAX_VISIBLE_CHARS) + ellipsis.len();
            let to_show = build_string!(MAX_VISIBLE_CHARS, ellipsis, &self.passphrase()[offset..]);
            display_bold_center(Point::new(64, PASSPHRASE_ROW), &to_show);
        }
    }

    fn append_char(&mut self, ctx: &mut EventCtx, ch: char) {
        self.textbox.append(ctx, ch);
    }

    fn delete_last_digit(&mut self, ctx: &mut EventCtx) {
        self.textbox.delete_last(ctx);
    }

    fn get_category_from_menu(&mut self, page_counter: u8) -> ChoiceCategory {
        match page_counter {
            0 => ChoiceCategory::LowercaseLetter,
            1 => ChoiceCategory::UppercaseLetter,
            2 => ChoiceCategory::Digit,
            3 => ChoiceCategory::SpecialSymbol,
            _ => panic!("Not a category index"),
        }
    }

    fn get_char(&self, index: usize) -> char {
        match self.current_category {
            ChoiceCategory::LowercaseLetter => LOWERCASE_LETTERS[index],
            ChoiceCategory::UppercaseLetter => UPPERCASE_LETTERS[index],
            ChoiceCategory::Digit => DIGITS[index],
            ChoiceCategory::SpecialSymbol => SPECIAL_SYMBOLS[index],
            ChoiceCategory::Menu => panic!("Menu does not have characters"),
        }
    }

    /// MENU choices with accept and cancel hold-to-confirm side buttons.
    fn get_menu_choices() -> Vec<MultilineStringChoiceItem, MAX_CHOICE_LENGTH> {
        let mut choices: Vec<MultilineStringChoiceItem, MAX_CHOICE_LENGTH> = MENU
            .iter()
            .map(|menu_item| {
                MultilineStringChoiceItem::new(
                    String::from(*menu_item),
                    ButtonLayout::default_three(),
                )
            })
            .collect();
        // Including accept button on the left and cancel on the very right
        let last_index = choices.len() - 1;
        choices[0].btn_layout.btn_left =
            Some(ButtonDetails::new("ACC").with_duration(HOLD_DURATION));
        choices[last_index].btn_layout.btn_right =
            Some(ButtonDetails::new("CNC").with_duration(HOLD_DURATION));

        choices
    }

    /// Displaying the MENU
    fn show_menu_page(&mut self, ctx: &mut EventCtx) {
        let menu_choices = Self::get_menu_choices();
        self.choice_page.reset(ctx, menu_choices, true, false);
        // Going back to the last MENU position before showing the MENU
        self.choice_page.set_page_counter(ctx, self.menu_position);
    }

    /// Whether this index is the MENU index - the last one in the list.
    fn is_menu_choice(&self, page_counter: u8) -> bool {
        let current_length = match self.current_category {
            ChoiceCategory::LowercaseLetter => LOWERCASE_LETTERS.len(),
            ChoiceCategory::UppercaseLetter => UPPERCASE_LETTERS.len(),
            ChoiceCategory::Digit => DIGITS.len(),
            ChoiceCategory::SpecialSymbol => SPECIAL_SYMBOLS.len(),
            ChoiceCategory::Menu => panic!("Not callable from menu"),
        };
        page_counter == current_length as u8
    }

    /// Displaying the character category
    fn show_category_page(&mut self, ctx: &mut EventCtx) {
        let new_characters: Vec<&char, 30> = match self.current_category {
            ChoiceCategory::LowercaseLetter => LOWERCASE_LETTERS.iter().collect(),
            ChoiceCategory::UppercaseLetter => UPPERCASE_LETTERS.iter().collect(),
            ChoiceCategory::Digit => DIGITS.iter().collect(),
            ChoiceCategory::SpecialSymbol => SPECIAL_SYMBOLS.iter().collect(),
            ChoiceCategory::Menu => panic!("Menu does not have characters"),
        };

        let mut choices: Vec<MultilineStringChoiceItem, MAX_CHOICE_LENGTH> = new_characters
            .iter()
            .map(|ch| {
                MultilineStringChoiceItem::new(
                    util::char_to_string(**ch),
                    ButtonLayout::default_three(),
                )
            })
            .collect();

        // Including a MENU choice at the end (visible from start) to return back
        let menu_choice = MultilineStringChoiceItem::new(
            String::from("MENU"),
            ButtonLayout::special_middle("RETURN"),
        );
        choices.push(menu_choice).unwrap();

        self.choice_page.reset(ctx, choices, true, true);
    }

    pub fn passphrase(&self) -> &str {
        self.textbox.content()
    }

    fn is_full(&self) -> bool {
        self.textbox.is_full()
    }
}

impl Component for PassphraseEntry {
    type Msg = PassphraseEntryMsg;

    fn place(&mut self, bounds: Rect) -> Rect {
        self.choice_page.place(bounds)
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        // Any event should hide the shown passphrase if there
        self.show_plain_passphrase = false;

        let msg = self.choice_page.event(ctx, event);

        if self.current_category == ChoiceCategory::Menu {
            match msg {
                // Going to new category, applying some action or returning the result
                Some(ChoicePageMsg::Choice(page_counter)) => match page_counter as usize {
                    DEL_INDEX => {
                        self.delete_last_digit(ctx);
                        ctx.request_paint();
                    }
                    SHOW_INDEX => {
                        self.show_plain_passphrase = true;
                        ctx.request_paint();
                    }
                    _ => {
                        self.menu_position = page_counter;
                        self.current_category = self.get_category_from_menu(page_counter);
                        self.show_category_page(ctx);
                        ctx.request_paint();
                    }
                },
                Some(ChoicePageMsg::LeftMost) => return Some(PassphraseEntryMsg::Confirmed),
                Some(ChoicePageMsg::RightMost) => return Some(PassphraseEntryMsg::Cancelled),
                _ => {}
            }
        } else {
            // Coming back to MENU or adding new character
            if let Some(ChoicePageMsg::Choice(page_counter)) = msg {
                if self.is_menu_choice(page_counter) {
                    self.current_category = ChoiceCategory::Menu;
                    self.show_menu_page(ctx);
                    ctx.request_paint();
                } else if !self.is_full() {
                    let new_letter = self.get_char(page_counter as usize);
                    self.append_char(ctx, new_letter);
                    ctx.request_paint();
                }
            }
        }

        None
    }

    fn paint(&mut self) {
        self.choice_page.paint();
        self.update_situation();
    }
}

#[cfg(feature = "ui_debug")]
impl crate::trace::Trace for PassphraseEntry {
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.open("PassphraseEntry");
        t.close();
    }
}
