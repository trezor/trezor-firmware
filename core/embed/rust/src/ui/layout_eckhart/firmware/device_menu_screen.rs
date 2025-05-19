use core::ops::{Deref, DerefMut};

use crate::{
    error::Error,
    micropython::gc::GcBox,
    strutil::TString,
    ui::{
        component::{
            text::{
                paragraphs::{Paragraph, Paragraphs},
                TextStyle,
            },
            Component, Event, EventCtx,
        },
        geometry::Rect,
        layout_eckhart::{
            component::{Button, ButtonStyleSheet},
            constant::SCREEN,
            firmware::{
                Header, HeaderMsg, TextScreen, TextScreenMsg, VerticalMenu, VerticalMenuScreen,
                VerticalMenuScreenMsg, SHORT_MENU_ITEMS,
            },
        },
        shape::Renderer,
    },
};

use super::{theme, ShortMenuVec};
use heapless::Vec;

const MAX_DEPTH: usize = 3;
const MAX_SUBSCREENS: usize = 8;
const MAX_SUBMENUS: usize = MAX_SUBSCREENS - 2 /* (about and device screen) */;

const DISCONNECT_DEVICE_MENU_INDEX: usize = 1;

#[derive(Clone)]
enum Action {
    // Go to another registered subscreen
    GoTo(usize),

    // Return a DeviceMenuMsg to the caller
    Return(DeviceMenuMsg),
}

#[derive(Copy, Clone)]
pub enum DeviceMenuMsg {
    // Root menu
    BackupFailed,

    // "Pair & Connect"
    DevicePair, // pair a new device
    DeviceDisconnect(
        usize, /* which device to disconnect, index in the list of devices */
    ),

    // Security menu
    CheckBackup,
    WipeDevice,

    // Device menu
    ScreenBrightness,

    // nothing selected
    Close,
}

struct MenuItem {
    text: TString<'static>,
    subtext: Option<(TString<'static>, Option<TextStyle>)>,
    stylesheet: ButtonStyleSheet,
    action: Option<Action>,
}

impl MenuItem {
    pub fn new(text: TString<'static>, action: Option<Action>) -> Self {
        Self {
            text,
            subtext: None,
            stylesheet: theme::menu_item_title(),
            action,
        }
    }

    pub fn with_subtext(mut self, subtext: Option<(TString<'static>, Option<TextStyle>)>) -> Self {
        self.subtext = subtext;
        self
    }

    pub fn with_stylesheet(mut self, stylesheet: ButtonStyleSheet) -> Self {
        self.stylesheet = stylesheet;
        self
    }
}

struct Submenu {
    header_text: TString<'static>,
    show_battery: bool,
    items: Vec<MenuItem, SHORT_MENU_ITEMS>,
}

impl Submenu {
    pub fn new(header_text: TString<'static>, items: Vec<MenuItem, SHORT_MENU_ITEMS>) -> Self {
        Self {
            header_text,
            show_battery: false,
            items,
        }
    }

    pub fn with_battery(mut self) -> Self {
        self.show_battery = true;
        self
    }
}

// Each subscreen of the DeviceMenuScreen is one of these
enum Subscreen {
    // A registered submenu
    Submenu(usize),

    // A screen allowing the user to to disconnect a device
    DeviceScreen(
        TString<'static>, /* device name */
        usize,            /* index in the list of devices */
    ),

