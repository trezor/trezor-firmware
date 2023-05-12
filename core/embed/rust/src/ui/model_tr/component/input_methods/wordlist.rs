use crate::{
    strutil::StringType,
    trezorhal::wordlist::Wordlist,
    ui::{
        component::{text::common::TextBox, Child, Component, ComponentExt, Event, EventCtx},
        geometry::Rect,
        util::char_to_string,
    },
};

use super::super::{theme, ButtonLayout, ChangingTextLine, ChoiceFactory, ChoiceItem, ChoicePage};
use heapless::String;

enum WordlistAction {
    Letter(char),
    Word(&'static str),
    Delete,
}

const MAX_WORD_LENGTH: usize = 10;
const MAX_LETTERS_LENGTH: usize = 26;

/// Offer words when there will be fewer of them than this
const OFFER_WORDS_THRESHOLD: usize = 10;

/// Where will be the DELETE option - at the first position
const DELETE_INDEX: usize = 0;
/// Which index will be used at the beginning.
/// (Accounts for DELETE to be at index 0)
const INITIAL_PAGE_COUNTER: usize = DELETE_INDEX + 1;

const PROMPT: &str = "_";

/// Type of the wordlist, deciding the list of words to be used
#[derive(Clone, Copy)]
pub enum WordlistType {
    Bip39,
    Slip39,
}

struct ChoiceFactoryWordlist {
    wordlist: Wordlist,
    offer_words: bool,
}

impl ChoiceFactoryWordlist {
    pub fn new(wordlist_type: WordlistType, prefix: &str) -> Self {
        let wordlist = match wordlist_type {
            WordlistType::Bip39 => Wordlist::bip39(),
            WordlistType::Slip39 => Wordlist::slip39(),
        }
        .filter_prefix(prefix);
        let offer_words = wordlist.len() < OFFER_WORDS_THRESHOLD;
        Self {
            wordlist,
            offer_words,
        }
    }
}

impl<T: StringType> ChoiceFactory<T> for ChoiceFactoryWordlist {
    type Action = WordlistAction;

    fn count(&self) -> usize {
        // Accounting for the DELETE option (+1)
        1 + if self.offer_words {
            self.wordlist.len()
        } else {
            self.wordlist.get_available_letters().count()
        }
    }

    fn get(&self, choice_index: usize) -> (ChoiceItem<T>, Self::Action) {
        // Putting DELETE as the first option in both cases
        // (is a requirement for WORDS, doing it for LETTERS as well to unite it)
        if choice_index == DELETE_INDEX {
            return (
                ChoiceItem::new("DELETE", ButtonLayout::arrow_armed_arrow("CONFIRM".into()))
                    .with_icon(theme::ICON_DELETE),
                WordlistAction::Delete,
            );
        }
        if self.offer_words {
            let word = self.wordlist.get(choice_index - 1).unwrap_or_default();
            (
                ChoiceItem::new(word, ButtonLayout::default_three_icons()),
                WordlistAction::Word(word),
            )
        } else {
            let letter = self
                .wordlist
                .get_available_letters()
                .nth(choice_index - 1)
                .unwrap_or_default();
            (
                ChoiceItem::new(char_to_string(letter), ButtonLayout::default_three_icons()),
                WordlistAction::Letter(letter),
            )
        }
    }
}

/// Component for entering a mnemonic from a wordlist - BIP39 or SLIP39.
pub struct WordlistEntry<T: StringType> {
    choice_page: ChoicePage<ChoiceFactoryWordlist, T, WordlistAction>,
    chosen_letters: Child<ChangingTextLine<String<{ MAX_WORD_LENGTH + 1 }>>>,
    textbox: TextBox<MAX_WORD_LENGTH>,
    offer_words: bool,
    wordlist_type: WordlistType,
}

impl<T> WordlistEntry<T>
where
    T: StringType + Clone,
{
    pub fn new(wordlist_type: WordlistType) -> Self {
        let choices = ChoiceFactoryWordlist::new(wordlist_type, "");
        Self {
            // Starting at second page because of DELETE option
            choice_page: ChoicePage::new(choices)
                .with_incomplete(true)
                .with_carousel(true)
                .with_initial_page_counter(INITIAL_PAGE_COUNTER),
            chosen_letters: Child::new(ChangingTextLine::center_mono(String::from(PROMPT))),
            textbox: TextBox::empty(),
            offer_words: false,
            wordlist_type,
        }
    }

    /// Gets up-to-date choices for letters or words.
    fn get_current_choices(&mut self) -> ChoiceFactoryWordlist {
        // Narrowing the word list
        ChoiceFactoryWordlist::new(self.wordlist_type, self.textbox.content())
    }

    /// Updates the whole page.
    fn update(&mut self, ctx: &mut EventCtx) {
        self.update_chosen_letters(ctx);
        let new_choices = self.get_current_choices();
        self.offer_words = new_choices.offer_words;
        // Not using carousel in case of words, as that looks weird in case
        // there is only one word to choose from.
        self.choice_page.reset(
            ctx,
            new_choices,
            Some(INITIAL_PAGE_COUNTER),
            !self.offer_words,
        );
        ctx.request_paint();
    }

    /// Reflects currently chosen letters in the textbox.
    fn update_chosen_letters(&mut self, ctx: &mut EventCtx) {
        let text = build_string!({ MAX_WORD_LENGTH + 1 }, self.textbox.content(), PROMPT);
        self.chosen_letters.mutate(ctx, |ctx, chosen_letters| {
            chosen_letters.update_text(text);
            chosen_letters.request_complete_repaint(ctx);
        });
    }
}

impl<T> Component for WordlistEntry<T>
where
    T: StringType + Clone,
{
    type Msg = &'static str;

    fn place(&mut self, bounds: Rect) -> Rect {
        let letters_area_height = self.chosen_letters.inner().needed_height();
        let (letters_area, choice_area) = bounds.split_top(letters_area_height);
        self.chosen_letters.place(letters_area);
        self.choice_page.place(choice_area);
        bounds
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        match self.choice_page.event(ctx, event) {
            Some(WordlistAction::Delete) => {
                self.textbox.delete_last(ctx);
                self.update(ctx);
            }
            Some(WordlistAction::Letter(letter)) => {
                self.textbox.append(ctx, letter);
                self.update(ctx);
            }
            Some(WordlistAction::Word(word)) => {
                return Some(word);
            }
            _ => {}
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
impl<T> crate::trace::Trace for WordlistEntry<T>
where
    T: StringType + Clone,
{
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        match self.wordlist_type {
            WordlistType::Bip39 => t.component("Bip39Entry"),
            WordlistType::Slip39 => t.component("Slip39Entry"),
        }
        t.string("textbox", self.textbox.content());

        if self.offer_words {
            t.bool("word_choices", true);
        } else {
            t.bool("letter_choices", true);
        }

        t.child("choice_page", &self.choice_page);
    }
}
