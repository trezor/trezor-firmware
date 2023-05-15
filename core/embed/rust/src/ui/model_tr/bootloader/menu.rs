#[cfg(feature = "ui_debug")]
use crate::trace::{Trace, Tracer};
use crate::ui::{
    component::{Child, Component, ComponentExt, Event, EventCtx, Pad},
    constant::screen,
    display,
    display::{Font, Icon},
    geometry::{Offset, Rect, CENTER},
    model_tr::{
        bootloader::{
            theme::{BLD_BG, BLD_FG, ICON_EXIT, ICON_REDO, ICON_TRASH},
            ReturnToC,
        },
        component::{Choice, ChoiceFactory, ChoicePage, ChoicePageMsg},
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

impl Choice<&'static str> for MenuChoice {
    fn paint_center(&self, _area: Rect, _inverse: bool) {
        Icon::new(self.icon).draw(screen().center() + Offset::y(-20), CENTER, BLD_FG, BLD_BG);

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

#[cfg(feature = "ui_debug")]
impl Trace for MenuChoice {
    fn trace(&self, t: &mut dyn Tracer) {
        t.open("MenuChoice");
        t.close();
    }
}

pub struct MenuChoiceFactory;

impl MenuChoiceFactory {
    const CHOICES: [(&'static str, &'static str, &'static [u8]); CHOICE_LENGTH] = [
        ("Factory", "reset", ICON_TRASH),
        ("Reboot", "Trezor", ICON_REDO),
        ("Exit", "menu", ICON_EXIT),
    ];

    pub fn new() -> Self {
        Self {}
    }
}

impl ChoiceFactory<&'static str> for MenuChoiceFactory {
    type Item = MenuChoice;

    fn count(&self) -> usize {
        CHOICE_LENGTH
    }

    fn get(&self, choice_index: usize) -> MenuChoice {
        MenuChoice::new(
            MenuChoiceFactory::CHOICES[choice_index].0,
            MenuChoiceFactory::CHOICES[choice_index].1,
            MenuChoiceFactory::CHOICES[choice_index].2,
        )
    }
}

pub struct Menu {
    bg: Pad,
    pg: Child<ChoicePage<MenuChoiceFactory, &'static str>>,
}

impl Menu {
    pub fn new() -> Self {
        let choices = MenuChoiceFactory::new();
        Self {
            bg: Pad::with_background(BLD_BG).with_clear(),
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

    #[cfg(feature = "ui_bounds")]
    fn bounds(&self, sink: &mut dyn FnMut(Rect)) {
        self.pg.bounds(sink)
    }
}