    // The about screen
    AboutScreen,
}

// Used to preallocate memory for the largest enum variant
#[allow(clippy::large_enum_variant)]
enum ActiveScreen<'a> {
    Menu(VerticalMenuScreen<ShortMenuVec>),
    About(TextScreen<Paragraphs<[Paragraph<'a>; 2]>>),

    // used only during `DeviceMenuScreen::new`
    Empty,
}

pub struct DeviceMenuScreen<'a> {
    bounds: Rect,

    battery_percentage: u8,
    firmware_version: TString<'static>,

    // These correspond to the currently active subscreen,
    // which is one of the possible kinds of subscreens
    // as defined by `enum Subscreen` (DeviceScreen is still a VerticalMenuScreen!)
    // This way we only need to keep one screen at any time in memory.
    active_screen: GcBox<ActiveScreen<'a>>,

    // Information needed to construct any subscreen on demand
    submenus: GcBox<Vec<Submenu, MAX_SUBMENUS>>,
    subscreens: Vec<Subscreen, MAX_SUBSCREENS>,

    // index of the current subscreen in the list of subscreens
    active_subscreen: usize,

    // stack of parents that led to the current subscreen
    parent_subscreens: Vec<usize, MAX_DEPTH>,
}

impl<'a> DeviceMenuScreen<'a> {
    pub fn new(
        failed_backup: bool,
        battery_percentage: u8,
        firmware_version: TString<'static>,
        device_name: TString<'static>,
        // NB: we currently only support one device at a time.
        // if we ever increase this size, we will need a way to return the correct
        // device index on Disconnect back to uPy
        // (see component_msg_obj.rs, which currently just returns "DeviceDisconnect" with no
        // index!)
        paired_devices: Vec<TString<'static>, 1>,
    ) -> Result<Self, Error> {
        let mut screen = Self {
            bounds: Rect::zero(),
            battery_percentage,
            firmware_version,
            active_screen: GcBox::new(ActiveScreen::Empty)?,
            active_subscreen: 0,
            submenus: GcBox::new(Vec::new())?,
            subscreens: Vec::new(),
            parent_subscreens: Vec::new(),
        };

        let about = screen.add_subscreen(Subscreen::AboutScreen);
        let security = screen.add_security_menu();
        let device = screen.add_device_menu(device_name, about);
        let settings = screen.add_settings_menu(security, device);

        let mut paired_device_indices: Vec<usize, 1> = Vec::new();
        for (i, device) in paired_devices.iter().enumerate() {
            unwrap!(paired_device_indices
                .push(screen.add_subscreen(Subscreen::DeviceScreen(*device, i))));
        }

        let devices = screen.add_paired_devices_menu(paired_devices, paired_device_indices);
        let pair_and_connect = screen.add_pair_and_connect_menu(devices);

        let root = screen.add_root_menu(failed_backup, pair_and_connect, settings);

        screen.set_active_subscreen(root);

        Ok(screen)
    }

    fn is_low_battery(&self) -> bool {
        self.battery_percentage < 20
    }

    fn add_paired_devices_menu(
        &mut self,
        paired_devices: Vec<TString<'static>, 1>,
        paired_device_indices: Vec<usize, 1>,
    ) -> usize {
        let mut items: Vec<MenuItem, SHORT_MENU_ITEMS> = Vec::new();
        for (device, idx) in paired_devices.iter().zip(paired_device_indices) {
            unwrap!(items.push(
                MenuItem::new(*device, Some(Action::GoTo(idx))).with_subtext(Some((
                    "Connected".into(),
                    Some(Button::SUBTEXT_STYLE_GREEN)
                ))) // TODO: this should be a boolean feature of the device
            ));
        }

        let submenu_index = self.add_submenu(Submenu::new("Manage paired devices".into(), items));
        self.add_subscreen(Subscreen::Submenu(submenu_index))
    }

    fn add_pair_and_connect_menu(&mut self, manage_devices_index: usize) -> usize {
        let mut items: Vec<MenuItem, SHORT_MENU_ITEMS> = Vec::new();
        unwrap!(items.push(
            MenuItem::new(
                "Manage paired devices".into(),
                Some(Action::GoTo(manage_devices_index)),
            )
            .with_subtext(Some((
                "1 device connected".into(),
                Some(Button::SUBTEXT_STYLE_GREEN)
            )))
        ));
        unwrap!(items.push(MenuItem::new(
            "Pair new device".into(),
            Some(Action::Return(DeviceMenuMsg::DevicePair)),
        )));

        let submenu_index = self.add_submenu(Submenu::new("Pair & connect".into(), items));
        self.add_subscreen(Subscreen::Submenu(submenu_index))
    }

    fn add_settings_menu(&mut self, security_index: usize, device_index: usize) -> usize {
        let mut items: Vec<MenuItem, SHORT_MENU_ITEMS> = Vec::new();
        unwrap!(items.push(MenuItem::new(
            "Security".into(),
            Some(Action::GoTo(security_index))
        )));
        unwrap!(items.push(MenuItem::new(
            "Device".into(),
            Some(Action::GoTo(device_index))
        )));

        let submenu_index = self.add_submenu(Submenu::new("Settings".into(), items));
        self.add_subscreen(Subscreen::Submenu(submenu_index))
    }

