use crate::{
    trezorhal::bip39,
    ui::{
        component::{text::common::TextBox, Component, Event, EventCtx, Pad},
        geometry::{Point, Rect},
        model_tr::theme,
    },
};

use super::{
    choice_item::BigCharacterChoiceItem, common, ButtonDetails, ButtonLayout, ChoiceItems,
    ChoicePage, ChoicePageMsg, TextChoiceItem,
};
use heapless::{String, Vec};

pub enum Bip39EntryMsg {
    Finish,
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
    pad: Pad,
    offer_words: bool,
    bip39_words_list: bip39::Wordlist,
    words: Vec<String<8>, 24>, // BIP39 has at most 24 words, each at most 8 characters
    word_count: u8,
}

impl Bip39Entry {
    pub fn new(word_count: u8) -> Self {
        let letter_choices: Vec<char, MAX_CHOICE_LENGTH> =
            bip39::get_available_letters("").collect();

        let choices = Self::get_letter_choice_page_items(&letter_choices);

        Self {
            choice_page: ChoicePage::new(choices),
            letter_choices,
            textbox: TextBox::empty(),
            pad: Pad::with_background(theme::BG),
            offer_words: false,
            bip39_words_list: bip39::Wordlist::all(),
            words: Vec::new(),
            word_count,
        }
    }

    /// Letter choice items with BIN leftmost button. Letters are BIG.
    fn get_letter_choice_page_items(
        letter_choices: &Vec<char, MAX_CHOICE_LENGTH>,
    ) -> Vec<ChoiceItems, MAX_CHOICE_LENGTH> {
        // TODO: we could support carousel for letters to quicken it for users
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
        bip39_words_list: &bip39::Wordlist,
    ) -> Vec<ChoiceItems, MAX_CHOICE_LENGTH> {
        let mut choices: Vec<ChoiceItems, MAX_CHOICE_LENGTH> = bip39_words_list
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
        self.bip39_words_list = self.bip39_words_list.filter_prefix(self.textbox.content());

        // Offering words when there is only a few of them
        // Otherwise getting relevant letters
        if self.bip39_words_list.len() < OFFER_WORDS_THRESHOLD {
            self.offer_words = true;

            Self::get_word_choice_page_items(&self.bip39_words_list)
        } else {
            self.offer_words = false;
            self.letter_choices = bip39::get_available_letters(self.textbox.content()).collect();

            Self::get_letter_choice_page_items(&self.letter_choices)
        }
    }

    fn update_situation(&mut self) {
        // On physical device, for a short moment, the header would display
        // "Select word 13/12" before showing another screen.
        if self.has_enough_words() {
            return;
        }
        // TODO: header has no need to change most of the time,
        // so we could maybe call it only when reaching a new word,
        // to reduce the flickering
        // (however, repaint is being called from `self.choice_page` on every letter change).
        self.show_current_header();
        self.show_current_letters();
    }

    /// Display prompt on the top with the current word index.
    fn show_current_header(&mut self) {
        // Clearing the pad not to conflict with the previous index there
        self.pad.clear();
        let title = build_string!(
            20,
            "Select word ",
            inttostr!(self.words.len() as u8 + 1),
            "/",
            inttostr!(self.word_count)
        );
        common::paint_header(Point::zero(), &title, &None);
    }

    /// Displays current letters together with underscore.
    fn show_current_letters(&self) {
        let to_show = build_string!({ MAX_LENGTH + 1 }, self.textbox.content(), "_");
        common::display_center(
            Point::new(64, CURRENT_LETTERS_ROW),
            &to_show,
            theme::FONT_MONO,
        );
    }

    fn reset_wordlist(&mut self) {
        self.bip39_words_list = bip39::Wordlist::all();
    }

    fn has_enough_words(&self) -> bool {
        self.word_count == self.words.len() as u8
    }

    pub fn all_words(&self) -> Vec<String<8>, 24> {
        self.words.clone()
    }

    fn save_new_word(&mut self, word_index: u8) {
        let word = self
            .bip39_words_list
            .get(word_index as usize)
            .unwrap_or_default();
        self.words.push(String::from(word)).unwrap();
    }

    fn start_with_another_word(&mut self, ctx: &mut EventCtx) {
        self.textbox.clear(ctx);
        self.reset_wordlist();
        self.set_new_choices_and_repaint(ctx);
    }

    fn save_new_letter(&mut self, ctx: &mut EventCtx, letter_index: u8) {
        let new_letter = self.letter_choices[letter_index as usize];
        self.textbox.append(ctx, new_letter);
        self.set_new_choices_and_repaint(ctx);
    }

    fn delete_last_letter(&mut self, ctx: &mut EventCtx) {
        self.textbox.delete_last(ctx);
        self.reset_wordlist();
        self.set_new_choices_and_repaint(ctx);
    }

    fn set_new_choices_and_repaint(&mut self, ctx: &mut EventCtx) {
        let new_choices = self.get_current_choices();
        self.choice_page.reset(ctx, new_choices, true, false);
        ctx.request_paint();
    }
}

impl Component for Bip39Entry {
    type Msg = Bip39EntryMsg;

    fn place(&mut self, bounds: Rect) -> Rect {
        let header_height = theme::FONT_HEADER.text_height() + 3;
        let (header_area, choice_area) = bounds.split_top(header_height);
        self.pad.place(header_area);

        self.choice_page.place(choice_area);
        bounds
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        let msg = self.choice_page.event(ctx, event);
        match msg {
            Some(ChoicePageMsg::Choice(page_counter)) => {
                // Clicked SELECT.
                if self.offer_words {
                    self.save_new_word(page_counter);
                    if self.has_enough_words() {
                        return Some(Bip39EntryMsg::Finish);
                    } else {
                        self.start_with_another_word(ctx);
                    }
                } else {
                    self.save_new_letter(ctx, page_counter);
                }
            }
            Some(ChoicePageMsg::LeftMost) => {
                // Clicked BIN.
                self.delete_last_letter(ctx);
            }
            _ => {}
        }

        None
    }

    fn paint(&mut self) {
        self.pad.paint();
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
