use crate::{
    micropython::buffer::StrBuffer,
    ui::{
        component::{Component, Event, EventCtx},
        geometry::Rect,
    },
};

use super::super::{ButtonLayout, ChoiceFactory, ChoiceItem, ChoicePage, ChoicePageMsg};
use heapless::{String, Vec};

#[cfg(feature = "ui_debug")]
use super::super::{ButtonAction, ButtonPos};

pub enum SimpleChoiceMsg {
    Result(String<50>),
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

    fn count(&self) -> u8 {
        N as u8
    }

    fn get(&self, choice_index: u8) -> ChoiceItem {
        let text = &self.choices[choice_index as usize];
        let mut choice_item = ChoiceItem::new(text, ButtonLayout::default_three_icons());

        // Disabling prev/next buttons for the first/last choice when not in carousel.
        // (could be done to the same button if there is only one)
        if !self.carousel {
            if choice_index == 0 {
                choice_item.set_left_btn(None);
            }
            if choice_index as usize == N - 1 {
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
}

impl<const N: usize> SimpleChoice<N> {
    pub fn new(str_choices: Vec<StrBuffer, N>, carousel: bool, show_incomplete: bool) -> Self {
        let choices = ChoiceFactorySimple::new(str_choices.clone(), carousel);
        Self {
            choices: str_choices,
            choice_page: ChoicePage::new(choices)
                .with_carousel(carousel)
                .with_incomplete(show_incomplete),
        }
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
                let result = String::from(self.choices[page_counter as usize].as_ref());
                Some(SimpleChoiceMsg::Result(result))
            }
            _ => None,
        }
    }

    fn paint(&mut self) {
        self.choice_page.paint();
    }
}

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
                let current_index = self.choice_page.page_index() as usize;
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
