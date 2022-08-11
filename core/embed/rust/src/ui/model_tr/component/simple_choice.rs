use crate::ui::{
    component::{Component, Event, EventCtx},
    geometry::Rect,
};

use super::{ButtonLayout, ChoiceItems, ChoicePage, ChoicePageMsg, TextChoiceItem};
use heapless::{String, Vec};

#[cfg(feature = "ui_debug")]
use super::{ButtonAction, ButtonPos};

pub enum SimpleChoiceMsg {
    Result(String<50>),
}

/// Simple wrapper around `ChoicePage` that allows for
/// inputting a list of values and receiving the chosen one.
pub struct SimpleChoice<T, const N: usize> {
    choices: Vec<T, N>,
    choice_page: ChoicePage<N>,
}

impl<T, const N: usize> SimpleChoice<T, N>
where
    T: AsRef<str>,
{
    pub fn new(str_choices: Vec<T, N>) -> Self {
        let mut choices: Vec<ChoiceItems, N> = str_choices
            .iter()
            .map(|word| {
                let choice = TextChoiceItem::new(word, ButtonLayout::default_three_icons());
                ChoiceItems::Text(choice)
            })
            .collect();
        // Not wanting anything as leftmost and rightmost button
        let last_index = choices.len() - 1;
        choices[0].set_left_btn(None);
        choices[last_index].set_right_btn(None);

        Self {
            choices: str_choices,
            choice_page: ChoicePage::new(choices),
        }
    }
}

impl<T, const N: usize> Component for SimpleChoice<T, N>
where
    T: AsRef<str>,
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
