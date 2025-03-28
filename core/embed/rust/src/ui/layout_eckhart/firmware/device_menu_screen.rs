use crate::{
    strutil::TString,
    ui::{
        component::{
            base::AttachType,
            text::paragraphs::{Paragraph, Paragraphs},
            Component, Event, EventCtx,
        },
        geometry::Rect,
        layout_eckhart::{
            component::Button,
            constant::SCREEN,
            firmware::{
                Header, HeaderMsg, TextScreen, TextScreenMsg, VerticalMenu, VerticalMenuScreen,
                VerticalMenuScreenMsg, MENU_MAX_ITEMS,
            },
        },
        shape::Renderer,
    },
};

use super::theme;
use heapless::Vec;

const MAX_DEPTH: usize = 5;
const MAX_SUBMENUS: usize = 10;

#[derive(Clone, Debug)]
enum Action {
    // Go to another registered child screen
    GoTo(usize),

    // Return a DeviceMenuMsg to the caller
    Return(DeviceMenuMsg),
}

struct SubmenuScreen {
    pub screen: VerticalMenuScreen,

    // actions for the menu items in the VerticalMenuScreen, in order
    pub actions: Vec<Option<Action>, MENU_MAX_ITEMS>,
}

enum Subscreen {
    Submenu(SubmenuScreen),
    AboutScreen,
}

#[derive(Copy, Clone, Debug)]
pub enum DeviceMenuMsg {
    NotImplemented,

    // Root menu
    BackupFailed,

    // "Pair & Connect"
    PairNewDevice,

    // Security menu
    CheckBackup,
    WipeDevice,

    // Device menu
    ScreenBrightness,

    Close,
}

pub struct DeviceMenuScreen<'a> {
    bounds: Rect,

    about_screen: TextScreen<Paragraphs<[Paragraph<'a>; 2]>>,

    // all the subscreens in the DeviceMenuScreen
    // which can be either VerticalMenuScreens with associated Actions
    // or some predefined TextScreens, such as "About"
    subscreens: Vec<Subscreen, MAX_SUBMENUS>,

    // the index of the current subscreen in the list of subscreens
    active_subscreen: usize,

    // stack of parents that led to the current subscreen
    parent_subscreens: Vec<usize, MAX_DEPTH>,
}

impl<'a> DeviceMenuScreen<'a> {
    pub fn new(
        failed_backup: bool,
        battery_percentage: usize,
        paired_devices: Vec<TString<'static>, 10>,
    ) -> Self {
        let about_content = Paragraphs::new([
            Paragraph::new(&theme::firmware::TEXT_REGULAR, "Firmware version"),
            Paragraph::new(&theme::firmware::TEXT_REGULAR, "2.3.1"), // TODO
        ]);

        let about_screen = TextScreen::new(about_content)
            .with_header(Header::new("About".into()).with_close_button());

        let mut screen = Self {
            bounds: Rect::zero(),
            about_screen,
            active_subscreen: 0,
            subscreens: Vec::new(),
            parent_subscreens: Vec::new(),
        };

        let about = screen.add_subscreen(Subscreen::AboutScreen);
        let security = screen.add_security_menu();
        let device = screen.add_device_menu("My device".into(), about); // TODO: device name
        let settings = screen.add_settings_menu(security, device);

        let mut paired_device_indices: Vec<usize, 10> = Vec::new();
        for device in &paired_devices {
            unwrap!(paired_device_indices.push(screen.add_paired_device_menu(*device)));
        }

        let devices = screen.add_paired_devices_menu(paired_devices, paired_device_indices);
        let pair_and_connect = screen.add_pair_and_connect_menu(devices);

        let root = screen.add_root_menu(
            failed_backup,
            battery_percentage,
            pair_and_connect,
            settings,
        );

        screen.set_active_subscreen(root);

        screen
    }

    fn add_paired_device_menu(&mut self, device: TString<'static>) -> usize {
        let mut actions: Vec<Option<Action>, MENU_MAX_ITEMS> = Vec::new();
        let mut menu = VerticalMenu::empty().with_separators();
        menu = menu.item(Button::new_menu_item(
            device.into(),
            None,
            theme::menu_item_title(),
        ));
        unwrap!(actions.push(None));

        let screen = VerticalMenuScreen::new(menu).with_header(
            Header::new("Manage".into())
                .with_left_button(Button::with_icon(theme::ICON_CHEVRON_LEFT), HeaderMsg::Back),
        );

        self.add_subscreen(Subscreen::Submenu(SubmenuScreen { screen, actions }))
    }

