use crate::{
    strutil::TString,
    translations::TR,
    ui::{
        component::{Component, Event, EventCtx},
        geometry::Rect,
        shape::Renderer,
    },
};

use super::super::{ButtonLayout, ChoiceFactory, ChoiceItem, ChoicePage};
use heapless::Vec;

// So that there is only one implementation, and not multiple generic ones
// as would be via `const N: usize` generics.
const MAX_LENGTH: usize = 5;

struct ChoiceFactorySimple {
    choices: Vec<TString<'static>, MAX_LENGTH>,
    carousel: bool,
}

impl ChoiceFactorySimple {
    fn new(choices: Vec<TString<'static>, MAX_LENGTH>, carousel: bool) -> Self {
        Self { choices, carousel }
    }

    fn get_string(&self, choice_index: usize) -> TString<'static> {
        self.choices[choice_index]
    }
}

impl ChoiceFactory for ChoiceFactorySimple {
    type Action = usize;
    type Item = ChoiceItem;

    fn count(&self) -> usize {
        self.choices.len()
    }

    fn get(&self, choice_index: usize) -> (Self::Item, Self::Action) {
        let text = &self.choices[choice_index];
        let mut choice_item = text.map(|t| {
            ChoiceItem::new(
                t,
                ButtonLayout::arrow_armed_arrow(TR::buttons__select.into()),
            )
        });

        // Disabling prev/next buttons for the first/last choice when not in carousel.
        // (could be done to the same button if there is only one)
        if !self.carousel {
            if choice_index == 0 {
                choice_item.set_left_btn(None);
            }
            if choice_index == self.count() - 1 {
                choice_item.set_right_btn(None);
            }
        }

        (choice_item, choice_index)
    }
}

/// Simple wrapper around `ChoicePage` that allows for
/// inputting a list of values and receiving the chosen one.
pub struct SimpleChoice {
    choice_page: ChoicePage<ChoiceFactorySimple, usize>,
    pub return_index: bool,
}

impl SimpleChoice {
    pub fn new(str_choices: Vec<TString<'static>, MAX_LENGTH>, carousel: bool) -> Self {
        let choices = ChoiceFactorySimple::new(str_choices, carousel);
        Self {
            choice_page: ChoicePage::new(choices).with_carousel(carousel),
            return_index: false,
        }
    }

    /// Show only the currently selected item, nothing left/right.
    pub fn with_only_one_item(mut self) -> Self {
        self.choice_page = self.choice_page.with_only_one_item(true);
        self
    }

    /// Show choices even when they do not fit entirely.
    pub fn with_show_incomplete(mut self) -> Self {
        self.choice_page = self.choice_page.with_incomplete(true);
        self
    }

    /// Returning chosen page index instead of the string result.
    pub fn with_return_index(mut self) -> Self {
        self.return_index = true;
        self
    }

    /// Translating the resulting index into actual string choice.
    pub fn result_by_index(&self, index: usize) -> TString<'static> {
        self.choice_page.choice_factory().get_string(index)
    }
}

impl Component for SimpleChoice {
    type Msg = usize;

    fn place(&mut self, bounds: Rect) -> Rect {
        self.choice_page.place(bounds)
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        self.choice_page.event(ctx, event).map(|evt| evt.0)
    }

    fn paint(&mut self) {
        self.choice_page.paint();
    }

    fn render<'s>(&'s self, target: &mut impl Renderer<'s>) {
        self.choice_page.render(target);
    }
}

// DEBUG-ONLY SECTION BELOW

#[cfg(feature = "ui_debug")]
impl crate::trace::Trace for SimpleChoice {
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.component("SimpleChoice");
        t.child("choice_page", &self.choice_page);
    }
}
