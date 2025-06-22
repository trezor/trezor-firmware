use crate::{
    strutil::TString,
    ui::{
        component::{Component, Event, EventCtx},
        geometry::Rect,
        shape::Renderer,
    },
};

use super::super::{
    ButtonDetails, ButtonLayout, ChoiceControls, ChoiceFactory, ChoiceItem, ChoiceMsg, ChoicePage,
};
use heapless::Vec;

// So that there is only one implementation, and not multiple generic ones
// as would be via `const N: usize` generics.
const MAX_LENGTH: usize = 5;

struct ChoiceFactorySimple {
    choices: Vec<TString<'static>, MAX_LENGTH>,
    controls: ChoiceControls,
    select_text: TString<'static>,
}

impl ChoiceFactorySimple {
    fn new(
        choices: Vec<TString<'static>, MAX_LENGTH>,
        controls: ChoiceControls,
        select_text: TString<'static>,
    ) -> Self {
        Self {
            choices,
            controls,
            select_text,
        }
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
        let mut choice_item =
            text.map(|t| ChoiceItem::new(t, ButtonLayout::arrow_armed_arrow(self.select_text)));

        // Disabling prev/next buttons for the first/last choice when not in carousel.
        // (could be done to the same item if there is only one)
        if self.controls != ChoiceControls::Carousel {
            if choice_index == 0 {
                if self.controls == ChoiceControls::Cancellable {
                    choice_item.set_left_btn(Some(ButtonDetails::cancel_icon()));
                } else {
                    choice_item.set_left_btn(None);
                }
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
    pub fn new(
        str_choices: Vec<TString<'static>, MAX_LENGTH>,
        controls: ChoiceControls,
        select_text: TString<'static>,
    ) -> Self {
        let choices = ChoiceFactorySimple::new(str_choices, controls, select_text);
        let choice_page = ChoicePage::new(choices).with_controls(controls);
        Self {
            choice_page,
            return_index: false,
        }
    }

    /// Set the page counter at the very beginning.
    pub fn with_initial_page_counter(mut self, page_counter: usize) -> Self {
        self.choice_page = self.choice_page.with_initial_page_counter(page_counter);
        self
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
    type Msg = ChoiceMsg<usize>;

    fn place(&mut self, bounds: Rect) -> Rect {
        self.choice_page.place(bounds)
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        self.choice_page.event(ctx, event)
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
