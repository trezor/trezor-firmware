use crate::{
    strutil::{ShortString, TString},
    translations::TR,
    trezorhal::random,
    ui::{
        component::{text::common::TextBox, Child, Component, ComponentExt, Event, EventCtx},
        display::Icon,
        geometry::Rect,
        shape::Renderer,
        util::char_to_string,
    },
};

use super::super::{
    theme, ButtonDetails, ButtonLayout, CancelConfirmMsg, ChangingTextLine, ChoiceFactory,
    ChoiceItem, ChoicePage,
};

/// Defines the choices currently available on the screen
#[derive(PartialEq, Clone, Copy)]
enum ChoiceCategory {
    Menu,
    LowercaseLetter,
    UppercaseLetter,
    Digit,
    SpecialSymbol,
}

const MAX_PASSPHRASE_LENGTH: usize = 50;

const DIGITS: &str = "0123456789";
const LOWERCASE_LETTERS: &str = "abcdefghijklmnopqrstuvwxyz";
const UPPERCASE_LETTERS: &str = "ABCDEFGHIJKLMNOPQRSTUVWXYZ";
const SPECIAL_SYMBOLS: &str = "_<>.:@/|\\!()+%&-[]?{},\'`;\"~$^=*#";

const MENU_LENGTH: usize = 8;
const SHOW_INDEX: usize = 0;
const CANCEL_DELETE_INDEX: usize = 1;
const ENTER_INDEX: usize = 2;
const LOWERCASE_INDEX: usize = 3;
const UPPERCASE_INDEX: usize = 4;
const DIGITS_INDEX: usize = 5;
const SPECIAL_INDEX: usize = 6;
const SPACE_INDEX: usize = 7;

#[derive(Clone)]
struct MenuItem {
    text: TString<'static>,
    action: PassphraseAction,
    icon: Option<Icon>,
    show_confirm: bool,
    without_release: bool,
}

const MENU: [MenuItem; MENU_LENGTH] = [
    MenuItem {
        text: TR::inputs__show.as_tstring(),
        action: PassphraseAction::Show,
        icon: Some(theme::ICON_EYE),
        show_confirm: true,
        without_release: false,
    },
    MenuItem {
        text: TString::from_str("CANCEL OR DELETE"),
        action: PassphraseAction::CancelOrDelete,
        icon: None,
        show_confirm: true,
        without_release: true,
    },
    MenuItem {
        text: TR::inputs__enter.as_tstring(),
        action: PassphraseAction::Enter,
        icon: Some(theme::ICON_TICK),
        show_confirm: true,
        without_release: false,
    },
    MenuItem {
        text: TString::from_str("abc"),
        action: PassphraseAction::Category(ChoiceCategory::LowercaseLetter),
        icon: None,
        show_confirm: false,
        without_release: false,
    },
    MenuItem {
        text: TString::from_str("ABC"),
        action: PassphraseAction::Category(ChoiceCategory::UppercaseLetter),
        icon: None,
        show_confirm: false,
        without_release: false,
    },
    MenuItem {
        text: TString::from_str("123"),
        action: PassphraseAction::Category(ChoiceCategory::Digit),
        icon: None,
        show_confirm: false,
        without_release: false,
    },
    MenuItem {
        text: TString::from_str("#$!"),
        action: PassphraseAction::Category(ChoiceCategory::SpecialSymbol),
        icon: None,
        show_confirm: false,
        without_release: false,
    },
    MenuItem {
        text: TR::inputs__space.as_tstring(),
        action: PassphraseAction::Character(' '),
        icon: Some(theme::ICON_SPACE),
        show_confirm: false,
        without_release: false,
    },
];

#[derive(Clone, Copy)]
enum PassphraseAction {
    Menu,
    Show,
    CancelOrDelete,
    Enter,
    Category(ChoiceCategory),
    Character(char),
}

