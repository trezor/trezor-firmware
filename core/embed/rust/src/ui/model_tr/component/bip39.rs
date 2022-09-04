use crate::{
    trezorhal::bip39,
    ui::{
        component::{text::common::TextBox, Component, Event, EventCtx, Pad},
        geometry::{Point, Rect},
        model_tr::theme,
    },
};

use super::{
    choice_item::BigCharacterChoiceItem, common, ButtonDetails, ButtonLayout, ChoiceFactory,
    ChoiceItem, ChoicePage, ChoicePageMsg, TextChoiceItem,
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

struct ChoiceFactoryBIP39 {
    // TODO: replace these Vecs by iterators somehow?
    letter_choices: Option<Vec<char, MAX_CHOICE_LENGTH>>,
    word_choices: Option<Vec<&'static str, OFFER_WORDS_THRESHOLD>>,
}
impl ChoiceFactoryBIP39 {
    fn new(
        letter_choices: Option<Vec<char, MAX_CHOICE_LENGTH>>,
        word_choices: Option<Vec<&'static str, OFFER_WORDS_THRESHOLD>>,
    ) -> Self {
        Self {
            letter_choices,
            word_choices,
        }
    }

    fn letters(letter_choices: Vec<char, MAX_CHOICE_LENGTH>) -> Self {
        Self::new(Some(letter_choices), None)
    }

    fn words(word_choices: Vec<&'static str, OFFER_WORDS_THRESHOLD>) -> Self {
        Self::new(None, Some(word_choices))
    }

    /// Word choice items with BIN leftmost button.
    fn get_word_item(&self, choice_index: u8) -> ChoiceItem {
        if let Some(word_choices) = &self.word_choices {
            let word = word_choices[choice_index as usize];
            let choice = TextChoiceItem::new(word, ButtonLayout::default_three_icons());
            let mut word_item = ChoiceItem::Text(choice);

            // Adding BIN leftmost button and removing the rightmost one.
            if choice_index == 0 {
                word_item.set_left_btn(Some(ButtonDetails::bin_icon()));
            } else if choice_index as usize == word_choices.len() - 1 {
                word_item.set_right_btn(None);
            }

            word_item
        } else {
            unreachable!()
        }
    }

    /// Letter choice items with BIN leftmost button. Letters are BIG.
    fn get_letter_item(&self, choice_index: u8) -> ChoiceItem {
        // TODO: we could support carousel for letters to quicken it for users
        // (but then the BIN would need to be an option on its own, not so
        // user-friendly)
        if let Some(letter_choices) = &self.letter_choices {
            let letter = letter_choices[choice_index as usize];
            let letter_choice =
                BigCharacterChoiceItem::new(letter, ButtonLayout::default_three_icons());
            let mut letter_item = ChoiceItem::BigCharacter(letter_choice);

            // Adding BIN leftmost button and removing the rightmost one.
            if choice_index == 0 {
                letter_item.set_left_btn(Some(ButtonDetails::bin_icon()));
            } else if choice_index as usize == letter_choices.len() - 1 {
                letter_item.set_right_btn(None);
            }

            letter_item
        } else {
            unreachable!()
        }
    }
}
impl ChoiceFactory for ChoiceFactoryBIP39 {
    fn get(&self, choice_index: u8) -> ChoiceItem {
        if self.letter_choices.is_some() {
            self.get_letter_item(choice_index)
        } else if self.word_choices.is_some() {
            self.get_word_item(choice_index)
        } else {
            unreachable!()
        }
    }

    fn count(&self) -> u8 {
        if let Some(letter_choices) = &self.letter_choices {
            letter_choices.len() as u8
        } else if let Some(word_choices) = &self.word_choices {
            word_choices.len() as u8
        } else {
            unreachable!()
        }
    }
}

/// Component for entering a BIP39 mnemonic.
pub struct Bip39Entry {
    choice_page: ChoicePage<ChoiceFactoryBIP39>,
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
        let choices = ChoiceFactoryBIP39::letters(letter_choices.clone());

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

    /// Gets up-to-date choices for letters or words.
    fn get_current_choices(&mut self) -> ChoiceFactoryBIP39 {
        // Narrowing the word list
        self.bip39_words_list = self.bip39_words_list.filter_prefix(self.textbox.content());

        // Offering words when there is only a few of them
        // Otherwise getting relevant letters
        if self.bip39_words_list.len() < OFFER_WORDS_THRESHOLD {
            self.offer_words = true;
            let word_choices = self.bip39_words_list.iter().collect();
            ChoiceFactoryBIP39::words(word_choices)
        } else {
            self.offer_words = false;
            self.letter_choices = bip39::get_available_letters(self.textbox.content()).collect();
            ChoiceFactoryBIP39::letters(self.letter_choices.clone())
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
        // (however, repaint is being called from `self.choice_page` on every letter
        // change).
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
        common::paint_header(Point::zero(), title, None);
    }

    /// Displays current letters together with underscore.
    fn show_current_letters(&self) {
        let text = build_string!({ MAX_LENGTH + 1 }, self.textbox.content(), "_");
        common::display_center(Point::new(64, CURRENT_LETTERS_ROW), text, theme::FONT_MONO);
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
use super::{ButtonAction, ButtonPos};
#[cfg(feature = "ui_debug")]
use crate::ui::util;

#[cfg(feature = "ui_debug")]
impl crate::trace::Trace for Bip39Entry {
    fn get_btn_action(&self, pos: ButtonPos) -> String<25> {
        match pos {
            ButtonPos::Left => match self.choice_page.has_previous_choice() {
                true => ButtonAction::PrevPage.string(),
                false => ButtonAction::Action("Delete last char").string(),
            },
            ButtonPos::Right => match self.choice_page.has_next_choice() {
                true => ButtonAction::NextPage.string(),
                false => ButtonAction::empty(),
            },
            ButtonPos::Middle => {
                let current_index = self.choice_page.page_index() as usize;
                let choice: String<10> = if self.offer_words {
                    self.bip39_words_list
                        .get(current_index)
                        .unwrap_or_default()
                        .into()
                } else {
                    util::char_to_string(self.letter_choices[current_index])
                };
                ButtonAction::select_item(choice)
            }
        }
    }

    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.open("Bip39Entry");
        t.kw_pair("textbox", self.textbox.content());

        self.report_btn_actions(t);

        t.open("words");
        for word in &self.words {
            t.string(word);
        }
        t.close();

        t.open("letter_choices");
        for ch in &self.letter_choices {
            t.string(&util::char_to_string::<1>(*ch));
        }
        t.close();

        t.field("choice_page", &self.choice_page);
        t.close();
    }
}
