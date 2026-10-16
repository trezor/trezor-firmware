use super::super::component::{ButtonLayout, ChoiceFactory, ChoiceItem, ChoiceMsg, ChoicePage};
use super::super::theme::bootloader::BLD_BG;
use crate::ui::component::{Component, Event, EventCtx, Pad};
use crate::ui::geometry::Rect;
use crate::ui::layout::simplified::ReturnToC;
use crate::ui::shape::Renderer;

#[repr(u32)]
#[derive(Copy, Clone)]
pub enum MenuMsg {
    Close = 0xAABBCCDD,
    Reboot = 0x11223344,
    FactoryReset = 0x55667788,
}
impl ReturnToC for MenuMsg {
    fn return_to_c(self) -> u32 {
        self as u32
    }
}

/// Items of the bootloader menu, see `MenuMsg::from_selection`.
pub const MENU_ITEMS: [&str; 2] = ["Reboot", "Factory reset"];

impl MenuMsg {
    pub fn from_selection(selection: MenuSelection) -> Option<Self> {
        Some(match selection {
            MenuSelection::Close => Self::Close,
            MenuSelection::Item(0) => Self::Reboot,
            MenuSelection::Item(_) => Self::FactoryReset,
        })
    }
}

#[derive(Copy, Clone)]
pub enum MenuSelection {
    /// The menu was closed by the cross on its first item
    Close,
    /// Index of the selected item
    Item(usize),
}

pub struct MenuChoiceFactory<const N: usize> {
    items: [&'static str; N],
}

impl<const N: usize> ChoiceFactory for MenuChoiceFactory<N> {
    type Action = usize;
    type Item = ChoiceItem;

    fn count(&self) -> usize {
        N
    }

    fn get(&self, choice_index: usize) -> (Self::Item, Self::Action) {
        let btn_layout = ButtonLayout::menu_item(choice_index == 0, choice_index == N - 1);
        (
            ChoiceItem::new(self.items[choice_index], btn_layout),
            choice_index,
        )
    }
}

/// Context menu carousel, the same as the firmware `select_menu`. The cross on
/// the first item closes the menu.
pub struct Menu<const N: usize> {
    pad: Pad,
    choice_page: ChoicePage<MenuChoiceFactory<N>, usize>,
}

impl<const N: usize> Menu<N> {
    pub fn new(items: [&'static str; N]) -> Self {
        let choices = MenuChoiceFactory { items };
        Self {
            pad: Pad::with_background(BLD_BG).with_clear(),
            choice_page: ChoicePage::new(choices).with_incomplete(true),
        }
    }
}

impl<const N: usize> Component for Menu<N> {
    type Msg = MenuSelection;

    fn place(&mut self, bounds: Rect) -> Rect {
        self.pad.place(bounds);
        self.choice_page.place(bounds);
        bounds
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        match self.choice_page.event(ctx, event) {
            Some(ChoiceMsg::Choice { item, .. }) => Some(MenuSelection::Item(item)),
            Some(ChoiceMsg::Cancel) => Some(MenuSelection::Close),
            None => None,
        }
    }

    fn render<'s>(&'s self, target: &mut impl Renderer<'s>) {
        self.pad.render(target);
        self.choice_page.render(target);
    }
}