/// Get a character at a specified index for a specified category.
fn get_char(current_category: &ChoiceCategory, index: usize) -> char {
    let group = match current_category {
        ChoiceCategory::LowercaseLetter => LOWERCASE_LETTERS,
        ChoiceCategory::UppercaseLetter => UPPERCASE_LETTERS,
        ChoiceCategory::Digit => DIGITS,
        ChoiceCategory::SpecialSymbol => SPECIAL_SYMBOLS,
        ChoiceCategory::Menu => unreachable!(),
    };
    unwrap!(group.chars().nth(index))
}

/// How many choices are available for a specified category.
/// (does not count the extra MENU choice for characters)
fn get_category_length(current_category: &ChoiceCategory) -> usize {
    match current_category {
        ChoiceCategory::LowercaseLetter => LOWERCASE_LETTERS.len(),
        ChoiceCategory::UppercaseLetter => UPPERCASE_LETTERS.len(),
        ChoiceCategory::Digit => DIGITS.len(),
        ChoiceCategory::SpecialSymbol => SPECIAL_SYMBOLS.len(),
        ChoiceCategory::Menu => MENU.len(),
    }
}

/// Random position/index in the given category
fn random_category_position(category: &ChoiceCategory) -> usize {
    let category_length = get_category_length(category) as u32;
    random::uniform_between(0, category_length - 1) as usize
}

/// Whether this index is the MENU index - the last one in the list.
fn is_menu_choice(current_category: &ChoiceCategory, page_index: usize) -> bool {
    if let ChoiceCategory::Menu = current_category {
        unreachable!()
    }
    let category_length = get_category_length(current_category);
    page_index == category_length
}

/// Choose random character category to be pre-selected
fn random_menu_position() -> usize {
    random::uniform_between(LOWERCASE_INDEX as u32, SPECIAL_INDEX as u32) as usize
}

struct ChoiceFactoryPassphrase {
    current_category: ChoiceCategory,
    /// Used to either show DELETE or CANCEL
    is_empty: bool,
}

impl ChoiceFactoryPassphrase {
    fn new(current_category: ChoiceCategory, is_empty: bool) -> Self {
        Self {
            current_category,
            is_empty,
        }
    }

    /// MENU choices with accept and cancel hold-to-confirm side buttons.
    fn get_menu_item(&self, choice_index: usize) -> (ChoiceItem, PassphraseAction) {
        #[allow(const_item_mutation)]
        let current_item = &mut MENU[choice_index];
        // More options for CANCEL/DELETE button
        if matches!(current_item.action, PassphraseAction::CancelOrDelete) {
            if self.is_empty {
                current_item.text = TR::inputs__cancel.into();
                current_item.icon = Some(theme::ICON_CANCEL);
            } else {
                current_item.text = TR::inputs__delete.into();
                current_item.icon = Some(theme::ICON_DELETE);
            }
        }

        let mut menu_item = current_item.text.map(|t| {
            ChoiceItem::new(
                t,
                ButtonLayout::arrow_armed_arrow(TR::buttons__select.into()),
            )
        });

        // Action buttons have different middle button text
        if current_item.show_confirm {
            let confirm_btn = ButtonDetails::armed_text(TR::buttons__confirm.into());
            menu_item.set_middle_btn(Some(confirm_btn));
        }

        // Making middle button create LongPress events
        if current_item.without_release {
            menu_item = menu_item.with_middle_action_without_release();
        }

        if let Some(icon) = current_item.icon {
            menu_item = menu_item.with_icon(icon);
        }
        (menu_item, current_item.action)
    }

    /// Character choices with a BACK to MENU choice at the end (visible from
    /// start) to return back
    fn get_character_item(&self, choice_index: usize) -> (ChoiceItem, PassphraseAction) {
        if is_menu_choice(&self.current_category, choice_index) {
            (
                TR::inputs__back.map_translated(|t| {
                    ChoiceItem::new(
                        t,
                        ButtonLayout::arrow_armed_arrow(TR::inputs__return.into()),
                    )
                    .with_icon(theme::ICON_ARROW_BACK_UP)
                }),
                PassphraseAction::Menu,
            )
        } else {
            let ch = get_char(&self.current_category, choice_index);
            (
                ChoiceItem::new(
                    char_to_string(ch),
                    ButtonLayout::arrow_armed_arrow(TR::buttons__select.into()),
                ),
                PassphraseAction::Character(ch),
            )
        }
    }
}

