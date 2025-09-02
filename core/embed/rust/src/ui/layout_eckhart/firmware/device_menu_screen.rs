use core::{
    convert::TryFrom,
    ops::{Deref, DerefMut},
};

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

#[cfg(feature = "ble")]
use crate::ui::event::BLEEvent;

use super::{
    super::{
        component::{Button, ButtonStyleSheet, FuelGauge},
        constant::SCREEN,
        firmware::{
            Header, HeaderMsg, RegulatoryMsg, RegulatoryScreen, TextScreen, TextScreenMsg,
            VerticalMenu, VerticalMenuScreen, VerticalMenuScreenMsg, MEDIUM_MENU_ITEMS,
        },
    },
    theme, MediumMenuVec, ShortMenuVec,
};
use heapless::Vec;

#[repr(u8)]
#[derive(Copy, Clone, Default)]
#[cfg_attr(test, derive(Debug))]
pub enum DeviceMenuId {
    #[default]
    Root = 0,
    PairAndConnect,
    Settings,
    Security,
    PinCode,
    WipeCode,
    Device,
    Power,
}

impl TryFrom<usize> for DeviceMenuId {
    type Error = ();
    fn try_from(v: usize) -> Result<Self, Self::Error> {
        match v {
            0 => Ok(DeviceMenuId::Root),
            1 => Ok(DeviceMenuId::PairAndConnect),
            2 => Ok(DeviceMenuId::Settings),
            3 => Ok(DeviceMenuId::Security),
            4 => Ok(DeviceMenuId::PinCode),
            5 => Ok(DeviceMenuId::WipeCode),
            6 => Ok(DeviceMenuId::Device),
            7 => Ok(DeviceMenuId::Power),
            _ => Err(()),
        }
    }
}

impl From<DeviceMenuId> for u8 {
    #[inline]
    fn from(id: DeviceMenuId) -> Self {
        id as u8
    }
}

// FIXME: use mem::variant_count when it becomes stable
const MAX_SUBMENUS: usize = 8;
// submenus, device screens, regulatory and about screens
const MAX_SUBSCREENS: usize = MAX_SUBMENUS + MAX_PAIRED_DEVICES + 2;

const DISCONNECT_DEVICE_MENU_INDEX: usize = 0;

#[derive(Clone)]
enum Action {
    /// Go to a registered submenu by id (static)
    GoToSubmenu(DeviceMenuId),
    /// Go to an arbitrary subscreen index (kept for device/about/regulatory)
    GoTo(usize),
    /// Return a DeviceMenuMsg to the caller
    Return(DeviceMenuMsg),
}

#[derive(Copy, Clone)]
pub enum DeviceMenuMsg {
    // Root menu
    BackupFailed,

    // "Pair & Connect"
    DevicePair,       // pair a new device
    DeviceDisconnect, // disconnect a device
    DeviceUnpair(
        usize, /* which device to unpair, index in the list of devices */
    ),
    DeviceUnpairAll,

    // Power
    TurnOff,
    Reboot,
    RebootToBootloader,

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
    LedEnabled,
    WipeDevice,

    // Misc
    MenuRefresh(DeviceMenuId),
    Close,
}

struct MenuItem {
    text: TString<'static>,
    subtext: Option<(TString<'static>, Option<&'static TextStyle>)>,
    subtext_marquee: bool,
    stylesheet: &'static ButtonStyleSheet,
    connection_status: Option<bool>,
    action: Option<Action>,
}
const MENU_ITEM_NORMAL: &ButtonStyleSheet = &theme::menu_item_title();
const MENU_ITEM_LIGHT_WARNING: &ButtonStyleSheet = &theme::menu_item_title_yellow();
const MENU_ITEM_WARNING: &ButtonStyleSheet = &theme::menu_item_title_orange();
const MENU_ITEM_ERROR: &ButtonStyleSheet = &theme::menu_item_title_red();

impl MenuItem {
    pub fn new(text: TString<'static>, action: Option<Action>) -> Self {
        Self {
            text,
            subtext: None,
            subtext_marquee: false,
            stylesheet: MENU_ITEM_NORMAL,
            action,
            connection_status: None,
        }
    }

    pub fn with_subtext(
        &mut self,
        subtext: Option<(TString<'static>, Option<&'static TextStyle>)>,
    ) -> &mut Self {
        self.subtext = subtext;
        self
    }

