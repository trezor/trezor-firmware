use crate::{
    time::Duration,
    ui::{
        component::{text::common::TextBox, Component, Event, EventCtx},
        geometry::Rect,
    },
};

use super::{
    choice_item::BigCharacterChoiceItem,
    common::{display_dots_center_top, display_secret_center_top},
    ButtonDetails, ButtonLayout, ChoiceItems, ChoicePage, ChoicePageMsg, MultilineTextChoiceItem,
    TextChoiceItem,
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

const PIN_ROW_DOTS: i32 = 8;
const PIN_ROW_DIGITS: i32 = 10;

const MAX_LENGTH: usize = 50;
const HOLD_DURATION: Duration = Duration::from_secs(1);

const MAX_CHOICE_LENGTH: usize = 30 + 1; // accounting for MENU choice as well

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
const MENU: [&str; MENU_LENGTH] = ["abc", "ABC", "123", "*#_", "SHOW PASS", "DEL LAST CHAR"];

/// Component for entering a passphrase.
pub struct PassphraseEntry {
    choice_page: ChoicePage<MAX_CHOICE_LENGTH>,
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
        display_dots_center_top(self.textbox.len(), 21);
    }

    fn reveal_current_passphrase(&self) {
        display_secret_center_top(self.passphrase(), 21);
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
            _ => {
                panic!("Not a category index")
            }
        }
    }

    fn get_char(&self, index: usize) -> char {
        match self.current_category {
            ChoiceCategory::LowercaseLetter => LOWERCASE_LETTERS[index],
            ChoiceCategory::UppercaseLetter => UPPERCASE_LETTERS[index],
            ChoiceCategory::Digit => DIGITS[index],
            ChoiceCategory::SpecialSymbol => SPECIAL_SYMBOLS[index],
            ChoiceCategory::Menu => {
                panic!("Menu does not have characters")
            }
        }
    }

    /// MENU choices with accept and cancel hold-to-confirm side buttons.
    fn get_menu_choices() -> Vec<ChoiceItems, MAX_CHOICE_LENGTH> {
        let mut choices: Vec<ChoiceItems, MAX_CHOICE_LENGTH> = MENU
            .iter()
            .map(|menu_item| {
                let item = MultilineTextChoiceItem::new(
                    String::from(*menu_item),
                    ButtonLayout::default_three_icons(),
                )
                .use_delimiter(' ');
                ChoiceItems::MultilineText(item)
            })
            .collect();
        // Including accept button on the left and cancel on the very right
        let last_index = choices.len() - 1;
        choices[0].set_left_btn(Some(
            ButtonDetails::text("ACC").with_duration(HOLD_DURATION),
        ));
        choices[last_index].set_right_btn(Some(
            ButtonDetails::text("CNC").with_duration(HOLD_DURATION),
        ));

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
            ChoiceCategory::Menu => {
                panic!("Not callable from menu")
            }
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
            ChoiceCategory::Menu => {
                panic!("Menu does not have characters")
            }
        };

        let mut choices: Vec<ChoiceItems, MAX_CHOICE_LENGTH> = new_characters
            .iter()
            .map(|ch| {
                let choice = BigCharacterChoiceItem::new(**ch, ButtonLayout::default_three_icons());
                ChoiceItems::BigCharacter(choice)
            })
            .collect();

        // Including a MENU choice at the end (visible from start) to return back
        let menu_choice =
            TextChoiceItem::new("MENU", ButtonLayout::three_icons_middle_text("RETURN"));
        choices.push(ChoiceItems::Text(menu_choice)).unwrap();

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
use super::{ButtonAction, ButtonPos};
#[cfg(feature = "ui_debug")]
use crate::ui::util;

#[cfg(feature = "ui_debug")]
impl crate::trace::Trace for PassphraseEntry {
    fn get_btn_action(&self, pos: ButtonPos) -> String<25> {
        match pos {
            ButtonPos::Left => match self.current_category {
                ChoiceCategory::Menu => match self.choice_page.has_previous_choice() {
                    true => ButtonAction::PrevPage.string(),
                    false => ButtonAction::Confirm.string(),
                },
                _ => ButtonAction::PrevPage.string(),
            },
            ButtonPos::Right => match self.current_category {
                ChoiceCategory::Menu => match self.choice_page.has_next_choice() {
                    true => ButtonAction::NextPage.string(),
                    false => ButtonAction::Cancel.string(),
                },
                _ => ButtonAction::NextPage.string(),
            },
            ButtonPos::Middle => {
                let current_index = self.choice_page.page_index() as usize;
                match &self.current_category {
                    ChoiceCategory::Menu => match current_index {
                        DEL_INDEX => ButtonAction::Action("Del last char").string(),
                        SHOW_INDEX => ButtonAction::Action("Show pass").string(),
                        _ => ButtonAction::select_item(MENU[current_index]),
                    },
                    _ => {
                        // There is "MENU" option at the end
                        match self.choice_page.has_next_choice() {
                            false => ButtonAction::Action("Back to MENU").string(),
                            true => {
                                let ch = match &self.current_category {
                                    ChoiceCategory::LowercaseLetter => {
                                        LOWERCASE_LETTERS[current_index]
                                    }
                                    ChoiceCategory::UppercaseLetter => {
                                        UPPERCASE_LETTERS[current_index]
                                    }
                                    ChoiceCategory::Digit => DIGITS[current_index],
                                    ChoiceCategory::SpecialSymbol => SPECIAL_SYMBOLS[current_index],
                                    ChoiceCategory::Menu => unreachable!(),
                                };
                                ButtonAction::select_item(util::char_to_string::<1>(ch))
                            }
                        }
                    }
                }
            }
        }
    }

    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.open("PassphraseEntry");
        // NOTE: `show_plain_passphrase` was not able to be transferred,
        // as it is true only for a very small amount of time
        t.kw_pair("textbox", self.textbox.content());
        self.report_btn_actions(t);
        t.field("choice_page", &self.choice_page);
        t.close();
    }
}