impl ChoiceFactory for ChoiceFactoryPassphrase {
    type Action = PassphraseAction;
    type Item = ChoiceItem;

    fn count(&self) -> usize {
        let length = get_category_length(&self.current_category);
        // All non-MENU categories have an extra item for returning back to MENU
        match self.current_category {
            ChoiceCategory::Menu => length,
            _ => length + 1,
        }
    }
    fn get(&self, choice_index: usize) -> (Self::Item, Self::Action) {
        match self.current_category {
            ChoiceCategory::Menu => self.get_menu_item(choice_index),
            _ => self.get_character_item(choice_index),
        }
    }
}

/// Component for entering a passphrase.
pub struct PassphraseEntry {
    choice_page: ChoicePage<ChoiceFactoryPassphrase, PassphraseAction>,
    passphrase_dots: Child<ChangingTextLine>,
    show_plain_passphrase: bool,
    show_last_digit: bool,
    textbox: TextBox,
    current_category: ChoiceCategory,
}

impl PassphraseEntry {
    pub fn new() -> Self {
        Self {
            choice_page: ChoicePage::new(ChoiceFactoryPassphrase::new(ChoiceCategory::Menu, true))
                .with_carousel(true)
                .with_initial_page_counter(random_menu_position()),
            passphrase_dots: Child::new(ChangingTextLine::center_mono("", MAX_PASSPHRASE_LENGTH)),
            show_plain_passphrase: false,
            show_last_digit: false,
            textbox: TextBox::empty(MAX_PASSPHRASE_LENGTH),
            current_category: ChoiceCategory::Menu,
        }
    }

    fn update_passphrase_dots(&mut self, ctx: &mut EventCtx) {
        debug_assert!({
            let s = ShortString::new();
            s.capacity() >= MAX_PASSPHRASE_LENGTH
        });

        let text_to_show = if self.show_plain_passphrase {
            unwrap!(ShortString::try_from(self.passphrase()))
        } else if self.is_empty() {
            unwrap!(ShortString::try_from(""))
        } else {
            // Showing asterisks and possibly the last digit.
            let mut dots = ShortString::new();
            for _ in 0..self.textbox.len() - 1 {
                unwrap!(dots.push('*'));
            }
            let last_char = if self.show_last_digit {
                unwrap!(self.textbox.content().chars().last())
            } else {
                '*'
            };
            unwrap!(dots.push(last_char));
            dots
        };
        self.passphrase_dots.mutate(ctx, |ctx, passphrase_dots| {
            passphrase_dots.update_text(&text_to_show);
            passphrase_dots.request_complete_repaint(ctx);
        });
    }

    fn append_char(&mut self, ctx: &mut EventCtx, ch: char) {
        self.textbox.append(ctx, ch);
    }

    fn delete_last_digit(&mut self, ctx: &mut EventCtx) {
        self.textbox.delete_last(ctx);
    }

    fn delete_all_digits(&mut self, ctx: &mut EventCtx) {
        self.textbox.clear(ctx);
    }

    /// Displaying the MENU
    fn show_menu_page(&mut self, ctx: &mut EventCtx) {
        let menu_choices = ChoiceFactoryPassphrase::new(ChoiceCategory::Menu, self.is_empty());
        self.choice_page
            .reset(ctx, menu_choices, Some(random_menu_position()), true);
    }

    /// Displaying the character category
    fn show_category_page(&mut self, ctx: &mut EventCtx) {
        let category_choices = ChoiceFactoryPassphrase::new(self.current_category, self.is_empty());
        self.choice_page.reset(
            ctx,
            category_choices,
            Some(random_category_position(&self.current_category)),
            true,
        );
    }