    fn add_security_menu(&mut self) -> usize {
        let mut items: Vec<MenuItem, SHORT_MENU_ITEMS> = Vec::new();
        unwrap!(items.push(MenuItem::new(
            "Check backup".into(),
            Some(Action::Return(DeviceMenuMsg::CheckBackup)),
        )));
        unwrap!(items.push(MenuItem::new(
            "Wipe device".into(),
            Some(Action::Return(DeviceMenuMsg::WipeDevice))
        )));

        let submenu_index = self.add_submenu(Submenu::new("Security".into(), items));
        self.add_subscreen(Subscreen::Submenu(submenu_index))
    }

    fn add_device_menu(&mut self, device_name: TString<'static>, about_index: usize) -> usize {
        let mut items: Vec<MenuItem, SHORT_MENU_ITEMS> = Vec::new();
        unwrap!(
            items.push(MenuItem::new("Name".into(), None).with_subtext(Some((device_name, None))))
        );
        unwrap!(items.push(MenuItem::new(
            "Screen brightness".into(),
            Some(Action::Return(DeviceMenuMsg::ScreenBrightness)),
        )));
        unwrap!(items.push(MenuItem::new(
            "About".into(),
            Some(Action::GoTo(about_index))
        )));

        let submenu_index = self.add_submenu(Submenu::new("Device".into(), items));
        self.add_subscreen(Subscreen::Submenu(submenu_index))
    }

    fn add_root_menu(
        &mut self,
        failed_backup: bool,
        pair_and_connect_index: usize,
        settings_index: usize,
    ) -> usize {
        let mut items: Vec<MenuItem, SHORT_MENU_ITEMS> = Vec::new();
        if failed_backup {
            unwrap!(items.push(
                MenuItem::new(
                    "Backup failed".into(),
                    Some(Action::Return(DeviceMenuMsg::BackupFailed)),
                )
                .with_subtext(Some(("Review".into(), None)))
                .with_stylesheet(theme::menu_item_title_red()),
            ));
        }
        unwrap!(items.push(
            MenuItem::new(
                "Pair & connect".into(),
                Some(Action::GoTo(pair_and_connect_index)),
            )
            .with_subtext(Some((
                "1 device connected".into(),
                Some(Button::SUBTEXT_STYLE_GREEN)
            )))
        ));
        unwrap!(items.push(MenuItem::new(
            "Settings".into(),
            Some(Action::GoTo(settings_index)),
        )));

        let submenu_index = self.add_submenu(Submenu::new("".into(), items).with_battery());
        self.add_subscreen(Subscreen::Submenu(submenu_index))
    }

    fn add_submenu(&mut self, submenu: Submenu) -> usize {
        unwrap!(self.submenus.push(submenu));
        self.submenus.len() - 1
    }

    fn add_subscreen(&mut self, screen: Subscreen) -> usize {
        unwrap!(self.subscreens.push(screen));
        self.subscreens.len() - 1
    }

    fn set_active_subscreen(&mut self, idx: usize) {
        assert!(idx < self.subscreens.len());
        self.active_subscreen = idx;
        self.build_active_subscreen();
    }

    fn build_active_subscreen(&mut self) {
        match self.subscreens[self.active_subscreen] {
            Subscreen::Submenu(ref mut submenu_index) => {
                let submenu = &self.submenus[*submenu_index];
                let mut menu = VerticalMenu::<ShortMenuVec>::empty().with_separators();
                for item in &submenu.items {
                    let button = if let Some((subtext, subtext_style)) = item.subtext {
                        Button::new_menu_item_with_subtext(
                            item.text,
                            item.stylesheet,
                            subtext,
                            subtext_style,
                        )
                    } else {
                        Button::new_menu_item(item.text, item.stylesheet)
                    };
                    menu.item(button);
                }
                let mut header = Header::new(submenu.header_text).with_close_button();
                if submenu.show_battery {
                    header = header.with_icon(
                        theme::ICON_BATTERY_ZAP,
                        if self.is_low_battery() {
                            theme::YELLOW
                        } else {
                            theme::GREEN_LIME
                        },
                    );
                } else {
                    header = header.with_left_button(
                        Button::with_icon(theme::ICON_CHEVRON_LEFT),
                        HeaderMsg::Back,
                    );
                }
                *self.active_screen.deref_mut() =
                    ActiveScreen::Menu(VerticalMenuScreen::new(menu).with_header(header));
            }
            Subscreen::DeviceScreen(device, _) => {
                let mut menu = VerticalMenu::empty().with_separators();
                menu.item(Button::new_menu_item(device, theme::menu_item_title()));
                menu.item(Button::new_menu_item(
                    "Disconnect".into(),
                    theme::menu_item_title_red(),
                ));
                *self.active_screen.deref_mut() = ActiveScreen::Menu(
                    VerticalMenuScreen::new(menu).with_header(
                        Header::new("Manage".into())
                            .with_close_button()
                            .with_left_button(
                                Button::with_icon(theme::ICON_CHEVRON_LEFT),
                                HeaderMsg::Back,
                            ),
                    ),
                );
            }
            Subscreen::AboutScreen => {
                let about_content = Paragraphs::new([
                    Paragraph::new(&theme::firmware::TEXT_REGULAR, "Firmware version"),
                    Paragraph::new(&theme::firmware::TEXT_REGULAR, self.firmware_version),
                ]);

                *self.active_screen.deref_mut() = ActiveScreen::About(
                    TextScreen::new(about_content)
                        .with_header(Header::new("About".into()).with_close_button()),
                );
            }
        }
    }

