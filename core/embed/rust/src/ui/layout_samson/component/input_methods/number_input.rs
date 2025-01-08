use crate::{
    strutil::ShortString,
    translations::TR,
    ui::{
        component::{Component, Event, EventCtx},
        geometry::Rect,
        shape::Renderer,
    },
};

use super::super::{ButtonLayout, ChoiceFactory, ChoiceItem, ChoicePage};

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
    type Action = u32;
    type Item = ChoiceItem;

    fn count(&self) -> usize {
        (self.max - self.min + 1) as usize
    }

    fn get(&self, choice_index: usize) -> (Self::Item, Self::Action) {
        let num = self.min + choice_index as u32;
        let text = unwrap!(ShortString::try_from(num));
        let mut choice_item = ChoiceItem::new(
            text,
            ButtonLayout::arrow_armed_arrow(TR::buttons__select.into()),
        );

        // Disabling prev/next buttons for the first/last choice.
        // (could be done to the same button if there is only one)
        if choice_index == 0 {
            choice_item.set_left_btn(None);
        }
        if choice_index == <ChoiceFactoryNumberInput as ChoiceFactory>::count(self) - 1 {
            choice_item.set_right_btn(None);
        }

        (choice_item, num)
    }
}

/// Simple wrapper around `ChoicePage` that allows for
/// inputting a list of values and receiving the chosen one.
pub struct NumberInput {
    choice_page: ChoicePage<ChoiceFactoryNumberInput, u32>,
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
    type Msg = u32;

    fn place(&mut self, bounds: Rect) -> Rect {
        self.choice_page.place(bounds)
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        self.choice_page.event(ctx, event).map(|evt| evt.0)
    }

    fn render<'s>(&'s self, target: &mut impl Renderer<'s>) {
        self.choice_page.render(target);
    }
}

// DEBUG-ONLY SECTION BELOW

#[cfg(feature = "ui_debug")]
impl crate::trace::Trace for NumberInput {
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.component("NumberInput");
        t.child("choice_page", &self.choice_page);
    }
}
