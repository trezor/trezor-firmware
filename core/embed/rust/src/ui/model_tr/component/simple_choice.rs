use crate::ui::{
    component::{Component, Event, EventCtx},
    geometry::Rect,
};
use core::ops::Deref;

use super::{
    common::{ButtonDetails, StringChoiceItem},
    ChoicePage, ChoicePageMsg,
};
use heapless::{String, Vec};

pub enum SimpleChoiceMsg {
    Result(String<50>),
}

/// Simple wrapper around `ChoicePage` that allows for
/// inputting a list of values and receiving the chosen one.
pub struct SimpleChoice<T, const N: usize> {
    choices: Vec<T, N>,
    choice_page: ChoicePage<StringChoiceItem, N>,
    result_choice_index: usize,
}

impl<T, const N: usize> SimpleChoice<T, N>
where
    T: Deref<Target = str>,
{
    pub fn new(str_choices: Vec<T, N>) -> Self {
        let mut choices: Vec<StringChoiceItem, N> = str_choices
            .iter()
            .map(|digit| {
                StringChoiceItem::from_str(
                    digit.as_ref(),
                    Some(ButtonDetails::new("BACK")),
                    Some(ButtonDetails::new("SELECT")),
                    Some(ButtonDetails::new("NEXT")),
                )
            })
            .collect();
        // Not wanting anything as leftmost and rightmost button
        let last_index = choices.len() - 1;
        choices[0].btn_left = None;
        choices[last_index].btn_right = None;

        Self {
            choices: str_choices,
            choice_page: ChoicePage::new(choices),
            result_choice_index: 0,
        }
    }
}

impl<T, const N: usize> Component for SimpleChoice<T, N>
where
    T: Deref<Target = str>,
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
    T: Deref<Target = str>,
{
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.open("SimpleChoice");
        t.close();
    }
}
