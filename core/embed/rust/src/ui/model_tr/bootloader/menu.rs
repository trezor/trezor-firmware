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
        component::{ChoiceFactory, ChoicePage, ChoicePageMsg},
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
    fn get(&self, choice_index: u8) -> (&'static str, &'static str, &'static [u8]) {
        MenuChoiceFactory::CHOICES[choice_index as usize]
    }
}

impl ChoiceFactory for MenuChoiceFactory {
    fn count(&self) -> u8 {
        CHOICE_LENGTH as u8
    }

    fn paint_center(&self, choice_index: u8, _area: Rect, _inverse: bool) {
        let content = self.get(choice_index);

        let text_1 = content.0;
        let text_2 = content.1;
        let icon = content.2;

        display::icon(screen().center() + Offset::y(-20), icon, BLD_FG, BLD_BG);
        display::text_center(
            screen().center() + Offset::y(0),
            text_1,
            Font::NORMAL,
            BLD_FG,
            BLD_BG,
        );
        display::text_center(
            screen().center() + Offset::y(10),
            text_2,
            Font::NORMAL,
            BLD_FG,
            BLD_BG,
        );
    }

    #[cfg(feature = "ui_debug")]
    fn trace(&self, t: &mut dyn Tracer, name: &str, choice_index: u8) {
        t.field(name, &self.get(choice_index));
    }
}

pub struct Menu {
    bg: Pad,
    pg: Child<ChoicePage<MenuChoiceFactory>>,
}

impl Menu {
    pub fn new() -> Self {
        let choices = MenuChoiceFactory::new();
        let mut instance = Self {
            bg: Pad::with_background(BLD_BG),
            pg: ChoicePage::new(choices).with_carousel(true).into_child(),
        };
        instance.bg.clear();
        instance
    }
}

impl Component for Menu {
    type Msg = MenuMsg;

    fn place(&mut self, bounds: Rect) -> Rect {
        self.bg.place(bounds);
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
        self.bg.paint();
        self.pg.paint();
    }

    fn bounds(&self, sink: &mut dyn FnMut(Rect)) {
        self.pg.bounds(sink)
    }
}
