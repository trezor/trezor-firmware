use crate::{
    trezorhal::bip39,
    ui::{
        component::{text::common::TextBox, Component, Event, EventCtx},
        geometry::{Point, Rect},
    },
};

use super::{common, common::StringChoiceItem, ChoicePage, ChoicePageMsg};
use heapless::{String, Vec};

pub enum Bip39EntryMsg {
    ResultWord(String<50>),
}

const LETTERS_ROW: i32 = 40;

const MAX_LENGTH: usize = 20;

const MAX_CHOICE_LENGTH: usize = 26;

/// Offer words when there will be fewer of them than this
const OFFER_WORDS_THRESHOLD: usize = 10;

/// Component for entering a BIP39 mnemonic.
pub struct Bip39Entry {
    choice_page: ChoicePage<StringChoiceItem, MAX_CHOICE_LENGTH>,
    letter_choices: Vec<char, MAX_CHOICE_LENGTH>,
    textbox: TextBox<MAX_LENGTH>,
    offer_words: bool,
    words_list: bip39::Wordlist,
}

impl Bip39Entry {
    pub fn new() -> Self {
        let letter_choices: Vec<char, MAX_CHOICE_LENGTH> =
            bip39::get_available_letters("").collect();
        let choices = letter_choices
            .iter()
            .map(|ch| StringChoiceItem::from_char(*ch))
            .collect();
        let mut choice_page = ChoicePage::new(choices);
        choice_page.set_leftmost_button("BIN");

        Self {
            choice_page,
            letter_choices,
            textbox: TextBox::empty(),
            offer_words: false,
            words_list: bip39::Wordlist::all(),
        }
    }

    /// Gets up-to-date choices for letters or words.
    fn get_current_choices(&mut self) -> Vec<StringChoiceItem, MAX_CHOICE_LENGTH> {
        // Narrowing the word list
        self.words_list = self.words_list.filter_prefix(self.textbox.content());

        // Offering words when there is only a few of them
        // Otherwise getting relevant letters
        if self.words_list.len() < OFFER_WORDS_THRESHOLD {
            self.offer_words = true;
            self.words_list
                .iter()
                .map(StringChoiceItem::from_slice)
                .collect()
        } else {
            self.offer_words = false;
            self.letter_choices = bip39::get_available_letters(self.textbox.content()).collect();
            self.letter_choices
                .iter()
                .map(|ch| StringChoiceItem::from_char(*ch))
                .collect()
        }
    }

    fn update_situation(&mut self) {
        self.show_current_letters();
    }

    fn show_current_letters(&self) {
        let to_show = build_string!({ MAX_LENGTH + 1 }, self.textbox.content(), "_");
        common::display_bold_center(Point::new(64, LETTERS_ROW), &to_show);
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
                if self.offer_words {
                    // When we already offer words, return the word at the given index
                    let word = self
                        .words_list
                        .get(page_counter as usize)
                        .unwrap_or_default();
                    Some(Bip39EntryMsg::ResultWord(String::from(word)))
                } else {
                    // Otherwise, appending the new letter and resetting the choice page
                    // with up-to-date choices
                    let new_letter = self.letter_choices[page_counter as usize];
                    self.append_letter(ctx, new_letter);
                    let new_choices = self.get_current_choices();
                    self.choice_page.reset(new_choices, true, false);
                    None
                }
            }
            Some(ChoicePageMsg::LeftMost) => {
                // Deleting last letter, updating wordlist and updating choices
                self.delete_last_letter(ctx);
                self.reset_wordlist();
                let new_choices = self.get_current_choices();
                self.choice_page.reset(new_choices, true, false);
                None
            }
            _ => None,
        }
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
