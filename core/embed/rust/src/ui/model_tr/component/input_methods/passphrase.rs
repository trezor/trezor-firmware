use crate::ui::{
    component::{text::common::TextBox, Child, Component, ComponentExt, Event, EventCtx},
    display::Icon,
    geometry::Rect,
    model_tr::theme,
    util::char_to_string,
};

use super::super::{
    ButtonDetails, ButtonLayout, ChangingTextLine, ChoiceFactory, ChoiceItem, ChoicePage,
    ChoicePageMsg,
};
use heapless::String;

pub enum PassphraseEntryMsg {
    Confirmed,
    Cancelled,
}

/// Defines the choices currently available on the screen
#[derive(PartialEq, Clone)]
enum ChoiceCategory {
    Menu,
    LowercaseLetter,
    UppercaseLetter,
    Digit,
    SpecialSymbol,
}

const MAX_PASSPHRASE_LENGTH: usize = 50;

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
const DELETE_INDEX: usize = MENU_LENGTH - 1;
const SHOW_INDEX: usize = MENU_LENGTH - 2;
const MENU: [&str; MENU_LENGTH] = ["abc", "ABC", "123", "*#_", "SHOW", "DELETE"];

/// Get a character at a specified index for a specified category.
fn get_char(current_category: &ChoiceCategory, index: u8) -> char {
    let index = index as usize;
    match current_category {
        ChoiceCategory::LowercaseLetter => LOWERCASE_LETTERS[index],
        ChoiceCategory::UppercaseLetter => UPPERCASE_LETTERS[index],
        ChoiceCategory::Digit => DIGITS[index],
        ChoiceCategory::SpecialSymbol => SPECIAL_SYMBOLS[index],
        ChoiceCategory::Menu => unreachable!(),
    }
}

/// Return category from menu based on page index.
fn get_category_from_menu(page_index: u8) -> ChoiceCategory {
    match page_index {
        0 => ChoiceCategory::LowercaseLetter,
        1 => ChoiceCategory::UppercaseLetter,
        2 => ChoiceCategory::Digit,
        3 => ChoiceCategory::SpecialSymbol,
        _ => unreachable!(),
    }
}

/// How many choices are available for a specified category.
/// (does not count the extra MENU choice for characters)
fn get_category_length(current_category: &ChoiceCategory) -> u8 {
    match current_category {
        ChoiceCategory::LowercaseLetter => LOWERCASE_LETTERS.len() as u8,
        ChoiceCategory::UppercaseLetter => UPPERCASE_LETTERS.len() as u8,
        ChoiceCategory::Digit => DIGITS.len() as u8,
        ChoiceCategory::SpecialSymbol => SPECIAL_SYMBOLS.len() as u8,
        ChoiceCategory::Menu => MENU.len() as u8,
    }
}

/// Whether this index is the MENU index - the last one in the list.
fn is_menu_choice(current_category: &ChoiceCategory, page_index: u8) -> bool {
    if let ChoiceCategory::Menu = current_category {
        unreachable!()
    }
    let category_length = get_category_length(current_category);
    page_index == category_length
}

struct ChoiceFactoryPassphrase {
    current_category: ChoiceCategory,
}

impl ChoiceFactoryPassphrase {
    fn new(current_category: ChoiceCategory) -> Self {
        Self { current_category }
    }

    /// MENU choices with accept and cancel hold-to-confirm side buttons.
    fn get_menu_item(&self, choice_index: u8) -> ChoiceItem {
        let choice = MENU[choice_index as usize];
        let mut menu_item = ChoiceItem::new(
            String::<50>::from(choice),
            ButtonLayout::default_three_icons(),
        );

        // Including accept button on the left and cancel on the very right.
        // TODO: could have some icons instead of the shortcut text
        if choice_index == 0 {
            menu_item.set_left_btn(Some(
                ButtonDetails::text("ACC".into()).with_default_duration(),
            ));
        }
        if choice_index == MENU.len() as u8 - 1 {
            menu_item.set_right_btn(Some(
                ButtonDetails::text("CAN".into()).with_default_duration(),
            ));
        }

        // Including icons for some items.
        if choice_index == DELETE_INDEX as u8 {
            menu_item = menu_item.with_icon(Icon::new(theme::ICON_DELETE));
        } else if choice_index == SHOW_INDEX as u8 {
            menu_item = menu_item.with_icon(Icon::new(theme::ICON_EYE));
        }

        menu_item
    }

    /// Character choices with a MENU choice at the end (visible from start) to
    /// return back
    fn get_character_item(&self, choice_index: u8) -> ChoiceItem {
        if is_menu_choice(&self.current_category, choice_index) {
            ChoiceItem::new(
                "MENU",
                ButtonLayout::three_icons_middle_text("RETURN".into()),
            )
        } else {
            let ch = get_char(&self.current_category, choice_index);
            ChoiceItem::new(char_to_string::<1>(ch), ButtonLayout::default_three_icons())
        }
    }
}

