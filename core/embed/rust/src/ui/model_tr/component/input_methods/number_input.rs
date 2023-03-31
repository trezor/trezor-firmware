use crate::ui::{
    component::{Component, Event, EventCtx},
    geometry::Rect,
};

use super::super::{ButtonLayout, ChoiceFactory, ChoiceItem, ChoicePage, ChoicePageMsg};
use heapless::String;

pub enum NumberInputMsg {
    Number(u32),
}

struct ChoiceFactoryNumberInput {
    min: u32,
    max: u32,
}

impl ChoiceFactoryNumberInput {
    fn new(min: u32, max: u32) -> Self {
        Self { min, max }
    }
}

impl ChoiceFactory for ChoiceFactoryNumberInput {
    type Item = ChoiceItem;

    fn count(&self) -> usize {
        (self.max - self.min + 1) as usize
    }

    fn get(&self, choice_index: usize) -> ChoiceItem {
        let num = self.min + choice_index as u32;
        let text: String<10> = String::from(num);
        let mut choice_item = ChoiceItem::new(text, ButtonLayout::default_three_icons());

        // Disabling prev/next buttons for the first/last choice.
        // (could be done to the same button if there is only one)
        if choice_index == 0 {
            choice_item.set_left_btn(None);
        }
        if choice_index == self.count() - 1 {
            choice_item.set_right_btn(None);
        }

        choice_item
    }
}

/// Simple wrapper around `ChoicePage` that allows for
/// inputting a list of values and receiving the chosen one.
pub struct NumberInput {
    choice_page: ChoicePage<ChoiceFactoryNumberInput>,
    min: u32,
}

impl NumberInput {
    pub fn new(min: u32, max: u32, init_value: u32) -> Self {
        let choices = ChoiceFactoryNumberInput::new(min, max);
        let initial_page = init_value - min;
        Self {
            min,
            choice_page: ChoicePage::new(choices).with_initial_page_counter(initial_page as usize),
        }
    }
}

impl Component for NumberInput {
    type Msg = NumberInputMsg;

    fn place(&mut self, bounds: Rect) -> Rect {
        self.choice_page.place(bounds)
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        let msg = self.choice_page.event(ctx, event);
        match msg {
            Some(ChoicePageMsg::Choice(page_counter)) => {
                let result_num = self.min + page_counter as u32;
                Some(NumberInputMsg::Number(result_num))
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
impl crate::trace::Trace for NumberInput {
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
                let current_num = self.min + current_index as u32;
                ButtonAction::select_item(inttostr!(current_num))
            }
        }
    }

    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.open("NumberInput");
        self.report_btn_actions(t);
        t.field("choice_page", &self.choice_page);
        t.close();
    }
}