    pub fn with_subtext_marquee(&mut self) -> &mut Self {
        self.subtext_marquee = true;
        self
    }

    pub fn with_connection_status(&mut self, connection_status: Option<bool>) -> &mut Self {
        self.connection_status = connection_status;
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
    Submenu(usize, DeviceMenuId),

    // A screen allowing the user to to disconnect a device
    DeviceScreen(
        TString<'static>, /* device name */
        bool,             /* is the device connected? */
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
    Menu(VerticalMenuScreen<MediumMenuVec>, DeviceMenuId),
    Device(VerticalMenuScreen<ShortMenuVec>),
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

    // Sparse map from SubmenuId -> subscreen index
    submenu_index: [Option<usize>; MAX_SUBMENUS],

    // index of the current subscreen in the list of subscreens
    active_subscreen: usize,
}

impl DeviceMenuScreen {
    #[allow(clippy::too_many_arguments)]
    pub fn new(
        init_submenu: Option<usize>,
        failed_backup: bool,
        paired_devices: Vec<TString<'static>, MAX_PAIRED_DEVICES>,
        connected_idx: Option<usize>,
        pin_code: Option<bool>,
        auto_lock_delay: Option<TString<'static>>,
        wipe_code: Option<bool>,
        check_backup: bool,
        device_name: Option<TString<'static>>,
        screen_brightness: Option<TString<'static>>,
        haptic_feedback: Option<bool>,
        led_enabled: Option<bool>,
        about_items: Obj,
    ) -> Result<Self, Error> {
        let mut screen = Self {
            bounds: Rect::zero(),
            about_items,
            active_screen: GcBox::new(ActiveScreen::Empty)?,
            active_subscreen: 0,
            submenus: GcBox::new(Vec::new())?,
            subscreens: Vec::new(),
            submenu_index: [None; MAX_SUBMENUS],
        };

        if pin_code.is_some() || auto_lock_delay.is_some() || wipe_code.is_some() || check_backup {
            screen.register_security_menu(pin_code, auto_lock_delay, wipe_code, check_backup);
        }
        screen.register_device_menu(device_name, screen_brightness, haptic_feedback, led_enabled);
        screen.register_settings_menu();
        screen.register_power_menu();

        let is_connected = connected_idx.is_some_and(|idx| idx < paired_devices.len());
        let connected_subtext: Option<TString<'static>> =
            is_connected.then_some(TR::words__connected.into());

        let mut submenu_indices: Vec<usize, MAX_PAIRED_DEVICES> = Vec::new();
        for (i, device) in paired_devices.iter().enumerate() {
            let connected = connected_idx == Some(i);
            unwrap!(submenu_indices
                .push(screen.add_subscreen(Subscreen::DeviceScreen(*device, connected, i))));
        }

        screen.register_pair_and_connect_menu(paired_devices, submenu_indices, connected_idx);
        let pin_unset = pin_code == Some(false);
        screen.register_root_menu(failed_backup, pin_unset, connected_subtext);

        // Activate the init submenu
        let init_submenu_id = init_submenu
            .and_then(|v| DeviceMenuId::try_from(v).ok())
            .unwrap_or_default();

        let init_subscreen = unwrap!(screen.try_resolve_submenu(init_submenu_id));
        screen.set_active_subscreen(init_subscreen);

        Ok(screen)
    }

    #[inline]
    fn register_submenu(&mut self, id: DeviceMenuId, submenu: Submenu) {
        let idx_in_submenus = self.add_submenu(submenu);
        let subscreen_idx = self.add_subscreen(Subscreen::Submenu(idx_in_submenus, id));
        self.submenu_index[id as usize] = Some(subscreen_idx);
    }

    #[inline]
    fn try_resolve_submenu(&self, id: DeviceMenuId) -> Option<usize> {
        self.submenu_index[id as usize]
    }

    #[inline]
    fn has_submenu(&self, id: DeviceMenuId) -> bool {
        self.try_resolve_submenu(id).is_some()
    }

    fn register_pair_and_connect_menu(
        &mut self,
        paired_devices: Vec<TString<'static>, MAX_PAIRED_DEVICES>,
        submenu_indices: Vec<usize, MAX_PAIRED_DEVICES>,
        connected_idx: Option<usize>,
    ) {
        let mut items: Vec<MenuItem, MEDIUM_MENU_ITEMS> = Vec::new();
        for ((device_idx, device), submenu_idx) in
            paired_devices.iter().enumerate().zip(submenu_indices)
        {
            let mut item_device = MenuItem::new(*device, Some(Action::GoTo(submenu_idx)));
            // TODO: this should be a boolean feature of the device
            let connection_status = match connected_idx {
                Some(idx) if idx == device_idx => Some(true),
                _ => Some(false),
            };
            item_device.with_connection_status(connection_status);
            unwrap!(items.push(item_device));
        }

        unwrap!(items.push(MenuItem::new(
            TR::ble__pair_new.into(),
            Some(Action::Return(DeviceMenuMsg::DevicePair)),
        )));
        let mut unpair_all_item = MenuItem::new(
            TR::ble__forget_all.into(),
            Some(Action::Return(DeviceMenuMsg::DeviceUnpairAll)),
        );
        unpair_all_item.with_stylesheet(MENU_ITEM_WARNING);
        unwrap!(items.push(unpair_all_item));

        self.register_submenu(DeviceMenuId::PairAndConnect, Submenu::new(items));
    }

    fn register_settings_menu(&mut self) {
        let mut items: Vec<MenuItem, MEDIUM_MENU_ITEMS> = Vec::new();

        if self.has_submenu(DeviceMenuId::Security) {
            unwrap!(items.push(MenuItem::new(
                TR::words__security.into(),
                Some(Action::GoToSubmenu(DeviceMenuId::Security))
            )));
        }

        if self.has_submenu(DeviceMenuId::Device) {
            unwrap!(items.push(MenuItem::new(
                TR::words__device.into(),
                Some(Action::GoToSubmenu(DeviceMenuId::Device))
            )));
        }

        self.register_submenu(DeviceMenuId::Settings, Submenu::new(items));
    }

    fn register_power_menu(&mut self) {
        let mut items: Vec<MenuItem, MEDIUM_MENU_ITEMS> = Vec::new();
        unwrap!(items.push(MenuItem::new(
            TR::buttons__turn_off.into(),
            Some(Action::Return(DeviceMenuMsg::TurnOff))
        )));
        unwrap!(items.push(MenuItem::new(
            TR::buttons__restart.into(),
            Some(Action::Return(DeviceMenuMsg::Reboot))
        )));
        unwrap!(items.push(MenuItem::new(
            TR::reboot_to_bootloader__title.into(),
            Some(Action::Return(DeviceMenuMsg::RebootToBootloader))
        )));

        self.register_submenu(DeviceMenuId::Power, Submenu::new(items));
    }

    fn register_code_menu(&mut self, wipe_code: bool) {
        let mut items: Vec<MenuItem, MEDIUM_MENU_ITEMS> = Vec::new();
        let change_text = match wipe_code {
            true => TR::wipe_code__change,
            false => TR::pin__change,
        }
        .into();
        let change_action = match wipe_code {
            true => Action::Return(DeviceMenuMsg::WipeCode),
            false => Action::Return(DeviceMenuMsg::PinCode),
        };
        let change_pin_item = MenuItem::new(change_text, Some(change_action));
        unwrap!(items.push(change_pin_item));

        let remove_text = match wipe_code {
            true => TR::wipe_code__remove,
            false => TR::pin__remove,
        }
        .into();
        let remove_action = match wipe_code {
            true => Action::Return(DeviceMenuMsg::WipeRemove),
            false => Action::Return(DeviceMenuMsg::PinRemove),
        };
        let mut remove_pin_item = MenuItem::new(remove_text, Some(remove_action));
        remove_pin_item.with_stylesheet(MENU_ITEM_WARNING);
        unwrap!(items.push(remove_pin_item));

        let id = match wipe_code {
            true => DeviceMenuId::WipeCode,
            false => DeviceMenuId::PinCode,
        };
        self.register_submenu(id, Submenu::new(items));
    }

    fn register_security_menu(
        &mut self,
        pin_code: Option<bool>,
        auto_lock_delay: Option<TString<'static>>,
        wipe_code: Option<bool>,
        check_backup: bool,
    ) {
        let mut items: Vec<MenuItem, MEDIUM_MENU_ITEMS> = Vec::new();

        if let Some(pin_code) = pin_code {
            let (action, subtext) = if pin_code {
                self.register_code_menu(false);
                let action = Action::GoToSubmenu(DeviceMenuId::PinCode);
                let subtext = (
                    TR::words__enabled.into(),
                    Some(&theme::TEXT_MENU_ITEM_SUBTITLE_GREEN),
                );
                (action, subtext)
            } else {
                let action = Action::Return(DeviceMenuMsg::PinCode);
                let subtext = (TR::words__disabled.into(), None);
                (action, subtext)
            };

            let mut pin_code_item = MenuItem::new(TR::pin__title.into(), Some(action));
            pin_code_item.with_subtext(Some(subtext));
            unwrap!(items.push(pin_code_item));
        }

        if let Some(auto_lock_delay) = auto_lock_delay {
            let mut auto_lock_delay_item = MenuItem::new(
                TR::auto_lock__title.into(),
                Some(Action::Return(DeviceMenuMsg::AutoLockDelay)),
            );
            auto_lock_delay_item.with_subtext(Some((auto_lock_delay, None)));
            unwrap!(items.push(auto_lock_delay_item));
        }

        if let Some(wipe_code) = wipe_code {
            let (action, subtext) = if wipe_code {
                self.register_code_menu(true);
                let action = Action::GoToSubmenu(DeviceMenuId::WipeCode);
                let subtext = (
                    TR::words__enabled.into(),
                    Some(&theme::TEXT_MENU_ITEM_SUBTITLE_GREEN),
                );
                (action, subtext)
            } else {
                let action = Action::Return(DeviceMenuMsg::WipeCode);
                let subtext = (TR::words__disabled.into(), None);
                (action, subtext)
            };

            let mut wipe_code_item = MenuItem::new(TR::wipe_code__title.into(), Some(action));
            wipe_code_item.with_subtext(Some(subtext));
            unwrap!(items.push(wipe_code_item));
        }

        if check_backup {
            unwrap!(items.push(MenuItem::new(
                TR::reset__check_backup_title.into(),
                Some(Action::Return(DeviceMenuMsg::CheckBackup)),
            )));
        }

        self.register_submenu(DeviceMenuId::Security, Submenu::new(items));
    }

    fn register_device_menu(
        &mut self,
        device_name: Option<TString<'static>>,
        screen_brightness: Option<TString<'static>>,
        haptic_feedback: Option<bool>,
        led_enabled: Option<bool>,
    ) {
        let mut items: Vec<MenuItem, MEDIUM_MENU_ITEMS> = Vec::new();
        if let Some(device_name) = device_name {
            let mut item_device_name = MenuItem::new(
                TR::words__name.into(),
                Some(Action::Return(DeviceMenuMsg::DeviceName)),
            );
            item_device_name
                .with_subtext(Some((device_name, None)))
                .with_subtext_marquee();
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
            let subtext = match haptic_feedback {
                true => (
                    TR::words__on.into(),
                    Some(&theme::TEXT_MENU_ITEM_SUBTITLE_GREEN),
                ),
                _ => (TR::words__off.into(), None),
            };
            haptic_item.with_subtext(Some(subtext));
            unwrap!(items.push(haptic_item));
        }

        if let Some(led_enabled) = led_enabled {
            let mut led_item = MenuItem::new(
                TR::words__led.into(),
                Some(Action::Return(DeviceMenuMsg::LedEnabled)),
            );
            let subtext = match led_enabled {
                true => (
                    TR::words__on.into(),
                    Some(&theme::TEXT_MENU_ITEM_SUBTITLE_GREEN),
                ),
                _ => (TR::words__off.into(), None),
            };
            led_item.with_subtext(Some(subtext));
            unwrap!(items.push(led_item));
        }

        let regulatory_index = self.add_subscreen(Subscreen::RegulatoryScreen);
        unwrap!(items.push(MenuItem::new(
            TR::regulatory_certification__title.into(),
            Some(Action::GoTo(regulatory_index))
        )));

        let about_index = self.add_subscreen(Subscreen::AboutScreen);
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

        self.register_submenu(DeviceMenuId::Device, Submenu::new(items));
    }

    fn register_root_menu(
        &mut self,
        failed_backup: bool,
        pin_unset: bool,
        connected_subtext: Option<TString<'static>>,
    ) {
        let mut items: Vec<MenuItem, MEDIUM_MENU_ITEMS> = Vec::new();

        if failed_backup {
            let mut item = MenuItem::new(
                TR::homescreen__title_backup_failed.into(),
                Some(Action::Return(DeviceMenuMsg::BackupFailed)),
            );
            item.with_subtext(Some((TR::words__review.into(), None)));
            item.with_stylesheet(MENU_ITEM_ERROR);
            unwrap!(items.push(item));
        }

        if pin_unset {
            let mut item = MenuItem::new(
                TR::homescreen__title_pin_not_set.into(),
                Some(Action::Return(DeviceMenuMsg::PinCode)),
            );
            item.with_subtext(Some((TR::words__set.into(), None)));
            item.with_stylesheet(MENU_ITEM_LIGHT_WARNING);
            unwrap!(items.push(item));
        }

        if self.has_submenu(DeviceMenuId::PairAndConnect) {
            let mut it = MenuItem::new(
                TR::ble__pair_title.into(),
                Some(Action::GoToSubmenu(DeviceMenuId::PairAndConnect)),
            );
            it.with_subtext(
                connected_subtext.map(|t| (t, Some(&theme::TEXT_MENU_ITEM_SUBTITLE_GREEN))),
            );
            unwrap!(items.push(it));
        }

        if self.has_submenu(DeviceMenuId::Settings) {
            unwrap!(items.push(MenuItem::new(
                TR::words__settings.into(),
                Some(Action::GoToSubmenu(DeviceMenuId::Settings)),
            )));
        }

        if self.has_submenu(DeviceMenuId::Power) {
            unwrap!(items.push(MenuItem::new(
                TR::words__power.into(),
                Some(Action::GoToSubmenu(DeviceMenuId::Power)),
            )));
        }

        self.register_submenu(DeviceMenuId::Root, Submenu::new(items).with_battery());
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

    fn activate_subscreen(&mut self, idx: usize, ctx: &mut EventCtx) {
        self.set_active_subscreen(idx);
        self.place(self.bounds);
        if let ActiveScreen::Menu(screen, ..) = self.active_screen.deref_mut() {
            screen.initialize_screen(ctx);
        }
    }

    fn build_active_subscreen(&mut self) {
        match self.subscreens[self.active_subscreen] {
            Subscreen::Submenu(submenu_index, id) => {
                let submenu = &self.submenus[submenu_index];
                let mut menu = VerticalMenu::<MediumMenuVec>::empty();
                for item in &submenu.items {
                    let button = if let Some(connected) = item.connection_status {
                        Button::new_connection_item(
                            item.text,
                            *item.stylesheet,
                            item.subtext.map(|(t, _)| t),
                            connected,
                        )
                    } else if let Some((subtext, subtext_style)) = item.subtext {
                        let subtext_style =
                            subtext_style.unwrap_or(&theme::TEXT_MENU_ITEM_SUBTITLE);
                        let ctor = if item.subtext_marquee {
                            Button::new_single_line_menu_item_with_subtext_marquee
                        } else {
                            Button::new_menu_item_with_subtext
                        };
                        ctor(item.text, *item.stylesheet, subtext, subtext_style)
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
                    ActiveScreen::Menu(VerticalMenuScreen::new(menu).with_header(header), id);
            }
            Subscreen::DeviceScreen(device, connected, _) => {
                let mut menu = VerticalMenu::empty();
                if connected {
                    menu.item(Button::new_menu_item(
                        TR::words__disconnect.into(),
                        theme::menu_item_title(),
                    ));
                }
                menu.item(Button::new_menu_item(
                    TR::words__forget.into(),
                    theme::menu_item_title_orange(),
                ));
                *self.active_screen.deref_mut() = ActiveScreen::Device(
                    VerticalMenuScreen::new(menu)
                        .with_header(
                            Header::new(TR::buttons__back.into())
                                .with_close_button()
                                .with_left_button(
                                    Button::with_icon(theme::ICON_CHEVRON_LEFT),
                                    HeaderMsg::Back,
                                ),
                        )
                        .with_subtitle(device),
                );
            }
            Subscreen::AboutScreen => {
                *self.active_screen.deref_mut() = ActiveScreen::About(
                    TextScreen::new(
                        PropsList::new_styled(
                            self.about_items,
                            &theme::TEXT_SMALL_LIGHT,
                            &theme::TEXT_MONO_MEDIUM_LIGHT,
                            &theme::TEXT_MONO_MEDIUM_LIGHT_DATA,
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
            Subscreen::Submenu(submenu_index, ..) => {
                match self.submenus[submenu_index].items[idx].action {
                    Some(Action::GoToSubmenu(id_new)) => {
                        if let Some(menu) = self.try_resolve_submenu(id_new) {
                            self.activate_subscreen(menu, ctx);
                        }
                        return None;
                    }
                    Some(Action::GoTo(menu)) => {
                        self.activate_subscreen(menu, ctx);
                        return None;
                    }
                    Some(Action::Return(msg)) => return Some(msg),
                    None => {}
                }
            }
            _ => {
                panic!("Expected a submenu!");
            }
        }

        None
    }

    fn go_back(&mut self, ctx: &mut EventCtx) -> Option<DeviceMenuMsg> {
        let parent = match self.subscreens[self.active_subscreen] {
            Subscreen::Submenu(_, id) => match id {
                DeviceMenuId::Root => return Some(DeviceMenuMsg::Close),
                DeviceMenuId::PairAndConnect => DeviceMenuId::Root,
                DeviceMenuId::Settings => DeviceMenuId::Root,
                DeviceMenuId::Security => DeviceMenuId::Settings,
                DeviceMenuId::PinCode => DeviceMenuId::Security,
                DeviceMenuId::WipeCode => DeviceMenuId::Security,
                DeviceMenuId::Device => DeviceMenuId::Settings,
                DeviceMenuId::Power => DeviceMenuId::Root,
            },
            Subscreen::DeviceScreen(..) => DeviceMenuId::PairAndConnect,
            Subscreen::AboutScreen | Subscreen::RegulatoryScreen => DeviceMenuId::Device,
        };

        self.activate_subscreen(unwrap!(self.try_resolve_submenu(parent)), ctx);
        None
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
            ActiveScreen::Menu(menu, ..) => {
                menu.place(bounds);
            }
            ActiveScreen::Device(device) => {
                device.place(bounds);
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
        #[cfg(feature = "ble")]
        if matches!(
            event,
            Event::BLE(BLEEvent::Connected | BLEEvent::Disconnected | BLEEvent::ConnectionChanged)
        ) {
            let submenu_idx = match self.active_screen.deref_mut() {
                ActiveScreen::Menu(_, id) => *id,
                ActiveScreen::Device(_) => DeviceMenuId::PairAndConnect,
                ActiveScreen::Regulatory(_) | ActiveScreen::About(_) => DeviceMenuId::Device,
                ActiveScreen::Empty => DeviceMenuId::Root,
            };

            return Some(DeviceMenuMsg::MenuRefresh(submenu_idx));
        }

        // Handle the event for the active menu
        let subscreen = &self.subscreens[self.active_subscreen];
        match (subscreen, self.active_screen.deref_mut()) {
            (Subscreen::Submenu(..), ActiveScreen::Menu(menu, ..)) => {
                match menu.event(ctx, event) {
                    Some(VerticalMenuScreenMsg::Selected(button_idx)) => {
                        return self.handle_submenu(ctx, button_idx);
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
            (Subscreen::DeviceScreen(_, connected, device_idx), ActiveScreen::Device(menu)) => {
                match menu.event(ctx, event) {
                    Some(VerticalMenuScreenMsg::Selected(button_idx)) => match button_idx {
                        DISCONNECT_DEVICE_MENU_INDEX if *connected => {
                            return Some(DeviceMenuMsg::DeviceDisconnect);
                        }
                        _ => {
                            return Some(DeviceMenuMsg::DeviceUnpair(*device_idx));
                        }
                    },
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
            ActiveScreen::Menu(menu, ..) => menu.render(target),
            ActiveScreen::Device(device) => device.render(target),
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

        match self.active_screen.deref() {
            ActiveScreen::Menu(ref screen, ..) => {
                t.child("Menu", screen);
            }
            ActiveScreen::Device(ref screen) => {
                t.child("Device", screen);
            }
            ActiveScreen::About(ref screen) => {
                t.child("About", screen);
            }
            ActiveScreen::Regulatory(ref screen) => {
                t.child("Regulatory", screen);
            }
            ActiveScreen::Empty => {
                t.null("ActiveScreen");
            }
        }
    }
}