    pub fn passphrase(&self) -> &str {
        self.textbox.content()
    }

    fn is_empty(&self) -> bool {
        self.textbox.is_empty()
    }

    fn is_full(&self) -> bool {
        self.textbox.len() >= MAX_PASSPHRASE_LENGTH
    }

    /// Randomly choose an index in the current category
    fn randomize_category_position(&mut self, ctx: &mut EventCtx) {
        self.choice_page.set_page_counter(
            ctx,
            random_category_position(&self.current_category),
            true,
        );
    }
}

impl Component for PassphraseEntry {
    type Msg = CancelConfirmMsg;

    fn place(&mut self, bounds: Rect) -> Rect {
        let passphrase_area_height = self.passphrase_dots.inner().needed_height();
        let (passphrase_area, choice_area) = bounds.split_top(passphrase_area_height);
        self.passphrase_dots.place(passphrase_area);
        self.choice_page.place(choice_area);
        bounds
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        // Any non-timer event when showing real passphrase should hide it
        // Same with showing last digit
        if !matches!(event, Event::Timer(_)) {
            if self.show_plain_passphrase {
                self.show_plain_passphrase = false;
                self.update_passphrase_dots(ctx);
            }
            if self.show_last_digit {
                self.show_last_digit = false;
                self.update_passphrase_dots(ctx);
            }
        }

        if let Some((action, long_press)) = self.choice_page.event(ctx, event) {
            match action {
                PassphraseAction::CancelOrDelete => {
                    if self.is_empty() {
                        return Some(CancelConfirmMsg::Cancelled);
                    } else {
                        // Deleting all when long-pressed
                        if long_press {
                            self.delete_all_digits(ctx);
                        } else {
                            self.delete_last_digit(ctx);
                        }
                        self.update_passphrase_dots(ctx);
                        if self.is_empty() {
                            // Allowing for DELETE/CANCEL change
                            self.show_menu_page(ctx);
                        }
                        ctx.request_paint();
                    }
                }
                PassphraseAction::Enter => {
                    return Some(CancelConfirmMsg::Confirmed);
                }
                PassphraseAction::Show => {
                    self.show_plain_passphrase = true;
                    self.update_passphrase_dots(ctx);
                    ctx.request_paint();
                }
                PassphraseAction::Category(category) => {
                    self.current_category = category;
                    self.show_category_page(ctx);
                    ctx.request_paint();
                }
                PassphraseAction::Menu => {
                    self.current_category = ChoiceCategory::Menu;
                    self.show_menu_page(ctx);
                    ctx.request_paint();
                }
                PassphraseAction::Character(ch) if !self.is_full() => {
                    self.append_char(ctx, ch);
                    self.show_last_digit = true;
                    self.update_passphrase_dots(ctx);
                    self.randomize_category_position(ctx);
                    ctx.request_paint();
                }
                _ => {}
            }
        }

        None
    }

    fn render<'s>(&'s self, target: &mut impl Renderer<'s>) {
        self.passphrase_dots.render(target);
        self.choice_page.render(target);
    }
}

// DEBUG-ONLY SECTION BELOW

#[cfg(feature = "ui_debug")]
impl crate::trace::Trace for PassphraseEntry {
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.component("PassphraseKeyboard");
        t.string("passphrase", self.textbox.content().into());
        t.string(
            "current_category",
            match self.current_category {
                ChoiceCategory::Menu => "MENU".into(),
                ChoiceCategory::LowercaseLetter => MENU[LOWERCASE_INDEX].text,
                ChoiceCategory::UppercaseLetter => MENU[UPPERCASE_INDEX].text,
                ChoiceCategory::Digit => MENU[DIGITS_INDEX].text,
                ChoiceCategory::SpecialSymbol => MENU[SPECIAL_INDEX].text,
            },
        );
        t.child("choice_page", &self.choice_page);
    }
}