    fn add_paired_devices_menu(
        &mut self,
        paired_devices: Vec<TString<'static>, 10>,
        paired_device_indices: Vec<usize, 10>,
    ) -> usize {
        let mut actions: Vec<Option<Action>, MENU_MAX_ITEMS> = Vec::new();
        let mut menu = VerticalMenu::empty().with_separators();
        for (device, idx) in paired_devices.iter().zip(paired_device_indices) {
            menu = menu.item(Button::new_menu_item(
                (*device).into(),
                None,
                theme::menu_item_title(),
            ));
            unwrap!(actions.push(Some(Action::GoTo(idx))));
        }

        let screen = VerticalMenuScreen::new(menu).with_header(
            Header::new("Manage paired devices".into())
                .with_right_button(Button::with_icon(theme::ICON_CROSS), HeaderMsg::Cancelled)
                .with_left_button(Button::with_icon(theme::ICON_CHEVRON_LEFT), HeaderMsg::Back),
        );

        self.add_subscreen(Subscreen::Submenu(SubmenuScreen { screen, actions }))
    }

    fn add_pair_and_connect_menu(&mut self, manage_devices_index: usize) -> usize {
        let mut actions: Vec<Option<Action>, MENU_MAX_ITEMS> = Vec::new();
        let mut menu = VerticalMenu::empty().with_separators();
        menu = menu.item(
            Button::new_menu_item(
                "Manage paired devices".into(),
                Some("1 device connected".into()), // TODO
                theme::menu_item_title(),
            )
            .subtext_green(),
        );
        unwrap!(actions.push(Some(Action::GoTo(manage_devices_index))));
        menu = menu.item(Button::new_menu_item(
            "Pair new device".into(),
            None,
            theme::menu_item_title(),
        ));
        unwrap!(actions.push(Some(Action::Return(DeviceMenuMsg::PairNewDevice))));

        let screen = VerticalMenuScreen::new(menu).with_header(
            Header::new("Pair & Connect".into())
                .with_right_button(Button::with_icon(theme::ICON_CROSS), HeaderMsg::Cancelled)
                .with_left_button(Button::with_icon(theme::ICON_CHEVRON_LEFT), HeaderMsg::Back),
        );

        self.add_subscreen(Subscreen::Submenu(SubmenuScreen { screen, actions }))
    }

    fn add_settings_menu(&mut self, security_index: usize, device_index: usize) -> usize {
        let mut actions: Vec<Option<Action>, MENU_MAX_ITEMS> = Vec::new();
        let mut menu = VerticalMenu::empty().with_separators();
        menu = menu.item(Button::new_menu_item(
            "Security".into(),
            None,
            theme::menu_item_title(),
        ));
        unwrap!(actions.push(Some(Action::GoTo(security_index))));
        menu = menu.item(Button::new_menu_item(
            "Device".into(),
            None,
            theme::menu_item_title(),
        ));
        unwrap!(actions.push(Some(Action::GoTo(device_index))));

        let screen = VerticalMenuScreen::new(menu).with_header(
            Header::new("Settings".into())
                .with_right_button(Button::with_icon(theme::ICON_CROSS), HeaderMsg::Cancelled)
                .with_left_button(Button::with_icon(theme::ICON_CHEVRON_LEFT), HeaderMsg::Back),
        );

        self.add_subscreen(Subscreen::Submenu(SubmenuScreen { screen, actions }))
    }

    fn add_security_menu(&mut self) -> usize {
        let mut actions: Vec<Option<Action>, MENU_MAX_ITEMS> = Vec::new();
        let mut menu = VerticalMenu::empty().with_separators();
        menu = menu.item(Button::new_menu_item(
            "Check backup".into(),
            None,
            theme::menu_item_title(),
        ));
        unwrap!(actions.push(Some(Action::Return(DeviceMenuMsg::CheckBackup))));
        menu = menu.item(Button::new_menu_item(
            "Wipe device".into(),
            None,
            theme::menu_item_title(),
        ));
        unwrap!(actions.push(Some(Action::Return(DeviceMenuMsg::WipeDevice))));

        let screen = VerticalMenuScreen::new(menu).with_header(
            Header::new("Security".into())
                .with_right_button(Button::with_icon(theme::ICON_CROSS), HeaderMsg::Cancelled)
                .with_left_button(Button::with_icon(theme::ICON_CHEVRON_LEFT), HeaderMsg::Back),
        );

        self.add_subscreen(Subscreen::Submenu(SubmenuScreen { screen, actions }))
    }

    fn add_device_menu(&mut self, device_name: TString<'static>, about_index: usize) -> usize {
        let mut actions: Vec<Option<Action>, MENU_MAX_ITEMS> = Vec::new();
        let mut menu = VerticalMenu::empty().with_separators();
        menu = menu.item(Button::new_menu_item(
            "Name".into(),
            Some(device_name),
            theme::menu_item_title(),
        ));
        unwrap!(actions.push(None));
        menu = menu.item(Button::new_menu_item(
            "Screen brightness".into(),
            None,
            theme::menu_item_title(),
        ));
        unwrap!(actions.push(Some(Action::Return(DeviceMenuMsg::ScreenBrightness))));
        menu = menu.item(Button::new_menu_item(
            "About".into(),
            None,
            theme::menu_item_title(),
        ));
        unwrap!(actions.push(Some(Action::GoTo(about_index))));

        let screen = VerticalMenuScreen::new(menu).with_header(
            Header::new("Security".into())
                .with_right_button(Button::with_icon(theme::ICON_CROSS), HeaderMsg::Cancelled)
                .with_left_button(Button::with_icon(theme::ICON_CHEVRON_LEFT), HeaderMsg::Back),
        );

        self.add_subscreen(Subscreen::Submenu(SubmenuScreen { screen, actions }))
    }