    fn handle_submenu(&mut self, ctx: &mut EventCtx, idx: usize) -> Option<DeviceMenuMsg> {
        match self.subscreens[self.active_subscreen] {
            Subscreen::Submenu(ref mut submenu_index) => {
                match self.submenus[*submenu_index].items[idx].action {
                    Some(Action::GoTo(menu)) => {
                        unwrap!(self.parent_subscreens.push(self.active_subscreen));
                        self.set_active_subscreen(menu);
                        self.place(self.bounds);
                        if let ActiveScreen::Menu(screen) = self.active_screen.deref_mut() {
                            screen.initialize_screen(ctx);
                        }
                        return None;
                    }
                    Some(Action::Return(msg)) => return Some(msg),
                    None => {}
                };
            }
            _ => {
                panic!("Expected a submenu!");
            }
        }

        None
    }

    fn go_back(&mut self, ctx: &mut EventCtx) -> Option<DeviceMenuMsg> {
        if let Some(parent) = self.parent_subscreens.pop() {
            self.set_active_subscreen(parent);
            self.place(self.bounds);
            if let ActiveScreen::Menu(screen) = self.active_screen.deref_mut() {
                screen.initialize_screen(ctx);
            }
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

        match self.active_screen.deref_mut() {
            ActiveScreen::Menu(menu) => {
                menu.place(bounds);
            }
            ActiveScreen::About(about) => {
                about.place(bounds);
            }
            ActiveScreen::Empty => {}
        };

        bounds
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        // Handle the event for the active menu
        let subscreen = &self.subscreens[self.active_subscreen];
        match (subscreen, self.active_screen.deref_mut()) {
            (Subscreen::Submenu(..) | Subscreen::DeviceScreen(..), ActiveScreen::Menu(menu)) => {
                match menu.event(ctx, event) {
                    Some(VerticalMenuScreenMsg::Selected(index)) => {
                        if let Subscreen::DeviceScreen(_, i) = subscreen {
                            if index == DISCONNECT_DEVICE_MENU_INDEX {
                                return Some(DeviceMenuMsg::DeviceDisconnect(*i));
                            }
                        } else {
                            return self.handle_submenu(ctx, index);
                        }
                    }
                    Some(VerticalMenuScreenMsg::Back) => {
                        return self.go_back(ctx);
                    }
                    Some(VerticalMenuScreenMsg::Close) => {
                        return Some(DeviceMenuMsg::Close);
                    }
                    _ => {}
                }
            }
            (Subscreen::AboutScreen, ActiveScreen::About(about)) => {
                if let Some(TextScreenMsg::Cancelled) = about.event(ctx, event) {
                    return self.go_back(ctx);
                }
            }
            _ => {}
        }

        None
    }

    fn render<'s>(&'s self, target: &mut impl Renderer<'s>) {
        match self.active_screen.deref() {
            ActiveScreen::Menu(menu) => menu.render(target),
            ActiveScreen::About(about) => about.render(target),
            ActiveScreen::Empty => {}
        };
    }
}

#[cfg(feature = "ui_debug")]
impl<'a> crate::trace::Trace for DeviceMenuScreen<'a> {
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.component("DeviceMenuScreen");
    }
}
