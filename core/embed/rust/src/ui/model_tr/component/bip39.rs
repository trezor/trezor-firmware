use crate::{
    trezorhal::bip39,
    ui::{
        component::{text::common::TextBox, Component, Event, EventCtx},
        geometry::{Point, Rect},
        model_tr::theme,
    },
};

use super::{
    choice_item::BigCharacterChoiceItem, common::display_center, ButtonDetails, ButtonLayout,
    ChoiceItems, ChoicePage, ChoicePageMsg, TextChoiceItem,
};
use heapless::{String, Vec};

pub enum Bip39EntryMsg {
    ResultWord(String<50>),
}

const CURRENT_LETTERS_ROW: i32 = 25;

const MAX_LENGTH: usize = 20;
const MAX_CHOICE_LENGTH: usize = 26;

/// Offer words when there will be fewer of them than this
const OFFER_WORDS_THRESHOLD: usize = 10;

/// Component for entering a BIP39 mnemonic.
pub struct Bip39Entry {
    choice_page: ChoicePage<MAX_CHOICE_LENGTH>,
    letter_choices: Vec<char, MAX_CHOICE_LENGTH>,
    textbox: TextBox<MAX_LENGTH>,
    offer_words: bool,
    words_list: bip39::Wordlist,
}

impl Bip39Entry {
    pub fn new() -> Self {
        let letter_choices: Vec<char, MAX_CHOICE_LENGTH> =
            bip39::get_available_letters("").collect();

        let choices = Self::get_letter_choice_page_items(&letter_choices);

        Self {
            choice_page: ChoicePage::new(choices),
            letter_choices,
            textbox: TextBox::empty(),
            offer_words: false,
            words_list: bip39::Wordlist::all(),
        }
    }

    /// Letter choice items with BIN leftmost button. Letters are BIG.
    fn get_letter_choice_page_items(
        letter_choices: &Vec<char, MAX_CHOICE_LENGTH>,
    ) -> Vec<ChoiceItems, MAX_CHOICE_LENGTH> {
        let mut choices: Vec<ChoiceItems, MAX_CHOICE_LENGTH> = letter_choices
            .iter()
            .map(|ch| {
                let choice = BigCharacterChoiceItem::new(*ch, ButtonLayout::default_three());
                ChoiceItems::BigCharacter(choice)
            })
            .collect();
        let last_index = choices.len() - 1;
        choices[0].set_left_btn(Some(ButtonDetails::new("BIN")));
        choices[last_index].set_right_btn(None);

        choices
    }

    /// Word choice items with BIN leftmost button.
    fn get_word_choice_page_items(
        words_list: &bip39::Wordlist,
    ) -> Vec<ChoiceItems, MAX_CHOICE_LENGTH> {
        let mut choices: Vec<ChoiceItems, MAX_CHOICE_LENGTH> = words_list
            .iter()
            .map(|word| {
                let choice = TextChoiceItem::from_str(word, ButtonLayout::default_three());
                ChoiceItems::Text(choice)
            })
            .collect();
        let last_index = choices.len() - 1;
        choices[0].set_left_btn(Some(ButtonDetails::new("BIN")));
        choices[last_index].set_right_btn(None);

        choices
    }

    /// Gets up-to-date choices for letters or words.
    fn get_current_choices(&mut self) -> Vec<ChoiceItems, MAX_CHOICE_LENGTH> {
        // Narrowing the word list
        self.words_list = self.words_list.filter_prefix(self.textbox.content());

        // Offering words when there is only a few of them
        // Otherwise getting relevant letters
        if self.words_list.len() < OFFER_WORDS_THRESHOLD {
            self.offer_words = true;

            Self::get_word_choice_page_items(&self.words_list)
        } else {
            self.offer_words = false;
            self.letter_choices = bip39::get_available_letters(self.textbox.content()).collect();

            Self::get_letter_choice_page_items(&self.letter_choices)
        }
    }

    fn update_situation(&mut self) {
        self.show_current_letters();
    }

    fn show_current_letters(&self) {
        let to_show = build_string!({ MAX_LENGTH + 1 }, self.textbox.content(), "_");
        display_center(
            Point::new(64, CURRENT_LETTERS_ROW),
            &to_show,
            theme::FONT_MONO,
        );
    }

    fn append_letter(&mut self, ctx: &mut EventCtx, letter: char) {
        self.textbox.append(ctx, letter);
    }

    fn delete_last_letter(&mut self, ctx: &mut EventCtx) {
        self.textbox.delete_last(ctx);
    }

    fn reset_wordlist(&mut self) {
        self.words_list = bip39::Wordlist::all();
    }
}

impl Component for Bip39Entry {
    type Msg = Bip39EntryMsg;

    fn place(&mut self, bounds: Rect) -> Rect {
        self.choice_page.place(bounds)
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        let msg = self.choice_page.event(ctx, event);
        match msg {
            Some(ChoicePageMsg::Choice(page_counter)) => {
                // Clicked SELECT.
                // When we already offer words, return the word at the given index.
                // Otherwise, appending the new letter and resetting the choice page
                // with up-to-date choices.
                if self.offer_words {
                    let word = self
                        .words_list
                        .get(page_counter as usize)
                        .unwrap_or_default();
                    return Some(Bip39EntryMsg::ResultWord(String::from(word)));
                } else {
                    let new_letter = self.letter_choices[page_counter as usize];
                    self.append_letter(ctx, new_letter);
                    let new_choices = self.get_current_choices();
                    self.choice_page.reset(ctx, new_choices, true, false);
                    ctx.request_paint();
                }
            }
            Some(ChoicePageMsg::LeftMost) => {
                // Clicked BIN. Deleting last letter, updating wordlist and updating choices
                self.delete_last_letter(ctx);
                self.reset_wordlist();
                let new_choices = self.get_current_choices();
                self.choice_page.reset(ctx, new_choices, true, false);
                ctx.request_paint();
            }
            _ => {}
        }

        None
    }

    fn paint(&mut self) {
        self.choice_page.paint();
        self.update_situation();
    }
}

#[cfg(feature = "ui_debug")]
impl crate::trace::Trace for Bip39Entry {
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.open("Bip39Entry");
        t.close();
    }
}
