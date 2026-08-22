use heapless::Vec;

use super::{theme, Button, ButtonMsg};
use crate::strutil::TString;
use crate::ui::component::{Component, Event, EventCtx};
use crate::ui::geometry::{Insets, Rect};
use crate::ui::shape::Renderer;
use crate::ui::ui_firmware::MAX_MENU_ITEMS;

/// Maximum number of buttons shown on the screen at once.
/// TODO: pagination for menus with more items.
const MAX_VISIBLE_BUTTONS: usize = 3;

#[cfg_attr(feature = "debug", derive(ufmt::derive::uDebug))]
pub enum SelectMenuMsg {
    /// Menu item selected (index into `items`, excluding the cancel item).
    Selected(usize),
    /// The cancel menu item was selected.
    Cancelled,
    /// The menu was closed without selecting anything.
    Closed,
}

/// Simple vertical menu of buttons, with an optional cancel item at the
/// bottom and a close button in the top-right corner.
pub struct SelectMenu {
    choice_buttons: Vec<Button, MAX_MENU_ITEMS>,
    cancel_button: Option<Button>,
    close_button: Button,
}

impl SelectMenu {
    pub fn new(
        items: Vec<TString<'static>, MAX_MENU_ITEMS>,
        cancel: Option<TString<'static>>,
    ) -> Self {
        let choice_buttons = items
            .into_iter()
            .map(|text| Button::with_text(text).styled(theme::button_pin()))
            .collect();
        let cancel_button =
            cancel.map(|text| Button::with_text(text).styled(theme::button_cancel()));
        let touch_area = {
            let border = theme::borders();
            Insets {
                left: border.left * 4,
                bottom: border.bottom * 4,
                ..border
            }
        };
        let close_button = Button::with_icon(theme::ICON_CORNER_CANCEL)
            .with_expanded_touch_area(touch_area)
            .styled(theme::button_moreinfo());

        Self {
            choice_buttons,
            cancel_button,
            close_button,
        }
    }

    /// Number of choice buttons that fit on the screen. The cancel button is
    /// always visible, so it reserves a slot for itself.
    fn visible_choices(&self) -> usize {
        let max = if self.cancel_button.is_some() {
            MAX_VISIBLE_BUTTONS - 1
        } else {
            MAX_VISIBLE_BUTTONS
        };
        self.choice_buttons.len().min(max)
    }
}

impl Component for SelectMenu {
    type Msg = SelectMenuMsg;

    fn place(&mut self, bounds: Rect) -> Rect {
        let bounds = bounds.inset(theme::borders());

        // Close button in the top-right corner, same as in `Frame`.
        let (_, button_area) = bounds.split_right(theme::CORNER_BUTTON_SIDE);
        let (button_area, _) = button_area.split_top(theme::CORNER_BUTTON_SIDE);
        self.close_button.place(button_area);

        let content = bounds.inset(Insets::top(
            theme::CORNER_BUTTON_SIDE + theme::BUTTON_SPACING,
        ));

        // Buttons are stacked from the top down in fixed-height slots (same
        // height as in `select_word`), so they never stretch to fill the
        // whole area.
        let mut slots = content;
        let n_choices = self.visible_choices();
        for button in self.choice_buttons.iter_mut().take(n_choices) {
            let (slot, rest) = slots.split_top(theme::BUTTON_HEIGHT);
            button.place(slot);
            slots = rest.inset(Insets::top(theme::BUTTON_SPACING));
        }
        if let Some(cancel) = &mut self.cancel_button {
            let (slot, _) = slots.split_top(theme::BUTTON_HEIGHT);
            cancel.place(slot);
        }

        bounds
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        let n_choices = self.visible_choices();
        for (i, button) in self.choice_buttons.iter_mut().take(n_choices).enumerate() {
            if matches!(button.event(ctx, event), Some(ButtonMsg::Clicked)) {
                return Some(SelectMenuMsg::Selected(i));
            }
        }
        if let Some(cancel) = &mut self.cancel_button {
            if matches!(cancel.event(ctx, event), Some(ButtonMsg::Clicked)) {
                return Some(SelectMenuMsg::Cancelled);
            }
        }
        if matches!(
            self.close_button.event(ctx, event),
            Some(ButtonMsg::Clicked)
        ) {
            return Some(SelectMenuMsg::Closed);
        }
        None
    }

    fn render<'s>(&'s self, target: &mut impl Renderer<'s>) {
        for button in self.choice_buttons.iter().take(self.visible_choices()) {
            button.render(target);
        }
        if let Some(cancel) = &self.cancel_button {
            cancel.render(target);
        }
        self.close_button.render(target);
    }
}

#[cfg(feature = "ui_debug")]
impl crate::trace::Trace for SelectMenu {
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.component("SelectMenu");
        t.in_list("buttons", &|button_list| {
            for button in self.choice_buttons.iter().take(self.visible_choices()) {
                button_list.child(button);
            }
            if let Some(cancel) = &self.cancel_button {
                button_list.child(cancel);
            }
        });
        t.child("close_button", &self.close_button);
    }
}
