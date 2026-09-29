use super::super::{theme, ButtonLayout, ChoiceFactory, ChoiceItem, ChoiceMsg, ChoicePage};
use crate::strutil::ShortString;
use crate::translations::TR;
use crate::ui::component::{Component, Event, EventCtx};
use crate::ui::geometry::Rect;
use crate::ui::shape::Renderer;

/// Action of a single choice in the number input carousel: either a number
/// from the offered range, or going back to the previous screen (the leftmost
/// item).
#[derive(Clone, Copy)]
pub enum NumberInputAction {
    Back,
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
    type Action = NumberInputAction;
    type Item = ChoiceItem;

    fn count(&self) -> usize {
        // one extra item for going back
        (self.max - self.min + 2) as usize
    }

    fn get(&self, choice_index: usize) -> (Self::Item, Self::Action) {
        if choice_index == 0 {
            // the leftmost item goes back to the previous screen when
            // confirmed; there is no going further left from it
            (
                TR::inputs__back.map_translated(|t| {
                    let mut choice_item = ChoiceItem::new(
                        t,
                        ButtonLayout::arrow_armed_arrow(TR::inputs__return.into()),
                    )
                    .with_icon(theme::ICON_ARROW_BACK_UP);
                    choice_item.set_left_btn(None);
                    choice_item
                }),
                NumberInputAction::Back,
            )
        } else {
            let num = self.min + choice_index as u32 - 1;
            let text = unwrap!(ShortString::try_from(num));
            let mut choice_item = ChoiceItem::new(
                text,
                ButtonLayout::arrow_armed_arrow(TR::buttons__select.into()),
            );

            // Disabling the next button for the last choice.
            if choice_index == <ChoiceFactoryNumberInput as ChoiceFactory>::count(self) - 1 {
                choice_item.set_right_btn(None);
            }

            (choice_item, NumberInputAction::Number(num))
        }
    }
}

/// Simple wrapper around `ChoicePage` that allows for
/// inputting a list of values and receiving the chosen one.
pub struct NumberInput {
    choice_page: ChoicePage<ChoiceFactoryNumberInput, NumberInputAction>,
    min: u32,
}

impl NumberInput {
    pub fn new(min: u32, max: u32, init_value: u32) -> Self {
        let choices = ChoiceFactoryNumberInput::new(min, max);
        // +1 to skip the leading "back" item
        let initial_page = init_value - min + 1;
        Self {
            min,
            choice_page: ChoicePage::new(choices).with_initial_page_counter(initial_page as usize),
        }
    }
}

impl Component for NumberInput {
    type Msg = ChoiceMsg<NumberInputAction>;

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
impl crate::trace::Trace for NumberInput {
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.component("NumberInput");
        t.child("choice_page", &self.choice_page);
    }
}
