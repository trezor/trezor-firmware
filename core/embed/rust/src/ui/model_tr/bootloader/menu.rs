#[cfg(feature = "ui_debug")]
use crate::trace::Tracer;
use crate::ui::{
    component::{Child, Component, ComponentExt, Event, EventCtx, Pad},
    constant::screen,
    display,
    display::Font,
    geometry::{Offset, Rect},
    model_tr::{
        bootloader::{
            theme::{BLD_BG, BLD_FG},
            ReturnToC,
        },
        component::{Choice, ChoiceFactory, ChoicePage, ChoicePageMsg},
        theme::ICON_BIN,
    },
};

#[repr(u32)]
#[derive(Copy, Clone)]
pub enum MenuMsg {
    Close = 1,
    Reboot = 2,
    FactoryReset = 3,
}
impl ReturnToC for MenuMsg {
    fn return_to_c(self) -> u32 {
        self as u32
    }
}

const CHOICE_LENGTH: usize = 3;

pub struct MenuChoice {
    text1: &'static str,
    text2: &'static str,
    icon: &'static [u8],
}

impl MenuChoice {
    pub fn new(text1: &'static str, text2: &'static str, icon: &'static [u8]) -> Self {
        Self { text1, text2, icon }
    }
}

impl Choice for MenuChoice {
    fn paint_center(&self, _area: Rect, _inverse: bool) {
        display::icon(
            screen().center() + Offset::y(-20),
            self.icon,
            BLD_FG,
            BLD_BG,
        );
        display::text_center(
            screen().center() + Offset::y(0),
            self.text1,
            Font::NORMAL,
            BLD_FG,
            BLD_BG,
        );
        display::text_center(
            screen().center() + Offset::y(10),
            self.text2,
            Font::NORMAL,
            BLD_FG,
            BLD_BG,
        );
    }
}

pub struct MenuChoiceFactory;

impl MenuChoiceFactory {
    const CHOICES: [(&'static str, &'static str, &'static [u8]); CHOICE_LENGTH] = [
        ("WIPE", "DEVICE", ICON_BIN.0),
        ("REBOOT", "TREZOR", ICON_BIN.0),
        ("EXIT", "MENU", ICON_BIN.0),
    ];

    pub fn new() -> Self {
        Self {}
    }
}

impl ChoiceFactory for MenuChoiceFactory {
    type Item = MenuChoice;

    fn count(&self) -> u8 {
        CHOICE_LENGTH as u8
    }

    fn get(&self, choice_index: u8) -> MenuChoice {
        MenuChoice::new(
            MenuChoiceFactory::CHOICES[choice_index as usize].0,
            MenuChoiceFactory::CHOICES[choice_index as usize].1,
            MenuChoiceFactory::CHOICES[choice_index as usize].2,
        )
    }
}

pub struct Menu {
    pg: Child<ChoicePage<MenuChoiceFactory>>,
}

impl Menu {
    pub fn new() -> Self {
        let choices = MenuChoiceFactory::new();
        Self {
            pg: ChoicePage::new(choices)
                .with_carousel(true)
                .with_only_one_item(true)
                .into_child(),
        }
    }
}

impl Component for Menu {
    type Msg = MenuMsg;

    fn place(&mut self, bounds: Rect) -> Rect {
        self.pg.place(bounds);
        bounds
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        match self.pg.event(ctx, event) {
            Some(ChoicePageMsg::Choice(0)) => Some(MenuMsg::FactoryReset),
            Some(ChoicePageMsg::Choice(1)) => Some(MenuMsg::Reboot),
            Some(ChoicePageMsg::Choice(2)) => Some(MenuMsg::Close),
            _ => None,
        }
    }

    fn paint(&mut self) {
        self.pg.paint();
    }

    fn bounds(&self, sink: &mut dyn FnMut(Rect)) {
        self.pg.bounds(sink)
    }
}
