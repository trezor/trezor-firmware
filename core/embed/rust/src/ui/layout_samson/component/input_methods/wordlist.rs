use crate::{
    translations::TR,
    trezorhal::{random, wordlist::Wordlist},
    ui::{
        component::{text::common::TextBox, Child, Component, ComponentExt, Event, EventCtx},
        geometry::Rect,
        shape::Renderer,
        util::char_to_string,
    },
};

use super::super::{theme, ButtonLayout, ChangingTextLine, ChoiceFactory, ChoiceItem, ChoicePage};
use heapless::Vec;

enum WordlistAction {
    Letter(char),
    Word(&'static str),
    Delete,
    Previous,
}

const MAX_WORD_LENGTH: usize = 10;
const LINE_CAPACITY: usize = MAX_WORD_LENGTH + 1;

/// Offer words when there will be fewer of them than this
const OFFER_WORDS_THRESHOLD: usize = 10;

/// Where will be the DELETE option - at the first position
const DELETE_INDEX: usize = 0;
/// Which index will be used at the beginning.
/// (Accounts for DELETE to be at index 0)
const INITIAL_PAGE_COUNTER: usize = DELETE_INDEX + 1;

const PROMPT: &str = "_";

/// Choosing random choice index, disregarding DELETE option
fn get_random_position(num_choices: usize) -> usize {
    random::uniform_between(INITIAL_PAGE_COUNTER as u32, (num_choices - 1) as u32) as usize
}

/// Type of the wordlist, deciding the list of words to be used
#[derive(Clone, Copy)]
pub enum WordlistType {
    Bip39,
    Slip39,
}

struct ChoiceFactoryWordlist {
    wordlist: Wordlist,
    offer_words: bool,
    /// We want to randomize the order in which we show the words
    word_random_order: Vec<usize, OFFER_WORDS_THRESHOLD>,
    /// Whether the input is empty - and we should show PREVIOUS instead of
    /// DELETE
    empty_input: bool,
}

impl ChoiceFactoryWordlist {
    pub fn new(wordlist_type: WordlistType, prefix: &str) -> Self {
        let wordlist = match wordlist_type {
            WordlistType::Bip39 => Wordlist::bip39(),
            WordlistType::Slip39 => Wordlist::slip39(),
        }
        .filter_prefix(prefix);
        let offer_words = wordlist.len() < OFFER_WORDS_THRESHOLD;
        let word_random_order: Vec<usize, OFFER_WORDS_THRESHOLD> = if offer_words {
            // Filling slice with numbers 0..wordlist.len() and shuffling them
            let slice = &mut [0; OFFER_WORDS_THRESHOLD][..wordlist.len()];
            for (i, item) in slice.iter_mut().enumerate() {
                *item = i;
            }
            random::shuffle(slice);
            slice.iter().copied().collect()
        } else {
            Vec::new()
        };
        Self {
            wordlist,
            offer_words,
            word_random_order,
            empty_input: prefix.is_empty(),
        }
    }
}

impl ChoiceFactory for ChoiceFactoryWordlist {
    type Action = WordlistAction;
    type Item = ChoiceItem;

    fn count(&self) -> usize {
        // Accounting for the DELETE option (+1)
        1 + if self.offer_words {
            self.wordlist.len()
        } else {
            self.wordlist.get_available_letters().count()
        }
    }

    fn get(&self, choice_index: usize) -> (Self::Item, Self::Action) {
        // Putting DELETE as the first option in both cases
        // (is a requirement for WORDS, doing it for LETTERS as well to unite it)
        if choice_index == DELETE_INDEX {
            if self.empty_input {
                return (
                    TR::inputs__previous.map_translated(|t| {
                        ChoiceItem::new(
                            t,
                            ButtonLayout::arrow_armed_arrow(TR::buttons__select.into()),
                        )
                        .with_icon(theme::ICON_DELETE)
                        .with_middle_action_without_release()
                    }),
                    WordlistAction::Previous,
                );
            } else {
                return (
                    TR::inputs__delete.map_translated(|t| {
                        ChoiceItem::new(
                            t,
                            ButtonLayout::arrow_armed_arrow(TR::buttons__select.into()),
                        )
                        .with_icon(theme::ICON_DELETE)
                        .with_middle_action_without_release()
                    }),
                    WordlistAction::Delete,
                );
            }
        }
        if self.offer_words {
            // Taking a random (but always the same) word on this position
            let index = self.word_random_order[choice_index - 1];
            let word = self.wordlist.get(index).unwrap_or_default();
            (
                ChoiceItem::new(
                    word,
                    ButtonLayout::arrow_armed_arrow(TR::buttons__select.into()),
                ),
                WordlistAction::Word(word),
            )
        } else {
            let letter = self
                .wordlist
                .get_available_letters()
                .nth(choice_index - 1)
                .unwrap_or_default();
            (
                ChoiceItem::new(
                    char_to_string(letter),
                    ButtonLayout::arrow_armed_arrow(TR::buttons__select.into()),
                ),
                WordlistAction::Letter(letter),
            )
        }
    }
}

/// Component for entering a mnemonic from a wordlist - BIP39 or SLIP39.
pub struct WordlistEntry {
    choice_page: ChoicePage<ChoiceFactoryWordlist, WordlistAction>,
    chosen_letters: Child<ChangingTextLine>,
    textbox: TextBox,
    offer_words: bool,
    wordlist_type: WordlistType,
    /// Whether going back is allowed (is not on the very first word).
    can_go_back: bool,
}

impl WordlistEntry {
    pub fn new(wordlist_type: WordlistType, can_go_back: bool) -> Self {
        let choices = ChoiceFactoryWordlist::new(wordlist_type, "");
        let choices_count = <ChoiceFactoryWordlist as ChoiceFactory>::count(&choices);
        Self {
            // Starting at random letter position
            choice_page: ChoicePage::new(choices)
                .with_incomplete(true)
                .with_carousel(true)
                .with_initial_page_counter(get_random_position(choices_count)),
            chosen_letters: Child::new(ChangingTextLine::center_mono(PROMPT, LINE_CAPACITY)),
            textbox: TextBox::empty(MAX_WORD_LENGTH),
            offer_words: false,
            wordlist_type,
            can_go_back,
        }
    }