impl ChoiceFactory for ChoiceFactoryPassphrase {
    type Item = ChoiceItem;
    fn count(&self) -> u8 {
        let length = get_category_length(&self.current_category);
        // All non-MENU categories have an extra item for returning back to MENU
        match self.current_category {
            ChoiceCategory::Menu => length,
            _ => length + 1,
        }
    }
    fn get(&self, choice_index: u8) -> ChoiceItem {
        match self.current_category {
            ChoiceCategory::Menu => self.get_menu_item(choice_index),
            _ => self.get_character_item(choice_index),
        }
    }
}

/// Component for entering a passphrase.
pub struct PassphraseEntry {
    choice_page: ChoicePage<ChoiceFactoryPassphrase>,
    passphrase_dots: Child<ChangingTextLine<String<MAX_PASSPHRASE_LENGTH>>>,
    show_plain_passphrase: bool,
    textbox: TextBox<MAX_PASSPHRASE_LENGTH>,
    current_category: ChoiceCategory,
    menu_position: u8, // position in the menu so we can return back
}

impl PassphraseEntry {
    pub fn new() -> Self {
        let menu_choices = ChoiceFactoryPassphrase::new(ChoiceCategory::Menu);
        Self {
            choice_page: ChoicePage::new(menu_choices),
            passphrase_dots: Child::new(ChangingTextLine::center_mono(String::new())),
            show_plain_passphrase: false,
            textbox: TextBox::empty(),
            current_category: ChoiceCategory::Menu,
            menu_position: 0,
        }
    }

    fn update_passphrase_dots(&mut self, ctx: &mut EventCtx) {
        // TODO: when the passphrase is longer than fits the screen, we might show
        // ellipsis
        if self.show_plain_passphrase {
            let passphrase = String::from(self.passphrase());
            self.passphrase_dots.inner_mut().update_text(passphrase);
        } else {
            let mut dots: String<MAX_PASSPHRASE_LENGTH> = String::new();
            for _ in 0..self.textbox.len() {
                unwrap!(dots.push_str("*"));
            }
            self.passphrase_dots.inner_mut().update_text(dots);
        }
        self.passphrase_dots.request_complete_repaint(ctx);
    }

    fn append_char(&mut self, ctx: &mut EventCtx, ch: char) {
        self.textbox.append(ctx, ch);
    }

    fn delete_last_digit(&mut self, ctx: &mut EventCtx) {
        self.textbox.delete_last(ctx);
    }

    /// Displaying the MENU
    fn show_menu_page(&mut self, ctx: &mut EventCtx) {
        let menu_choices = ChoiceFactoryPassphrase::new(ChoiceCategory::Menu);
        self.choice_page.reset(ctx, menu_choices, true, false);
        // Going back to the last MENU position before showing the MENU
        self.choice_page.set_page_counter(ctx, self.menu_position);
    }

    /// Displaying the character category
    fn show_category_page(&mut self, ctx: &mut EventCtx) {
        let category_choices = ChoiceFactoryPassphrase::new(self.current_category.clone());
        self.choice_page.reset(ctx, category_choices, true, true);
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
        let passphrase_area_height = self.passphrase_dots.inner().needed_height();
        let (passphrase_area, choice_area) = bounds.split_top(passphrase_area_height);
        self.passphrase_dots.place(passphrase_area);
        self.choice_page.place(choice_area);
        bounds
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        // Any event when showing real passphrase should hide it
        if self.show_plain_passphrase {
            self.show_plain_passphrase = false;
            self.update_passphrase_dots(ctx);
        }

        let msg = self.choice_page.event(ctx, event);

        if self.current_category == ChoiceCategory::Menu {
            match msg {
                // Going to new category, applying some action or returning the result
                Some(ChoicePageMsg::Choice(page_counter)) => match page_counter as usize {
                    DELETE_INDEX => {
                        self.delete_last_digit(ctx);
                        self.update_passphrase_dots(ctx);
                        ctx.request_paint();
                    }
                    SHOW_INDEX => {
                        self.show_plain_passphrase = true;
                        self.update_passphrase_dots(ctx);
                        ctx.request_paint();
                    }
                    _ => {
                        self.menu_position = page_counter;
                        self.current_category = get_category_from_menu(page_counter);
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
                if is_menu_choice(&self.current_category, page_counter) {
                    self.current_category = ChoiceCategory::Menu;
                    self.show_menu_page(ctx);
                    ctx.request_paint();
                } else if !self.is_full() {
                    let new_char = get_char(&self.current_category, page_counter);
                    self.append_char(ctx, new_char);
                    self.update_passphrase_dots(ctx);
                    ctx.request_paint();
                }
            }
        }

        None
    }

    fn paint(&mut self) {
        self.passphrase_dots.paint();
        self.choice_page.paint();
    }
}

#[cfg(feature = "ui_debug")]
use super::super::{ButtonAction, ButtonPos};
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
                        DELETE_INDEX => ButtonAction::Action("Del last char").string(),
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
