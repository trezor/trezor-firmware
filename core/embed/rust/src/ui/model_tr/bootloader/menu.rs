#[cfg(feature = "ui_debug")]
use crate::trace::{Trace, Tracer};
use crate::ui::{
    component::{Child, Component, Event, EventCtx, Pad},
    constant::screen,
    display,
    display::{Font, Icon},
    geometry::{Alignment2D, Offset, Point, Rect},
};

use super::{
    super::component::{Choice, ChoiceFactory, ChoicePage},
    theme::{BLD_BG, BLD_FG, ICON_EXIT, ICON_REDO, ICON_TRASH},
    ReturnToC,
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
const SCREEN_CENTER: Point = screen().center();

pub struct MenuChoice {
    first_line: &'static str,
    second_line: &'static str,
    icon: Icon,
}

impl MenuChoice {
    pub fn new(first_line: &'static str, second_line: &'static str, icon: Icon) -> Self {
        Self {
            first_line,
            second_line,
            icon,
        }
    }
}

impl Choice<&'static str> for MenuChoice {
    fn paint_center(&self, _area: Rect, _inverse: bool) {
        // Icon on top and two lines of text below
        self.icon.draw(
            SCREEN_CENTER + Offset::y(-20),
            Alignment2D::CENTER,
            BLD_FG,
            BLD_BG,
        );

        display::text_center(SCREEN_CENTER, self.first_line, Font::NORMAL, BLD_FG, BLD_BG);
        display::text_center(
            SCREEN_CENTER + Offset::y(10),
            self.second_line,
            Font::NORMAL,
            BLD_FG,
            BLD_BG,
        );
    }
}

#[cfg(feature = "ui_debug")]
impl Trace for MenuChoice {
    fn trace(&self, t: &mut dyn Tracer) {
        t.component("MenuChoice");
    }
}

pub struct MenuChoiceFactory;

impl MenuChoiceFactory {
    const CHOICES: [(&'static str, &'static str, Icon); CHOICE_LENGTH] = [
        ("Factory", "reset", ICON_TRASH),
        ("Reboot", "Trezor", ICON_REDO),
        ("Exit", "menu", ICON_EXIT),
    ];

    pub fn new() -> Self {
        Self {}
    }
}

impl ChoiceFactory<&'static str> for MenuChoiceFactory {
    type Action = MenuMsg;
    type Item = MenuChoice;

    fn count(&self) -> usize {
        CHOICE_LENGTH
    }

    fn get(&self, choice_index: usize) -> (Self::Item, Self::Action) {
        let choice_item = MenuChoice::new(
            Self::CHOICES[choice_index].0,
            Self::CHOICES[choice_index].1,
            Self::CHOICES[choice_index].2,
        );
        let action = match choice_index {
            0 => MenuMsg::FactoryReset,
            1 => MenuMsg::Reboot,
            2 => MenuMsg::Close,
            _ => unreachable!(),
        };
        (choice_item, action)
    }
}

pub struct Menu {
    pad: Pad,
    choice_page: Child<ChoicePage<MenuChoiceFactory, &'static str, MenuMsg>>,
}

impl Menu {
    pub fn new() -> Self {
        let choices = MenuChoiceFactory::new();
        Self {
            pad: Pad::with_background(BLD_BG).with_clear(),
            choice_page: Child::new(
                ChoicePage::new(choices)
                    .with_carousel(true)
                    .with_only_one_item(true),
            ),
        }
    }
}

impl Component for Menu {
    type Msg = MenuMsg;

    fn place(&mut self, bounds: Rect) -> Rect {
        self.pad.place(bounds);
        self.choice_page.place(bounds);
        bounds
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        self.choice_page.event(ctx, event).map(|evt| evt.0)
    }

    fn paint(&mut self) {
        self.pad.paint();
        self.choice_page.paint();
    }

    #[cfg(feature = "ui_bounds")]
    fn bounds(&self, sink: &mut dyn FnMut(Rect)) {
        self.choice_page.bounds(sink)
    }
}
