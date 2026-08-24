use heapless::Vec;

use super::{theme, Button, ButtonMsg};
use crate::error::Error;
use crate::strutil::TString;
use crate::ui::component::{Component, Event, EventCtx};
use crate::ui::geometry::{Insets, Rect};
use crate::ui::shape::Renderer;
use crate::ui::ui_firmware::{MenuItemIntent, MAX_MENU_ITEMS};

/// Maximum number of buttons shown on the screen at once.
/// TODO: pagination for menus with more items.
const MAX_VISIBLE_BUTTONS: usize = 3;

#[cfg_attr(feature = "debug", derive(ufmt::derive::uDebug))]
pub enum SelectMenuMsg {
    /// Menu item selected (index into `items`).
    Selected(usize),
    /// The menu was closed without selecting anything.
    Closed,
}

/// Simple vertical menu of buttons, with a close button in the top-right
/// corner. An entry asking for `MenuItemIntent::Danger` is styled accordingly.
pub struct SelectMenu {
    choice_buttons: Vec<Button, MAX_MENU_ITEMS>,
    close_button: Button,
}

impl SelectMenu {
    pub fn new(
        items: Vec<(TString<'static>, MenuItemIntent), MAX_MENU_ITEMS>,
    ) -> Result<Self, Error> {
        if items.len() > MAX_VISIBLE_BUTTONS {
            return Err(Error::NotImplementedError);
        }
        let choice_buttons = items
            .into_iter()
            .map(|(text, intent)| {
                Button::with_text(text).styled(match intent {
                    MenuItemIntent::Danger => theme::button_cancel(),
                    MenuItemIntent::Standard => theme::button_default(),
                })
            })
            .collect();
        let close_button =
            Button::with_icon(theme::ICON_CORNER_CANCEL).styled(theme::button_moreinfo());

        Ok(Self {
            choice_buttons,
            close_button,
        })
    }

    /// Number of choice buttons that fit on the screen.
    fn visible_choices(&self) -> usize {
        self.choice_buttons.len().min(MAX_VISIBLE_BUTTONS)
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

        bounds
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        let n_choices = self.visible_choices();
        for (i, button) in self.choice_buttons.iter_mut().take(n_choices).enumerate() {
            if matches!(button.event(ctx, event), Some(ButtonMsg::Clicked)) {
                return Some(SelectMenuMsg::Selected(i));
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
        });
        t.child("close_button", &self.close_button);
    }
}
