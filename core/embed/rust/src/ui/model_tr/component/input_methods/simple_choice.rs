use crate::{
    micropython::buffer::StrBuffer,
    ui::{
        component::{Component, Event, EventCtx},
        geometry::Rect,
    },
};

use super::super::{ButtonLayout, ChoiceFactory, ChoiceItem, ChoicePage, ChoicePageMsg};
use heapless::{String, Vec};

pub enum SimpleChoiceMsg {
    Result(String<50>),
    Index(usize),
}

struct ChoiceFactorySimple<const N: usize> {
    choices: Vec<StrBuffer, N>,
    carousel: bool,
}

impl<const N: usize> ChoiceFactorySimple<N> {
    fn new(choices: Vec<StrBuffer, N>, carousel: bool) -> Self {
        Self { choices, carousel }
    }
}

impl<const N: usize> ChoiceFactory for ChoiceFactorySimple<N> {
    type Item = ChoiceItem;

    fn count(&self) -> usize {
        N
    }

    fn get(&self, choice_index: usize) -> ChoiceItem {
        let text = &self.choices[choice_index];
        let mut choice_item = ChoiceItem::new(text, ButtonLayout::default_three_icons());

        // Disabling prev/next buttons for the first/last choice when not in carousel.
        // (could be done to the same button if there is only one)
        if !self.carousel {
            if choice_index == 0 {
                choice_item.set_left_btn(None);
            }
            if choice_index == N - 1 {
                choice_item.set_right_btn(None);
            }
        }

        choice_item
    }
}

/// Simple wrapper around `ChoicePage` that allows for
/// inputting a list of values and receiving the chosen one.
pub struct SimpleChoice<const N: usize> {
    choices: Vec<StrBuffer, N>,
    choice_page: ChoicePage<ChoiceFactorySimple<N>>,
    return_index: bool,
}

impl<const N: usize> SimpleChoice<N> {
    pub fn new(str_choices: Vec<StrBuffer, N>, carousel: bool) -> Self {
        let choices = ChoiceFactorySimple::new(str_choices.clone(), carousel);
        Self {
            choices: str_choices,
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
}

impl<const N: usize> Component for SimpleChoice<N> {
    type Msg = SimpleChoiceMsg;

    fn place(&mut self, bounds: Rect) -> Rect {
        self.choice_page.place(bounds)
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        let msg = self.choice_page.event(ctx, event);
        match msg {
            Some(ChoicePageMsg::Choice(page_counter)) => {
                if self.return_index {
                    Some(SimpleChoiceMsg::Index(page_counter))
                } else {
                    let result = String::from(self.choices[page_counter].as_ref());
                    Some(SimpleChoiceMsg::Result(result))
                }
            }
            _ => None,
        }
    }

    fn paint(&mut self) {
        self.choice_page.paint();
    }
}

// DEBUG-ONLY SECTION BELOW

#[cfg(feature = "ui_debug")]
use super::super::{ButtonAction, ButtonPos};

#[cfg(feature = "ui_debug")]
impl<const N: usize> crate::trace::Trace for SimpleChoice<N> {
    fn get_btn_action(&self, pos: ButtonPos) -> String<25> {
        match pos {
            ButtonPos::Left => match self.choice_page.has_previous_choice() {
                true => ButtonAction::PrevPage.string(),
                false => ButtonAction::empty(),
            },
            ButtonPos::Right => match self.choice_page.has_next_choice() {
                true => ButtonAction::NextPage.string(),
                false => ButtonAction::empty(),
            },
            ButtonPos::Middle => {
                let current_index = self.choice_page.page_index();
                ButtonAction::select_item(self.choices[current_index].as_ref())
            }
        }
    }

    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.open("SimpleChoice");
        self.report_btn_actions(t);
        t.field("choice_page", &self.choice_page);
        t.close();
    }
}
