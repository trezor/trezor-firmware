use crate::ui::{
    component::{Component, Event, EventCtx},
    geometry::Rect,
};

use super::{ButtonLayout, ChoiceFactory, ChoiceItem, ChoicePage, ChoicePageMsg, TextChoiceItem};
use heapless::{String, Vec};

#[cfg(feature = "ui_debug")]
use super::{ButtonAction, ButtonPos};

pub enum SimpleChoiceMsg {
    Result(String<50>),
}

struct ChoiceFactorySimple<T, const N: usize> {
    choices: Vec<T, N>,
}

impl<T, const N: usize> ChoiceFactorySimple<T, N>
where
    T: AsRef<str>,
{
    fn new(choices: Vec<T, N>) -> Self {
        Self { choices }
    }
}

impl<T, const N: usize> ChoiceFactory for ChoiceFactorySimple<T, N>
where
    T: AsRef<str>,
{
    fn get(&self, choice_index: u8) -> ChoiceItem {
        let text = &self.choices[choice_index as usize];
        let text_item = TextChoiceItem::new(text, ButtonLayout::default_three_icons());
        let mut choice_item = ChoiceItem::Text(text_item);

        // Disabling prev/next buttons for the first/last choice.
        if choice_index == 0 {
            choice_item.set_left_btn(None);
        } else if choice_index as usize == N - 1 {
            choice_item.set_right_btn(None);
        }

        choice_item
    }

    fn count(&self) -> u8 {
        N as u8
    }
}

/// Simple wrapper around `ChoicePage` that allows for
/// inputting a list of values and receiving the chosen one.
pub struct SimpleChoice<T, const N: usize>
where
    T: AsRef<str>,
    T: Clone,
{
    choices: Vec<T, N>,
    choice_page: ChoicePage<ChoiceFactorySimple<T, N>>,
}

impl<T, const N: usize> SimpleChoice<T, N>
where
    T: AsRef<str>,
    T: Clone,
{
    pub fn new(str_choices: Vec<T, N>) -> Self {
        let choices = ChoiceFactorySimple::new(str_choices.clone());
        Self {
            choices: str_choices,
            choice_page: ChoicePage::new(choices),
        }
    }
}

impl<T, const N: usize> Component for SimpleChoice<T, N>
where
    T: AsRef<str>,
    T: Clone,
{
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
impl<T, const N: usize> crate::trace::Trace for SimpleChoice<T, N>
where
    T: AsRef<str>,
    T: Clone,
{
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
