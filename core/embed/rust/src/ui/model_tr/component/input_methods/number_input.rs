use crate::{
    strutil::StringType,
    ui::{
        component::{Component, Event, EventCtx},
        geometry::Rect,
    },
};

use super::super::{ButtonLayout, ChoiceFactory, ChoiceItem, ChoicePage};
use heapless::String;

struct ChoiceFactoryNumberInput {
    min: u32,
    max: u32,
}

impl ChoiceFactoryNumberInput {
    fn new(min: u32, max: u32) -> Self {
        Self { min, max }
    }
}

impl<T: StringType + Clone> ChoiceFactory<T> for ChoiceFactoryNumberInput {
    type Action = u32;
    type Item = ChoiceItem<T>;

    fn count(&self) -> usize {
        (self.max - self.min + 1) as usize
    }

    fn get(&self, choice_index: usize) -> (Self::Item, Self::Action) {
        let num = self.min + choice_index as u32;
        let text: String<10> = String::from(num);
        let mut choice_item = ChoiceItem::new(text, ButtonLayout::default_three_icons());

        // Disabling prev/next buttons for the first/last choice.
        // (could be done to the same button if there is only one)
        if choice_index == 0 {
            choice_item.set_left_btn(None);
        }
        if choice_index == <ChoiceFactoryNumberInput as ChoiceFactory<T>>::count(self) - 1 {
            choice_item.set_right_btn(None);
        }

        (choice_item, num)
    }
}

/// Simple wrapper around `ChoicePage` that allows for
/// inputting a list of values and receiving the chosen one.
pub struct NumberInput<T: StringType + Clone> {
    choice_page: ChoicePage<ChoiceFactoryNumberInput, T, u32>,
    min: u32,
}

impl<T> NumberInput<T>
where
    T: StringType + Clone,
{
    pub fn new(min: u32, max: u32, init_value: u32) -> Self {
        let choices = ChoiceFactoryNumberInput::new(min, max);
        let initial_page = init_value - min;
        Self {
            min,
            choice_page: ChoicePage::new(choices).with_initial_page_counter(initial_page as usize),
        }
    }
}

impl<T> Component for NumberInput<T>
where
    T: StringType + Clone,
{
    type Msg = u32;

    fn place(&mut self, bounds: Rect) -> Rect {
        self.choice_page.place(bounds)
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        self.choice_page.event(ctx, event).map(|evt| evt.0)
    }

    fn paint(&mut self) {
        self.choice_page.paint();
    }
}

// DEBUG-ONLY SECTION BELOW

#[cfg(feature = "ui_debug")]
impl<T> crate::trace::Trace for NumberInput<T>
where
    T: StringType + Clone,
{
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.component("NumberInput");
        t.child("choice_page", &self.choice_page);
    }
}
