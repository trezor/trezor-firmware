use core::ops::{Deref, DerefMut};

use crate::{
    error::Error,
    micropython::{gc::GcBox, obj::Obj},
    strutil::TString,
    translations::TR,
    ui::{
        component::{
            text::{
                paragraphs::{ParagraphSource, Paragraphs},
                TextStyle,
            },
            Component, Event, EventCtx,
        },
        geometry::{LinearPlacement, Rect},
        layout::util::PropsList,
        shape::Renderer,
        ui_firmware::MAX_PAIRED_DEVICES,
    },
};

use super::{
    super::{
        component::{Button, ButtonStyleSheet, FuelGauge},
        constant::SCREEN,
        firmware::{
            Header, HeaderMsg, RegulatoryMsg, RegulatoryScreen, TextScreen, TextScreenMsg,
            VerticalMenu, VerticalMenuScreen, VerticalMenuScreenMsg, MEDIUM_MENU_ITEMS,
        },
    },
    theme, MediumMenuVec,
};
use heapless::Vec;

const MAX_DEPTH: usize = 3;
const MAX_SUBSCREENS: usize = 12;
const MAX_SUBMENUS: usize = MAX_SUBSCREENS - 1 - MAX_PAIRED_DEVICES /* (about and device screens) */;

const DIS_CONNECT_DEVICE_MENU_INDEX: usize = 0;
const FORGET_DEVICE_MENU_INDEX: usize = 1;

#[derive(Clone)]
enum Action {
    /// Go to another registered subscreen
    GoTo(usize),
    /// Return a DeviceMenuMsg to the caller
    Return(DeviceMenuMsg),
}

#[derive(Copy, Clone)]
pub enum DeviceMenuMsg {
    // Root menu
    BackupFailed,

    // Bluetooth
    Bluetooth,

    // "Pair & Connect"
    DevicePair,       // pair a new device
    DeviceDisconnect, // disconnect a device
    DeviceConnect(
        usize, /* which device to connect, index in the list of devices */
    ),
    DeviceUnpair(
        usize, /* which device to unpair, index in the list of devices */
    ),
    DeviceUnpairAll,

    // Security menu
    PinCode,
    PinRemove,
    AutoLockDelay,
    WipeCode,
    WipeRemove,
    CheckBackup,

    // Device menu
    DeviceName,
    ScreenBrightness,
    HapticFeedback,
    Led,
    WipeDevice,

    // nothing selected
    Close,
}

struct MenuItem {
    text: TString<'static>,
    subtext: Option<(TString<'static>, Option<&'static TextStyle>)>,
    stylesheet: &'static ButtonStyleSheet,
    action: Option<Action>,
}
const MENU_ITEM_TITLE_STYLE_SHEET: &ButtonStyleSheet = &theme::menu_item_title();
const MENU_ITEM_WARNING: &ButtonStyleSheet = &theme::menu_item_title_orange();

impl MenuItem {
    pub fn new(text: TString<'static>, action: Option<Action>) -> Self {
        Self {
            text,
            subtext: None,
            stylesheet: MENU_ITEM_TITLE_STYLE_SHEET,
            action,
        }
    }

    pub fn with_subtext(
        &mut self,
        subtext: Option<(TString<'static>, Option<&'static TextStyle>)>,
    ) -> &mut Self {
        self.subtext = subtext;
        self
    }

    pub fn with_stylesheet(&mut self, stylesheet: &'static ButtonStyleSheet) -> &mut Self {
        self.stylesheet = stylesheet;
        self
    }
}

struct Submenu {
    show_battery: bool,
    items: Vec<MenuItem, MEDIUM_MENU_ITEMS>,
}

