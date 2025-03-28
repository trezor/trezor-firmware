use crate::{
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
                VerticalMenuScreenMsg, MENU_MAX_ITEMS,
            },
        },
        shape::Renderer,
    },
};

use super::theme;
use heapless::Vec;

const MAX_DEPTH: usize = 5;
const MAX_SUBSCREENS: usize = 10;

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

struct SubmenuScreen {
    header_text: TString<'static>,
    show_battery: bool,
    items: Vec<MenuItem, MENU_MAX_ITEMS>,
}

impl SubmenuScreen {
    pub fn new(header_text: TString<'static>, items: Vec<MenuItem, MENU_MAX_ITEMS>) -> Self {
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
#[allow(clippy::large_enum_variant)]
enum Subscreen {
    // A menu, with associated items and actions
    Submenu(SubmenuScreen),

    // A screen allowing the user to to disconnect a device
    DeviceScreen(
        TString<'static>, /* device name */
        usize,            /* index in the list of devices */
    ),

    // The about screen
    AboutScreen,
}

pub struct DeviceMenuScreen<'a> {
    bounds: Rect,

    battery_percentage: u8,

    // These correspond to the currently active subscreen,
    // which is one of the possible kinds of subscreens
    // as defined by `enum Subscreen`
    // The active one will be Some(...) and the other two will be None.
    // This way we only need to keep one screen at any time in memory.
    menu_screen: Option<VerticalMenuScreen>,
    paired_device_screen: Option<VerticalMenuScreen>,
    about_screen: Option<TextScreen<Paragraphs<[Paragraph<'a>; 2]>>>,

    // Information needed to construct any subscreen on demand
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
        // NB: we currently only support one device at a time.
        // if we ever increase this size, we will need a way to return the correct
        // device index on Disconnect back to uPy
        // (see component_msg_obj.rs, which currently just returns "DeviceDisconnect" with no
        // index!)
        paired_devices: Vec<TString<'static>, 1>,
    ) -> Self {
        let mut screen = Self {
            bounds: Rect::zero(),
            battery_percentage,
            menu_screen: None,
            paired_device_screen: None,
            about_screen: None,
            active_subscreen: 0,
            subscreens: Vec::new(),
            parent_subscreens: Vec::new(),
        };

        let about = screen.add_subscreen(Subscreen::AboutScreen);
        let security = screen.add_security_menu();
        let device = screen.add_device_menu("My device".into(), about); // TODO: device name
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

        screen
    }

    fn is_low_battery(&self) -> bool {
        self.battery_percentage < 20
    }

    fn add_paired_devices_menu(
        &mut self,
        paired_devices: Vec<TString<'static>, 1>,
        paired_device_indices: Vec<usize, 1>,
    ) -> usize {
        let mut items: Vec<MenuItem, MENU_MAX_ITEMS> = Vec::new();
        for (device, idx) in paired_devices.iter().zip(paired_device_indices) {
            unwrap!(items.push(
                MenuItem::new(*device, Some(Action::GoTo(idx))).with_subtext(Some((
                    "Connected".into(),
                    Some(Button::SUBTEXT_STYLE_GREEN)
                ))) // TODO: this should be a boolean feature of the device
            ));
        }

        self.add_subscreen(Subscreen::Submenu(SubmenuScreen::new(
            "Manage paired devices".into(),
            items,
        )))
    }

    fn add_pair_and_connect_menu(&mut self, manage_devices_index: usize) -> usize {
        let mut items: Vec<MenuItem, MENU_MAX_ITEMS> = Vec::new();
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

        self.add_subscreen(Subscreen::Submenu(SubmenuScreen::new(
            "Pair & connect".into(),
            items,
        )))
    }

    fn add_settings_menu(&mut self, security_index: usize, device_index: usize) -> usize {
        let mut items: Vec<MenuItem, MENU_MAX_ITEMS> = Vec::new();
        unwrap!(items.push(MenuItem::new(
            "Security".into(),
            Some(Action::GoTo(security_index))
        )));
        unwrap!(items.push(MenuItem::new(
            "Device".into(),
            Some(Action::GoTo(device_index))
        )));

        self.add_subscreen(Subscreen::Submenu(SubmenuScreen::new(
            "Settings".into(),
            items,
        )))
    }

    fn add_security_menu(&mut self) -> usize {
        let mut items: Vec<MenuItem, MENU_MAX_ITEMS> = Vec::new();
        unwrap!(items.push(MenuItem::new(
            "Check backup".into(),
            Some(Action::Return(DeviceMenuMsg::CheckBackup)),
        )));
        unwrap!(items.push(MenuItem::new(
            "Wipe device".into(),
            Some(Action::Return(DeviceMenuMsg::WipeDevice))
        )));

        self.add_subscreen(Subscreen::Submenu(SubmenuScreen::new(
            "Security".into(),
            items,
        )))
    }

    fn add_device_menu(&mut self, device_name: TString<'static>, about_index: usize) -> usize {
        let mut items: Vec<MenuItem, MENU_MAX_ITEMS> = Vec::new();
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

        self.add_subscreen(Subscreen::Submenu(SubmenuScreen::new(
            "Device".into(),
            items,
        )))
    }

    fn add_root_menu(
        &mut self,
        failed_backup: bool,
        pair_and_connect_index: usize,
        settings_index: usize,
    ) -> usize {
        let mut items: Vec<MenuItem, MENU_MAX_ITEMS> = Vec::new();
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
        self.add_subscreen(Subscreen::Submenu(
            SubmenuScreen::new("".into(), items).with_battery(),
        ))
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
            Subscreen::Submenu(ref mut submenu) => {
                self.paired_device_screen = None;
                self.about_screen = None;
                let mut menu = VerticalMenu::empty().with_separators();
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
                    menu = menu.item(button);
                }
                let mut header = Header::new(submenu.header_text)
                    .with_right_button(Button::with_icon(theme::ICON_CROSS), HeaderMsg::Cancelled);
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
                self.menu_screen = Some(VerticalMenuScreen::new(menu).with_header(header));
            }
            Subscreen::DeviceScreen(device, _) => {
                self.menu_screen = None;
                self.about_screen = None;
                let mut menu = VerticalMenu::empty().with_separators();
                menu = menu.item(Button::new_menu_item(device, theme::menu_item_title()));
                menu = menu.item(Button::new_menu_item(
                    "Disconnect".into(),
                    theme::menu_item_title_red(),
                ));
                self.paired_device_screen = Some(
                    VerticalMenuScreen::new(menu).with_header(
                        Header::new("Manage".into())
                            .with_right_button(
                                Button::with_icon(theme::ICON_CROSS),
                                HeaderMsg::Cancelled,
                            )
                            .with_left_button(
                                Button::with_icon(theme::ICON_CHEVRON_LEFT),
                                HeaderMsg::Back,
                            ),
                    ),
                );
            }
            Subscreen::AboutScreen => {
                self.menu_screen = None;
                self.paired_device_screen = None;
                let about_content = Paragraphs::new([
                    Paragraph::new(&theme::firmware::TEXT_REGULAR, "Firmware version"),
                    Paragraph::new(&theme::firmware::TEXT_REGULAR, "2.3.1"), // TODO
                ]);

                self.about_screen = Some(
                    TextScreen::new(about_content)
                        .with_header(Header::new("About".into()).with_close_button()),
                );
            }
        }
    }

    fn handle_submenu(&mut self, ctx: &mut EventCtx, idx: usize) -> Option<DeviceMenuMsg> {
        match self.subscreens[self.active_subscreen] {
            Subscreen::Submenu(ref mut menu_screen) => {
                match menu_screen.items[idx].action {
                    Some(Action::GoTo(menu)) => {
                        self.menu_screen.as_mut().unwrap().update_menu(ctx);
                        unwrap!(self.parent_subscreens.push(self.active_subscreen));
                        self.set_active_subscreen(menu);
                        self.place(self.bounds);
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

    fn go_back(&mut self) -> Option<DeviceMenuMsg> {
        if let Some(parent) = self.parent_subscreens.pop() {
            self.set_active_subscreen(parent);
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
            Subscreen::Submenu(..) => self.menu_screen.place(bounds),
            Subscreen::DeviceScreen(..) => self.paired_device_screen.place(bounds),
            Subscreen::AboutScreen => self.about_screen.place(bounds),
        };

        bounds
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        // Handle the event for the active menu
        match self.subscreens[self.active_subscreen] {
            Subscreen::Submenu(..) => match self.menu_screen.event(ctx, event) {
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
            Subscreen::DeviceScreen(_, i) => match self.paired_device_screen.event(ctx, event) {
                Some(VerticalMenuScreenMsg::Selected(index)) => {
                    if index == DISCONNECT_DEVICE_MENU_INDEX {
                        return Some(DeviceMenuMsg::DeviceDisconnect(i));
                    }
                }
                Some(VerticalMenuScreenMsg::Back) => {
                    return self.go_back();
                }
                Some(VerticalMenuScreenMsg::Close) => {
                    return Some(DeviceMenuMsg::Close);
                }
                _ => {}
            },
            Subscreen::AboutScreen => {
                if let Some(TextScreenMsg::Cancelled) = self.about_screen.event(ctx, event) {
                    return self.go_back();
                }
            }
        }

        None
    }

    fn render<'s>(&'s self, target: &mut impl Renderer<'s>) {
        match &self.subscreens[self.active_subscreen] {
            Subscreen::Submenu(..) => self.menu_screen.render(target),
            Subscreen::DeviceScreen(..) => self.paired_device_screen.render(target),
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
