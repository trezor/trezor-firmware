use crate::{
    trezorhal::bip39,
    ui::{
        component::{text::common::TextBox, Child, Component, ComponentExt, Event, EventCtx},
        display::Icon,
        geometry::Rect,
        model_tr::theme,
        util::char_to_string,
    },
};

use super::super::{
    ButtonLayout, ChangingTextLine, ChoiceFactory, ChoiceItem, ChoicePage, ChoicePageMsg,
};
use heapless::{String, Vec};

pub enum Bip39EntryMsg {
    ResultWord(String<15>),
}

const MAX_WORD_LENGTH: usize = 10;
const MAX_CHOICE_LENGTH: usize = 26;

/// Offer words when there will be fewer of them than this
const OFFER_WORDS_THRESHOLD: usize = 10;

const PROMPT: &str = "_";

/// We are offering either letters or words.
enum ChoiceFactoryBIP39 {
    Letters(Vec<char, MAX_CHOICE_LENGTH>),
    Words(Vec<&'static str, OFFER_WORDS_THRESHOLD>),
}

impl ChoiceFactoryBIP39 {
    fn letters(letter_choices: Vec<char, MAX_CHOICE_LENGTH>) -> Self {
        Self::Letters(letter_choices)
    }

    fn words(word_choices: Vec<&'static str, OFFER_WORDS_THRESHOLD>) -> Self {
        Self::Words(word_choices)
    }
}

impl ChoiceFactory for ChoiceFactoryBIP39 {
    type Item = ChoiceItem;

    fn count(&self) -> u8 {
        // Accounting for the DELETE option
        match self {
            Self::Letters(letter_choices) => letter_choices.len() as u8 + 1,
            Self::Words(word_choices) => word_choices.len() as u8 + 1,
        }
    }

    fn get(&self, choice_index: u8) -> ChoiceItem {
        // Letters have a carousel, words do not
        match self {
            Self::Letters(letter_choices) => {
                if choice_index >= letter_choices.len() as u8 {
                    ChoiceItem::new("DELETE", ButtonLayout::arrow_armed_icon("CONFIRM".into()))
                        .with_icon(Icon::new(theme::ICON_DELETE))
                } else {
                    let letter = letter_choices[choice_index as usize];
                    ChoiceItem::new(
                        char_to_string::<1>(letter),
                        ButtonLayout::default_three_icons(),
                    )
                }
            }
            Self::Words(word_choices) => {
                if choice_index >= word_choices.len() as u8 {
                    let mut item =
                        ChoiceItem::new("DELETE", ButtonLayout::arrow_armed_icon("CONFIRM".into()))
                            .with_icon(Icon::new(theme::ICON_DELETE));
                    item.set_right_btn(None);
                    item
                } else {
                    let word = word_choices[choice_index as usize];
                    let mut item = ChoiceItem::new(word, ButtonLayout::default_three_icons());
                    if choice_index == 0 {
                        item.set_left_btn(None);
                    }
                    item
                }
            }
        }
    }
}

/// Component for entering a BIP39 mnemonic.
pub struct Bip39Entry {
    choice_page: ChoicePage<ChoiceFactoryBIP39>,
    chosen_letters: Child<ChangingTextLine<String<{ MAX_WORD_LENGTH + 1 }>>>,
    letter_choices: Vec<char, MAX_CHOICE_LENGTH>,
    textbox: TextBox<MAX_WORD_LENGTH>,
    offer_words: bool,
    words_list: bip39::Wordlist,
}

impl Bip39Entry {
    pub fn new() -> Self {
        let letter_choices: Vec<char, MAX_CHOICE_LENGTH> =
            bip39::get_available_letters("").collect();
        let choices = ChoiceFactoryBIP39::letters(letter_choices.clone());

        Self {
            choice_page: ChoicePage::new(choices)
                .with_incomplete(true)
                .with_carousel(true),
            chosen_letters: Child::new(ChangingTextLine::center_mono(String::from(PROMPT))),
            letter_choices,
            textbox: TextBox::empty(),
            offer_words: false,
            words_list: bip39::Wordlist::all(),
        }
    }

