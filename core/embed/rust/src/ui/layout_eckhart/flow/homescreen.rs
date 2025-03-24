use crate::{
    error,
    strutil::TString,
    ui::{
        component::{
            text::paragraphs::{Paragraph, Paragraphs},
            ComponentExt as _,
        },
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
        Header, HeaderMsg, Homescreen, HomescreenMsg, TextScreen, TextScreenMsg, VerticalMenu,
        VerticalMenuScreen, VerticalMenuScreenMsg,
    },
    theme,
};

#[derive(Copy, Clone, PartialEq, Eq)]
pub enum HomeFlow {
    Homescreen,
    DeviceMenu,
    PairAndConnectMenu,
    ManagePairedDevicesMenu,
    PairNewDevice,
    SettingsMenu,
}

mod DeviceMenu {
    pub const PairAndConnect: usize = 0;
    pub const Settings: usize = 1;
}

mod PairAndConnectMenu {
    pub const ManagePairedDevices: usize = 0;
    pub const PairNewDevice: usize = 1;
}

impl FlowController for HomeFlow {
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
            (Self::DeviceMenu, FlowMsg::Choice(DeviceMenu::PairAndConnect)) => {
                Self::PairAndConnectMenu.goto()
            }
            (Self::DeviceMenu, FlowMsg::Choice(DeviceMenu::Settings)) => Self::SettingsMenu.goto(),
            (Self::PairAndConnectMenu, FlowMsg::Cancelled) => Self::Homescreen.goto(),
            (Self::PairAndConnectMenu, FlowMsg::Previous) => Self::DeviceMenu.goto(),
            (
                Self::PairAndConnectMenu,
                FlowMsg::Choice(PairAndConnectMenu::ManagePairedDevices),
            ) => Self::ManagePairedDevicesMenu.goto(),
            (Self::PairAndConnectMenu, FlowMsg::Choice(PairAndConnectMenu::PairNewDevice)) => {
                Self::PairNewDevice.goto()
            }
            (Self::ManagePairedDevicesMenu, FlowMsg::Cancelled) => Self::Homescreen.goto(),
            (Self::ManagePairedDevicesMenu, FlowMsg::Previous) => Self::PairAndConnectMenu.goto(),
            (Self::DeviceMenu, FlowMsg::Choice(DeviceMenu::Settings)) => Self::SettingsMenu.goto(),
            (Self::PairNewDevice, FlowMsg::Previous) => Self::PairAndConnectMenu.goto(),
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

    let device_menu_page = VerticalMenuScreen::new(
        VerticalMenu::empty()
            .item(Button::with_text("Pair & Connect".into()))
            .item(Button::with_text("Settings".into())),
    )
    .with_header(Header::new("Device menu".into()).with_close_button())
    .map(|msg| match msg {
        VerticalMenuScreenMsg::Selected(DeviceMenu::PairAndConnect) => {
            Some(FlowMsg::Choice(DeviceMenu::PairAndConnect))
        }
        VerticalMenuScreenMsg::Selected(DeviceMenu::Settings) => {
            Some(FlowMsg::Choice(DeviceMenu::Settings))
        }
        VerticalMenuScreenMsg::Close => Some(FlowMsg::Cancelled),
        _ => None,
    });

    let pair_and_connect_menu_page = VerticalMenuScreen::new(
        VerticalMenu::empty()
            .item(Button::with_text("Manage paired devices".into()))
            .item(Button::with_text("Pair new device".into())),
    )
    .with_header(
        Header::new("Pair & Connect".into())
            .with_back_button()
            .with_close_button(),
    )
    .map(|msg| match msg {
        VerticalMenuScreenMsg::Back => Some(FlowMsg::Previous),
        VerticalMenuScreenMsg::Selected(PairAndConnectMenu::ManagePairedDevices) => {
            Some(FlowMsg::Choice(PairAndConnectMenu::ManagePairedDevices))
        }
        VerticalMenuScreenMsg::Selected(PairAndConnectMenu::PairNewDevice) => {
            Some(FlowMsg::Choice(PairAndConnectMenu::PairNewDevice))
        }
        VerticalMenuScreenMsg::Close => Some(FlowMsg::Cancelled),
        _ => None,
    });

    let manage_paired_devices_menu_page = VerticalMenuScreen::new(
        VerticalMenu::empty()
            // TODO
            .item(Button::with_text(
                "Mobile Suite on Todd's iPhone / Connected".into(),
            ))
            .item(Button::with_text("Suite on PC / Disconnected".into())),
    )
    .with_header(
        Header::new("Manage paired devices".into())
            .with_back_button()
            .with_close_button(),
    )
    .map(|msg| match msg {
        VerticalMenuScreenMsg::Back => Some(FlowMsg::Previous),
        VerticalMenuScreenMsg::Selected(n) => Some(FlowMsg::Choice(n)), // assert n is in the range (# of devices)
        VerticalMenuScreenMsg::Close => Some(FlowMsg::Cancelled),
        _ => None,
    });

    let content = Paragraphs::new(Paragraph::new(&theme::firmware::TEXT_REGULAR, "HELLO"));
    let pair_new_device = TextScreen::new(content)
        .with_header(Header::new("Pair with new device".into()).with_close_button())
        .map(|msg| match msg {
            TextScreenMsg::Cancelled => Some(FlowMsg::Previous),
            _ => None,
        });

    let mut res = SwipeFlow::new(&HomeFlow::Homescreen)?;
    res.add_page(&HomeFlow::Homescreen, content_homescreen)?
        .add_page(&HomeFlow::DeviceMenu, device_menu_page)?
        .add_page(&HomeFlow::PairAndConnectMenu, pair_and_connect_menu_page)?
        .add_page(
            &HomeFlow::ManagePairedDevicesMenu,
            manage_paired_devices_menu_page,
        )?
        .add_page(&HomeFlow::PairNewDevice, pair_new_device)?;

    Ok(res)
}