    pub fn prefilled_word(word: &str, wordlist_type: WordlistType, can_go_back: bool) -> Self {
        // Word may be empty string, fallback to normal input
        if word.is_empty() {
            return Self::new(wordlist_type, can_go_back);
        }

        let choices = ChoiceFactoryWordlist::new(wordlist_type, word);
        Self {
            // Showing the chosen word at index 1
            choice_page: ChoicePage::new(choices)
                .with_incomplete(true)
                .with_initial_page_counter(1),
            chosen_letters: Child::new(ChangingTextLine::center_mono(word, LINE_CAPACITY)),
            textbox: TextBox::new(word, MAX_WORD_LENGTH),
            offer_words: false,
            wordlist_type,
            can_go_back,
        }
    }

    /// Gets up-to-date choices for letters or words.
    fn get_current_choices(&mut self) -> ChoiceFactoryWordlist {
        // Narrowing the word list
        ChoiceFactoryWordlist::new(self.wordlist_type, self.textbox.content())
    }

    fn get_last_textbox_letter(&self) -> Option<char> {
        self.textbox.content().chars().last()
    }

    fn get_new_page_counter(&self, new_choices: &ChoiceFactoryWordlist) -> usize {
        // Starting at the random position in case of letters and at the beginning in
        // case of words.
        if self.offer_words {
            INITIAL_PAGE_COUNTER
        } else {
            let choices_count = <ChoiceFactoryWordlist as ChoiceFactory>::count(new_choices);
            // There should be always DELETE and at least one letter
            assert!(choices_count > 1);
            if choices_count == 2 {
                // In case there is only DELETE and one letter, starting on that letter
                // (regardless of the last letter in the textbox)
                return INITIAL_PAGE_COUNTER;
            }
            // We do not want to end up at the same letter as the last one in the textbox
            loop {
                let random_position = get_random_position(choices_count);
                let current_action =
                    <ChoiceFactoryWordlist as ChoiceFactory>::get(new_choices, random_position).1;
                if let WordlistAction::Letter(current_letter) = current_action {
                    if let Some(last_letter) = self.get_last_textbox_letter() {
                        if current_letter == last_letter {
                            // Randomly trying again when the last and current letter match
                            continue;
                        }
                    }
                }
                break random_position;
            }
        }
    }

    /// Updates the whole page.
    fn update(&mut self, ctx: &mut EventCtx) {
        self.update_chosen_letters(ctx);
        let new_choices = self.get_current_choices();
        self.offer_words = new_choices.offer_words;
        let new_page_counter = self.get_new_page_counter(&new_choices);
        // Not using carousel in case of words, as that looks weird in case
        // there is only one word to choose from.
        self.choice_page
            .reset(ctx, new_choices, Some(new_page_counter), !self.offer_words);
        ctx.request_paint();
    }

    /// Reflects currently chosen letters in the textbox.
    fn update_chosen_letters(&mut self, ctx: &mut EventCtx) {
        let text = uformat!("{}{}", self.textbox.content(), PROMPT);
        self.chosen_letters.mutate(ctx, |ctx, chosen_letters| {
            chosen_letters.update_text(&text);
            chosen_letters.request_complete_repaint(ctx);
        });
    }
}

impl Component for WordlistEntry {
    type Msg = &'static str;

    fn place(&mut self, bounds: Rect) -> Rect {
        let letters_area_height = self.chosen_letters.inner().needed_height();
        let (letters_area, choice_area) = bounds.split_top(letters_area_height);
        self.chosen_letters.place(letters_area);
        self.choice_page.place(choice_area);
        bounds
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        if let Some((action, long_press)) = self.choice_page.event(ctx, event) {
            match action {
                WordlistAction::Previous => {
                    if self.can_go_back {
                        return Some("");
                    }
                }
                WordlistAction::Delete => {
                    // Deleting all when long-pressed
                    if long_press {
                        self.textbox.clear(ctx);
                    } else {
                        self.textbox.delete_last(ctx);
                    }
                    self.update(ctx);
                }
                WordlistAction::Letter(letter) => {
                    self.textbox.append(ctx, letter);
                    self.update(ctx);
                }
                WordlistAction::Word(word) => {
                    return Some(word);
                }
            }
        }
        None
    }

    fn render<'s>(&'s self, target: &mut impl Renderer<'s>) {
        self.chosen_letters.render(target);
        self.choice_page.render(target);
    }
}

// DEBUG-ONLY SECTION BELOW

#[cfg(feature = "ui_debug")]
impl crate::trace::Trace for WordlistEntry {
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.component("MnemonicKeyboard"); // unified with TT
        t.string("textbox", self.textbox.content().into());

        if self.offer_words {
            t.bool("word_choices", true);
        } else {
            t.bool("letter_choices", true);
        }

        t.child("choice_page", &self.choice_page);
    }
}
