use crate::{
    error,
    strutil::TString,
    ui::{
        component::ComponentExt as _,
        flow::{
            base::{Decision, DecisionBuilder as _},
            FlowController, FlowMsg, SwipeFlow,
        },
        geometry::Direction,
    },
};

use super::super::{
    component::Button,
    firmware::{
        Header, Homescreen, HomescreenMsg, VerticalMenu, VerticalMenuScreen, VerticalMenuScreenMsg,
    },
};

#[derive(Copy, Clone, PartialEq, Eq)]
pub enum Home {
    Homescreen,
    DeviceMenu,
}

impl FlowController for Home {
    #[inline]
    fn index(&'static self) -> usize {
        *self as usize
    }

    fn handle_swipe(&'static self, _direction: Direction) -> Decision {
        self.do_nothing()
    }

    fn handle_event(&'static self, msg: FlowMsg) -> Decision {
        match (self, msg) {
            (Self::Homescreen, FlowMsg::Cancelled) => self.return_msg(FlowMsg::Cancelled),
            (Self::Homescreen, FlowMsg::Info) => Self::DeviceMenu.goto(),
            (Self::DeviceMenu, FlowMsg::Cancelled) => Self::Homescreen.goto(),
            _ => self.do_nothing(),
        }
    }
}

pub fn new_home(
    label: TString<'static>,
    lockable: bool,
    locked: bool,
    bootscreen: bool,
    coinjoin_authorized: bool,
    notification: Option<(TString<'static>, u8)>,
) -> Result<SwipeFlow, error::Error> {
    let content_homescreen = Homescreen::new(
        label,
        lockable,
        locked,
        bootscreen,
        coinjoin_authorized,
        notification,
    )?
    .map(|msg| match msg {
        HomescreenMsg::Dismissed => Some(FlowMsg::Cancelled),
        HomescreenMsg::Menu => Some(FlowMsg::Info),
    });

    let menu = VerticalMenu::empty()
        .item(Button::with_text("Bluetooth management".into()))
        .item(Button::with_text("Device".into()))
        .item(Button::with_text("Check backup".into()))
        .item(Button::with_text("About".into()));
    let content_device_menu = VerticalMenuScreen::new(menu)
        .with_header(Header::new("Device menu".into()).with_close_button())
        .map(|msg| match msg {
            VerticalMenuScreenMsg::Selected(n) => Some(FlowMsg::Choice(n)),
            VerticalMenuScreenMsg::Close => Some(FlowMsg::Cancelled),
            _ => None,
        });

    let mut res = SwipeFlow::new(&Home::Homescreen)?;
    res.add_page(&Home::Homescreen, content_homescreen)?
        .add_page(&Home::DeviceMenu, content_device_menu)?;
    Ok(res)
}