    /// Gets up-to-date choices for letters or words.
    fn get_current_choices(&mut self) -> ChoiceFactoryBIP39 {
        // Narrowing the word list
        self.words_list = self.words_list.filter_prefix(self.textbox.content());

        // Offering words when there is only a few of them
        // Otherwise getting relevant letters
        if self.words_list.len() < OFFER_WORDS_THRESHOLD {
            self.offer_words = true;
            let word_choices = self.words_list.iter().collect();
            ChoiceFactoryBIP39::words(word_choices)
        } else {
            self.offer_words = false;
            self.letter_choices = bip39::get_available_letters(self.textbox.content()).collect();
            ChoiceFactoryBIP39::letters(self.letter_choices.clone())
        }
    }

    /// Updates the whole page.
    fn update(&mut self, ctx: &mut EventCtx) {
        self.update_chosen_letters(ctx);
        let new_choices = self.get_current_choices();
        // Not using carousel in case of words, as that looks weird in case
        // there is only one word to choose from.
        self.choice_page
            .reset(ctx, new_choices, true, !self.offer_words);
        ctx.request_paint();
    }

    /// Reflects currently chosen letters in the textbox.
    fn update_chosen_letters(&mut self, ctx: &mut EventCtx) {
        let text = build_string!({ MAX_WORD_LENGTH + 1 }, self.textbox.content(), PROMPT);
        self.chosen_letters.inner_mut().update_text(text);
        self.chosen_letters.request_complete_repaint(ctx);
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

    /// Get the index of DELETE item, which is always at the end.
    fn delete_index(&self) -> usize {
        if self.offer_words {
            self.words_list.len()
        } else {
            self.letter_choices.len()
        }
    }
}

impl Component for Bip39Entry {
    type Msg = Bip39EntryMsg;

    fn place(&mut self, bounds: Rect) -> Rect {
        let letters_area_height = self.chosen_letters.inner().needed_height();
        let (letters_area, choice_area) = bounds.split_top(letters_area_height);
        self.chosen_letters.place(letters_area);
        self.choice_page.place(choice_area);
        bounds
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        let msg = self.choice_page.event(ctx, event);
        if let Some(ChoicePageMsg::Choice(page_counter)) = msg {
            // Clicked SELECT.
            // When we already offer words, return the word at the given index.
            // Otherwise, resetting the choice page with up-to-date choices.
            if page_counter as usize == self.delete_index() {
                // Clicked DELETE. Deleting last letter, updating wordlist and updating choices
                self.delete_last_letter(ctx);
                self.reset_wordlist();
                self.update(ctx);
            } else if self.offer_words {
                let word = self
                    .words_list
                    .get(page_counter as usize)
                    .unwrap_or_default();
                return Some(Bip39EntryMsg::ResultWord(String::from(word)));
            } else {
                let new_letter = self.letter_choices[page_counter as usize];
                self.append_letter(ctx, new_letter);
                self.update(ctx);
            }
        }

        None
    }

    fn paint(&mut self) {
        self.chosen_letters.paint();
        self.choice_page.paint();
    }
}

// DEBUG-ONLY SECTION BELOW

#[cfg(feature = "ui_debug")]
use super::super::{ButtonAction, ButtonPos};
#[cfg(feature = "ui_debug")]
use crate::ui::util;

#[cfg(feature = "ui_debug")]
impl crate::trace::Trace for Bip39Entry {
    fn get_btn_action(&self, pos: ButtonPos) -> String<25> {
        match pos {
            ButtonPos::Left => ButtonAction::PrevPage.string(),
            ButtonPos::Right => ButtonAction::NextPage.string(),
            ButtonPos::Middle => {
                let current_index = self.choice_page.page_index() as usize;
                let choice: String<10> = if current_index == self.delete_index() {
                    String::from("DELETE")
                } else if self.offer_words {
                    self.words_list
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

        t.open("letter_choices");
        for ch in &self.letter_choices {
            t.string(&util::char_to_string::<1>(*ch));
        }
        t.close();

        t.field("choice_page", &self.choice_page);
        t.close();
    }
}