impl Submenu {
    pub fn new(items: Vec<MenuItem, MEDIUM_MENU_ITEMS>) -> Self {
        Self {
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
    // A screen showing the regulatory information
    RegulatoryScreen,
}

// Used to preallocate memory for the largest enum variant
#[allow(clippy::large_enum_variant)]
enum ActiveScreen {
    Menu(VerticalMenuScreen<MediumMenuVec>),
    About(TextScreen<Paragraphs<PropsList>>),
    Regulatory(RegulatoryScreen),

    // used only during `DeviceMenuScreen::new`
    Empty,
}

pub struct DeviceMenuScreen {
    bounds: Rect,
    about_items: Obj,
    // These correspond to the currently active subscreen,
    // which is one of the possible kinds of subscreens
    // as defined by `enum Subscreen` (DeviceScreen is still a VerticalMenuScreen!)
    // This way we only need to keep one screen at any time in memory.
    active_screen: GcBox<ActiveScreen>,
    // Information needed to construct any subscreen on demand
    submenus: GcBox<Vec<Submenu, MAX_SUBMENUS>>,
    subscreens: Vec<Subscreen, MAX_SUBSCREENS>,
    // index of the current subscreen in the list of subscreens
    active_subscreen: usize,
    // stack of parents that led to the current subscreen
    parent_subscreens: Vec<usize, MAX_DEPTH>,
}

impl DeviceMenuScreen {
    #[allow(clippy::too_many_arguments)]
    pub fn new(
        failed_backup: bool,
        _pin_unset: bool,
        paired_devices: Vec<TString<'static>, MAX_PAIRED_DEVICES>,
        _connected_idx: Option<usize>,
        _bluetooth: Option<bool>,
        _pin_code: Option<bool>,
        _auto_lock_delay: Option<TString<'static>>,
        _wipe_code: Option<bool>,
        _check_backup: bool,
        device_name: Option<TString<'static>>,
        screen_brightness: Option<TString<'static>>,
        haptic_feedback: Option<bool>,
        led: Option<bool>,
        about_items: Obj,
    ) -> Result<Self, Error> {
        let mut screen = Self {
            bounds: Rect::zero(),
            about_items,
            active_screen: GcBox::new(ActiveScreen::Empty)?,
            active_subscreen: 0,
            submenus: GcBox::new(Vec::new())?,
            subscreens: Vec::new(),
            parent_subscreens: Vec::new(),
        };

        let about = screen.add_subscreen(Subscreen::AboutScreen);
        let regulatory = screen.add_subscreen(Subscreen::RegulatoryScreen);
        let security = screen.add_security_menu();
        let device = screen.add_device_menu(
            device_name,
            screen_brightness,
            haptic_feedback,
            led,
            regulatory,
            about,
        );
        let settings = screen.add_settings_menu(security, device);

        let is_connected = !paired_devices.is_empty(); // FIXME after BLE API has this
        let connected_subtext: Option<TString<'static>> =
            is_connected.then_some("1 device connected".into());

        let mut paired_device_indices: Vec<usize, MAX_PAIRED_DEVICES> = Vec::new();
        for (i, device) in paired_devices.iter().enumerate() {
            unwrap!(paired_device_indices
                .push(screen.add_subscreen(Subscreen::DeviceScreen(*device, i))));
        }

        let devices = screen.add_paired_devices_menu(paired_devices, paired_device_indices);
        let pair_and_connect = screen.add_pair_and_connect_menu(devices, connected_subtext);

        let root =
            screen.add_root_menu(failed_backup, pair_and_connect, settings, connected_subtext);

        screen.set_active_subscreen(root);

        Ok(screen)
    }

    fn add_paired_devices_menu(
        &mut self,
        paired_devices: Vec<TString<'static>, MAX_PAIRED_DEVICES>,
        paired_device_indices: Vec<usize, MAX_PAIRED_DEVICES>,
    ) -> usize {
        let mut items: Vec<MenuItem, MEDIUM_MENU_ITEMS> = Vec::new();
        for (device, idx) in paired_devices.iter().zip(paired_device_indices) {
            let mut item_device = MenuItem::new(*device, Some(Action::GoTo(idx)));
            // TODO: this should be a boolean feature of the device
            item_device.with_subtext(Some((
                TR::words__connected.into(),
                Some(&theme::TEXT_MENU_ITEM_SUBTITLE_GREEN),
            )));
            unwrap!(items.push(item_device));
        }

        let submenu_index = self.add_submenu(Submenu::new(items));
        self.add_subscreen(Subscreen::Submenu(submenu_index))
    }

    fn add_pair_and_connect_menu(
        &mut self,
        manage_devices_index: usize,
        connected_subtext: Option<TString<'static>>,
    ) -> usize {
        let mut items: Vec<MenuItem, MEDIUM_MENU_ITEMS> = Vec::new();
        let mut manage_paired_item = MenuItem::new(
            TR::ble__manage_paired.into(),
            Some(Action::GoTo(manage_devices_index)),
        );
        manage_paired_item.with_subtext(
            connected_subtext.map(|t| (t, Some(&theme::TEXT_MENU_ITEM_SUBTITLE_GREEN))),
        );
        unwrap!(items.push(manage_paired_item));
        unwrap!(items.push(MenuItem::new(
            TR::ble__pair_new.into(),
            Some(Action::Return(DeviceMenuMsg::DevicePair)),
        )));

        let submenu_index = self.add_submenu(Submenu::new(items));
        self.add_subscreen(Subscreen::Submenu(submenu_index))
    }

    fn add_settings_menu(&mut self, security_index: usize, device_index: usize) -> usize {
        let mut items: Vec<MenuItem, MEDIUM_MENU_ITEMS> = Vec::new();
        unwrap!(items.push(MenuItem::new(
            TR::words__security.into(),
            Some(Action::GoTo(security_index))
        )));
        unwrap!(items.push(MenuItem::new(
            TR::words__device.into(),
            Some(Action::GoTo(device_index))
        )));

        let submenu_index = self.add_submenu(Submenu::new(items));
        self.add_subscreen(Subscreen::Submenu(submenu_index))
    }

    fn add_security_menu(&mut self) -> usize {
        let mut items: Vec<MenuItem, MEDIUM_MENU_ITEMS> = Vec::new();
        unwrap!(items.push(MenuItem::new(
            TR::reset__check_backup_title.into(),
            Some(Action::Return(DeviceMenuMsg::CheckBackup)),
        )));
        unwrap!(items.push(MenuItem::new(
            TR::wipe__title.into(),
            Some(Action::Return(DeviceMenuMsg::WipeDevice))
        )));

        let submenu_index = self.add_submenu(Submenu::new(items));
        self.add_subscreen(Subscreen::Submenu(submenu_index))
    }

    fn add_device_menu(
        &mut self,
        device_name: Option<TString<'static>>,
        screen_brightness: Option<TString<'static>>,
        haptic_feedback: Option<bool>,
        led: Option<bool>,
        regulatory_index: usize,
        about_index: usize,
    ) -> usize {
        let mut items: Vec<MenuItem, MEDIUM_MENU_ITEMS> = Vec::new();
        if let Some(device_name) = device_name {
            let mut item_device_name = MenuItem::new(
                TR::words__name.into(),
                Some(Action::Return(DeviceMenuMsg::DeviceName)),
            );
            item_device_name.with_subtext(Some((device_name, None)));
            unwrap!(items.push(item_device_name));
        }

        if let Some(brightness) = screen_brightness {
            let brightness_item = MenuItem::new(
                brightness,
                Some(Action::Return(DeviceMenuMsg::ScreenBrightness)),
            );
            unwrap!(items.push(brightness_item));
        }

        if let Some(haptic_feedback) = haptic_feedback {
            let mut haptic_item = MenuItem::new(
                TR::haptic_feedback__title.into(),
                Some(Action::Return(DeviceMenuMsg::HapticFeedback)),
            );
            let subtext = if haptic_feedback {
                (
                    TR::words__on.into(),
                    Some(&theme::TEXT_MENU_ITEM_SUBTITLE_GREEN),
                )
            } else {
                (TR::words__off.into(), None)
            };
            haptic_item.with_subtext(Some(subtext));
            unwrap!(items.push(haptic_item));
        }

        if let Some(led) = led {
            let mut led_item = MenuItem::new(
                TR::words__led.into(),
                Some(Action::Return(DeviceMenuMsg::Led)),
            );
            let subtext = if led {
                (
                    TR::words__on.into(),
                    Some(&theme::TEXT_MENU_ITEM_SUBTITLE_GREEN),
                )
            } else {
                (TR::words__off.into(), None)
            };
            led_item.with_subtext(Some(subtext));
            unwrap!(items.push(led_item));
        }

        unwrap!(items.push(MenuItem::new(
            TR::regulatory_certification__title.into(),
            Some(Action::GoTo(regulatory_index))
        )));

        unwrap!(items.push(MenuItem::new(
            TR::words__about.into(),
            Some(Action::GoTo(about_index))
        )));

        let mut wipe_device_item = MenuItem::new(
            TR::wipe__title.into(),
            Some(Action::Return(DeviceMenuMsg::WipeDevice)),
        );
        wipe_device_item.with_stylesheet(MENU_ITEM_WARNING);
        unwrap!(items.push(wipe_device_item));

        let submenu_index = self.add_submenu(Submenu::new(items));
        self.add_subscreen(Subscreen::Submenu(submenu_index))
    }

    fn add_root_menu(
        &mut self,
        failed_backup: bool,
        pair_and_connect_index: usize,
        settings_index: usize,
        connected_subtext: Option<TString<'static>>,
    ) -> usize {
        let mut items: Vec<MenuItem, MEDIUM_MENU_ITEMS> = Vec::new();
        if failed_backup {
            let mut item_backup_failed = MenuItem::new(
                TR::homescreen__title_backup_failed.into(),
                Some(Action::Return(DeviceMenuMsg::BackupFailed)),
            );
            item_backup_failed.with_subtext(Some((TR::words__review.into(), None)));
            item_backup_failed.with_stylesheet(MENU_ITEM_TITLE_STYLE_SHEET);
            unwrap!(items.push(item_backup_failed));
        }
        let mut item_pair_and_connect = MenuItem::new(
            TR::ble__pair_title.into(),
            Some(Action::GoTo(pair_and_connect_index)),
        );
        item_pair_and_connect.with_subtext(
            connected_subtext.map(|t| (t, Some(&theme::TEXT_MENU_ITEM_SUBTITLE_GREEN))),
        );
        unwrap!(items.push(item_pair_and_connect));
        unwrap!(items.push(MenuItem::new(
            TR::words__settings.into(),
            Some(Action::GoTo(settings_index)),
        )));

        let submenu_index = self.add_submenu(Submenu::new(items).with_battery());
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
                let mut menu = VerticalMenu::<MediumMenuVec>::empty().with_separators();
                for item in &submenu.items {
                    let button = if let Some((subtext, subtext_style)) = item.subtext {
                        let subtext_style =
                            subtext_style.unwrap_or(&theme::TEXT_MENU_ITEM_SUBTITLE);
                        Button::new_menu_item_with_subtext(
                            item.text,
                            *item.stylesheet,
                            subtext,
                            subtext_style,
                        )
                    } else {
                        Button::new_menu_item(item.text, *item.stylesheet)
                    };
                    menu.item(button);
                }
                let mut header = Header::new(TR::buttons__back.into()).with_close_button();
                if submenu.show_battery {
                    header = header.with_fuel_gauge(Some(FuelGauge::always()));
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
                    TR::words__disconnect.into(),
                    theme::menu_item_title_red(),
                ));
                *self.active_screen.deref_mut() = ActiveScreen::Menu(
                    VerticalMenuScreen::new(menu).with_header(
                        Header::new(TR::words__manage.into())
                            .with_close_button()
                            .with_left_button(
                                Button::with_icon(theme::ICON_CHEVRON_LEFT),
                                HeaderMsg::Back,
                            ),
                    ),
                );
            }
            Subscreen::AboutScreen => {
                *self.active_screen.deref_mut() = ActiveScreen::About(
                    TextScreen::new(
                        PropsList::new_styled(
                            self.about_items,
                            &theme::TEXT_SMALL_LIGHT,
                            &theme::TEXT_MONO_MEDIUM_LIGHT,
                            &theme::TEXT_MONO_MEDIUM_LIGHT,
                            theme::PROP_INNER_SPACING,
                            theme::PROPS_SPACING,
                        )
                        .unwrap_or_else(|_| unwrap!(PropsList::empty()))
                        .into_paragraphs()
                        .with_placement(LinearPlacement::vertical()),
                    )
                    .with_header(Header::new(TR::words__about.into()).with_close_button()),
                );
            }
            Subscreen::RegulatoryScreen => {
                *self.active_screen.deref_mut() = ActiveScreen::Regulatory(RegulatoryScreen::new());
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

impl Component for DeviceMenuScreen {
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
            ActiveScreen::Regulatory(regulatory) => {
                regulatory.place(bounds);
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
                        if let Subscreen::DeviceScreen(_, _) = subscreen {
                            if index == DIS_CONNECT_DEVICE_MENU_INDEX {
                                return Some(DeviceMenuMsg::DeviceDisconnect);
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
            (Subscreen::RegulatoryScreen, ActiveScreen::Regulatory(regulatory)) => {
                if let Some(RegulatoryMsg::Cancelled) = regulatory.event(ctx, event) {
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
            ActiveScreen::Regulatory(regulatory) => regulatory.render(target),
            ActiveScreen::Empty => {}
        };
    }
}

#[cfg(feature = "ui_debug")]
impl crate::trace::Trace for DeviceMenuScreen {
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.component("DeviceMenuScreen");
    }
}