    fn add_root_menu(
        &mut self,
        failed_backup: bool,
        battery_percentage: usize,
        pair_and_connect_index: usize,
        settings_index: usize,
    ) -> usize {
        let mut actions: Vec<Option<Action>, MENU_MAX_ITEMS> = Vec::new();
        let mut menu = VerticalMenu::empty().with_separators();
        if failed_backup {
            menu = menu.item(Button::new_menu_item(
                "Backup failed".into(),
                Some("Review".into()),
                theme::menu_item_title_red(),
            ));
            unwrap!(actions.push(Some(Action::Return(DeviceMenuMsg::BackupFailed))));
        }

        menu = menu.item(
            Button::new_menu_item(
                "Pair & connect".into(),
                Some("1 device connected".into()), // TODO
                theme::menu_item_title(),
            )
            .subtext_green(),
        );
        unwrap!(actions.push(Some(Action::GoTo(pair_and_connect_index))));

        menu = menu.item(Button::new_menu_item(
            "Settings".into(),
            None,
            theme::menu_item_title(),
        ));
        unwrap!(actions.push(Some(Action::GoTo(settings_index))));

        let screen = VerticalMenuScreen::new(menu).with_header(
            Header::new("".into())
                .with_battery(battery_percentage)
                .with_right_button(Button::with_icon(theme::ICON_CROSS), HeaderMsg::Cancelled),
        );

        self.add_subscreen(Subscreen::Submenu(SubmenuScreen { screen, actions }))
    }

    fn add_subscreen(&mut self, screen: Subscreen) -> usize {
        unwrap!(self.subscreens.push(screen));
        self.subscreens.len() - 1
    }

    fn set_active_subscreen(&mut self, idx: usize) {
        assert!(idx < self.subscreens.len());
        self.active_subscreen = idx;
    }

    fn handle_submenu(&mut self, ctx: &mut EventCtx, idx: usize) -> Option<DeviceMenuMsg> {
        match self.subscreens[self.active_subscreen] {
            Subscreen::Submenu(ref mut menu_screen) => {
                match menu_screen.actions[idx] {
                    Some(Action::GoTo(menu)) => {
                        menu_screen.screen.update_menu(ctx);
                        unwrap!(self.parent_subscreens.push(self.active_subscreen));
                        self.active_subscreen = menu;
                        self.place(self.bounds);
                    }
                    Some(Action::Return(msg)) => return Some(msg),
                    None => {}
                };
            }
            _ => {
                assert!(false, "Expected a submenu!");
            }
        }

        None
    }

    fn go_back(&mut self) -> Option<DeviceMenuMsg> {
        if let Some(parent) = self.parent_subscreens.pop() {
            self.active_subscreen = parent;
            self.place(self.bounds);
            None
        } else {
            Some(DeviceMenuMsg::Close)
        }
    }
}

impl<'a> Component for DeviceMenuScreen<'a> {
    type Msg = DeviceMenuMsg;

    fn place(&mut self, bounds: Rect) -> Rect {
        // assert full screen
        debug_assert_eq!(bounds.height(), SCREEN.height());
        debug_assert_eq!(bounds.width(), SCREEN.width());

        self.bounds = bounds;

        match self.subscreens[self.active_subscreen] {
            Subscreen::Submenu(ref mut menu_screen) => menu_screen.screen.place(bounds),
            Subscreen::AboutScreen => self.about_screen.place(bounds),
        };

        bounds
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        // Update the menu when the screen is attached
        if let Event::Attach(AttachType::Initial) = event {}

        // Handle the event for the active menu
        match self.subscreens[self.active_subscreen] {
            Subscreen::Submenu(ref mut menu_screen) => match menu_screen.screen.event(ctx, event) {
                Some(VerticalMenuScreenMsg::Selected(index)) => {
                    return self.handle_submenu(ctx, index);
                }
                Some(VerticalMenuScreenMsg::Back) => {
                    return self.go_back();
                }
                Some(VerticalMenuScreenMsg::Close) => {
                    return Some(DeviceMenuMsg::Close);
                }
                _ => {}
            },
            Subscreen::AboutScreen => match self.about_screen.event(ctx, event) {
                Some(TextScreenMsg::Cancelled) => {
                    return self.go_back();
                }
                _ => {}
            },
        }

        None
    }

    fn render<'s>(&'s self, target: &mut impl Renderer<'s>) {
        match &self.subscreens[self.active_subscreen] {
            Subscreen::Submenu(ref menu_screen) => menu_screen.screen.render(target),
            Subscreen::AboutScreen => self.about_screen.render(target),
        }
    }
}

#[cfg(feature = "ui_debug")]
impl<'a> crate::trace::Trace for DeviceMenuScreen<'a> {
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.component("DeviceMenuScreen");
    }
}
