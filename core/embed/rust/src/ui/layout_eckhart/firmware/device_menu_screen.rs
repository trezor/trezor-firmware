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

impl TryFrom<u8> for DeviceMenuId {
    type Error = ();
    fn try_from(v: u8) -> Result<Self, Self::Error> {
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

impl From<DeviceMenuId> for usize {
    #[inline]
    fn from(id: DeviceMenuId) -> Self {
        usize::from(id as u8)
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
    GoTo(u8),
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
        u8, /* which device to unpair, index in the list of devices */
    ),
    DeviceUnpairAll,

    // Power
    PowerOff,
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

trait VecExt {
    fn add(&mut self, item: MenuItem) -> &mut Self;
}

impl<const N: usize> VecExt for Vec<MenuItem, N> {
    fn add(&mut self, item: MenuItem) -> &mut Self {
        if self.push(item).is_err() {
            #[cfg(feature = "ui_debug")]
            fatal_error!("Menu item list is full");
        }
        self
    }
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
    fn new(text: TString<'static>, action: Option<Action>) -> Self {
        Self {
            text,
            subtext: None,
            subtext_marquee: false,
            stylesheet: MENU_ITEM_NORMAL,
            action,
            connection_status: None,
        }
    }

    pub fn go_to_submenu(title: TString<'static>, id: DeviceMenuId) -> Self {
        Self::new(title, Some(Action::GoToSubmenu(id)))
    }
    pub fn go_to_subscreen(title: TString<'static>, idx: u8) -> Self {
        Self::new(title, Some(Action::GoTo(idx)))
    }
    pub fn return_msg(title: TString<'static>, msg: DeviceMenuMsg) -> Self {
        Self::new(title, Some(Action::Return(msg)))
    }

    pub fn with_subtext(
        mut self,
        subtext: Option<(TString<'static>, Option<&'static TextStyle>)>,
    ) -> Self {
        self.subtext = subtext;
        self
    }

    pub fn with_subtext_marquee(mut self) -> Self {
        self.subtext_marquee = true;
        self
    }

    pub fn with_connection_status(mut self, connection_status: Option<bool>) -> Self {
        self.connection_status = connection_status;
        self
    }

    pub fn error(mut self) -> Self {
        self.stylesheet = MENU_ITEM_ERROR;
        self
    }

    pub fn warn(mut self) -> Self {
        self.stylesheet = MENU_ITEM_WARNING;
        self
    }

    pub fn light_warn(mut self) -> Self {
        self.stylesheet = MENU_ITEM_LIGHT_WARNING;
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
    Submenu(u8, DeviceMenuId),

    // A screen allowing the user to to disconnect a device
    DeviceScreen(
        TString<'static>, /* device name */
        bool,             /* is the device connected? */
        u8,               /* index in the list of devices */
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
    submenu_index: [Option<u8>; MAX_SUBMENUS],

    // index of the current subscreen in the list of subscreens
    active_subscreen: u8,
}

impl DeviceMenuScreen {
    #[allow(clippy::too_many_arguments)]
    pub fn new(
        init_submenu: Option<u8>,
        failed_backup: bool,
        paired_devices: Vec<TString<'static>, MAX_PAIRED_DEVICES>,
        connected_idx: Option<u8>,
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

        let is_connected = connected_idx.is_some_and(|idx| usize::from(idx) < paired_devices.len());
        let connected_subtext: Option<TString<'static>> =
            is_connected.then_some(TR::words__connected.into());

        let mut submenu_indices: Vec<u8, MAX_PAIRED_DEVICES> = Vec::new();
        for (i, device) in (0u8..).zip(paired_devices.iter()) {
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
        self.submenu_index[usize::from(id)] = Some(subscreen_idx);
    }

    #[inline]
    fn try_resolve_submenu(&self, id: DeviceMenuId) -> Option<u8> {
        self.submenu_index[usize::from(id)]
    }

    #[inline]
    fn has_submenu(&self, id: DeviceMenuId) -> bool {
        self.try_resolve_submenu(id).is_some()
    }

    fn register_pair_and_connect_menu(
        &mut self,
        paired_devices: Vec<TString<'static>, MAX_PAIRED_DEVICES>,
        submenu_indices: Vec<u8, MAX_PAIRED_DEVICES>,
        connected_idx: Option<u8>,
    ) {
        let mut items: Vec<MenuItem, MEDIUM_MENU_ITEMS> = Vec::new();
        for (device_idx, (device, submenu_idx)) in
            (0u8..).zip(paired_devices.iter().zip(submenu_indices))
        {
            let connection_status = match connected_idx {
                Some(idx) if idx == device_idx => Some(true),
                _ => Some(false),
            };
            let item_device = MenuItem::go_to_subscreen(*device, submenu_idx)
                .with_connection_status(connection_status);
            items.add(item_device);
        }

        items.add(MenuItem::return_msg(
            TR::ble__pair_new.into(),
            DeviceMenuMsg::DevicePair,
        ));
        let unpair_all_item =
            MenuItem::return_msg(TR::ble__forget_all.into(), DeviceMenuMsg::DeviceUnpairAll).warn();
        items.add(unpair_all_item);

        self.register_submenu(DeviceMenuId::PairAndConnect, Submenu::new(items));
    }

    fn register_settings_menu(&mut self) {
        let mut items: Vec<MenuItem, MEDIUM_MENU_ITEMS> = Vec::new();

        if self.has_submenu(DeviceMenuId::Security) {
            items.add(MenuItem::go_to_submenu(
                TR::words__security.into(),
                DeviceMenuId::Security,
            ));
        }

        if self.has_submenu(DeviceMenuId::Device) {
            items.add(MenuItem::go_to_submenu(
                TR::words__device.into(),
                DeviceMenuId::Device,
            ));
        }

        self.register_submenu(DeviceMenuId::Settings, Submenu::new(items));
    }

    fn register_power_menu(&mut self) {
        let mut items: Vec<MenuItem, MEDIUM_MENU_ITEMS> = Vec::new();
        items.add(MenuItem::return_msg(
            TR::buttons__reboot.into(),
            DeviceMenuMsg::Reboot,
        ));
        items.add(MenuItem::return_msg(
            TR::buttons__power_off.into(),
            DeviceMenuMsg::PowerOff,
        ));
        items.add(MenuItem::return_msg(
            TR::reboot_to_bootloader__title.into(),
            DeviceMenuMsg::RebootToBootloader,
        ));

        self.register_submenu(DeviceMenuId::Power, Submenu::new(items));
    }

    fn register_code_menu(&mut self, wipe_code: bool) {
        let mut items: Vec<MenuItem, MEDIUM_MENU_ITEMS> = Vec::new();
        let change_text = match wipe_code {
            true => TR::wipe_code__change,
            false => TR::pin__change,
        }
        .into();
        let change_msg = match wipe_code {
            true => DeviceMenuMsg::WipeCode,
            false => DeviceMenuMsg::PinCode,
        };
        let change_pin_item = MenuItem::return_msg(change_text, change_msg);
        items.add(change_pin_item);

        let remove_text = match wipe_code {
            true => TR::wipe_code__remove,
            false => TR::pin__remove,
        }
        .into();
        let remove_msg = match wipe_code {
            true => DeviceMenuMsg::WipeRemove,
            false => DeviceMenuMsg::PinRemove,
        };
        let remove_pin_item = MenuItem::return_msg(remove_text, remove_msg).warn();
        items.add(remove_pin_item);

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
            let item = if pin_code {
                self.register_code_menu(false);
                MenuItem::go_to_submenu(TR::pin__title.into(), DeviceMenuId::PinCode).with_subtext(
                    Some((
                        TR::words__enabled.into(),
                        Some(&theme::TEXT_MENU_ITEM_SUBTITLE_GREEN),
                    )),
                )
            } else {
                MenuItem::return_msg(TR::pin__title.into(), DeviceMenuMsg::PinCode)
                    .with_subtext(Some((TR::words__disabled.into(), None)))
            };
            items.add(item);
        }

        if let Some(auto_lock_delay) = auto_lock_delay {
            let auto_lock_delay_item =
                MenuItem::return_msg(TR::auto_lock__title.into(), DeviceMenuMsg::AutoLockDelay)
                    .with_subtext(Some((auto_lock_delay, None)));
            items.add(auto_lock_delay_item);
        }

        if let Some(wipe_code) = wipe_code {
            let item = if wipe_code {
                self.register_code_menu(true);
                MenuItem::go_to_submenu(TR::wipe_code__title.into(), DeviceMenuId::WipeCode)
                    .with_subtext(Some((
                        TR::words__enabled.into(),
                        Some(&theme::TEXT_MENU_ITEM_SUBTITLE_GREEN),
                    )))
            } else {
                MenuItem::return_msg(TR::wipe_code__title.into(), DeviceMenuMsg::WipeCode)
                    .with_subtext(Some((TR::words__disabled.into(), None)))
            };
            items.add(item);
        }

        if check_backup {
            items.add(MenuItem::return_msg(
                TR::reset__check_backup_title.into(),
                DeviceMenuMsg::CheckBackup,
            ));
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
            let item_device_name =
                MenuItem::return_msg(TR::words__name.into(), DeviceMenuMsg::DeviceName)
                    .with_subtext(Some((device_name, None)))
                    .with_subtext_marquee();
            items.add(item_device_name);
        }

        if let Some(brightness) = screen_brightness {
            let brightness_item = MenuItem::return_msg(brightness, DeviceMenuMsg::ScreenBrightness);
            items.add(brightness_item);
        }

        if let Some(haptic_feedback) = haptic_feedback {
            let subtext = match haptic_feedback {
                true => (
                    TR::words__on.into(),
                    Some(&theme::TEXT_MENU_ITEM_SUBTITLE_GREEN),
                ),
                _ => (TR::words__off.into(), None),
            };
            let haptic_item = MenuItem::return_msg(
                TR::haptic_feedback__title.into(),
                DeviceMenuMsg::HapticFeedback,
            )
            .with_subtext(Some(subtext));
            items.add(haptic_item);
        }

        if let Some(led_enabled) = led_enabled {
            let subtext = match led_enabled {
                true => (
                    TR::words__on.into(),
                    Some(&theme::TEXT_MENU_ITEM_SUBTITLE_GREEN),
                ),
                _ => (TR::words__off.into(), None),
            };
            let led_item = MenuItem::return_msg(TR::words__led.into(), DeviceMenuMsg::LedEnabled)
                .with_subtext(Some(subtext));
            items.add(led_item);
        }

        let regulatory_index = self.add_subscreen(Subscreen::RegulatoryScreen);
        items.add(MenuItem::go_to_subscreen(
            TR::regulatory_certification__title.into(),
            regulatory_index,
        ));

        let about_index = self.add_subscreen(Subscreen::AboutScreen);
        items.add(MenuItem::go_to_subscreen(
            TR::words__about.into(),
            about_index,
        ));

        let wipe_device_item =
            MenuItem::return_msg(TR::wipe__title.into(), DeviceMenuMsg::WipeDevice).warn();
        items.add(wipe_device_item);

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
            let item = MenuItem::return_msg(
                TR::homescreen__title_backup_failed.into(),
                DeviceMenuMsg::BackupFailed,
            )
            .with_subtext(Some((TR::words__review.into(), None)))
            .error();
            items.add(item);
        }

        if pin_unset {
            let item = MenuItem::return_msg(
                TR::homescreen__title_pin_not_set.into(),
                DeviceMenuMsg::PinCode,
            )
            .with_subtext(Some((TR::words__set.into(), None)))
            .light_warn();
            items.add(item);
        }

        if self.has_submenu(DeviceMenuId::PairAndConnect) {
            let it =
                MenuItem::go_to_submenu(TR::ble__pair_title.into(), DeviceMenuId::PairAndConnect)
                    .with_subtext(
                        connected_subtext.map(|t| (t, Some(&theme::TEXT_MENU_ITEM_SUBTITLE_GREEN))),
                    );
            items.add(it);
        }

        if self.has_submenu(DeviceMenuId::Settings) {
            items.add(MenuItem::go_to_submenu(
                TR::words__settings.into(),
                DeviceMenuId::Settings,
            ));
        }

        if self.has_submenu(DeviceMenuId::Power) {
            items.add(MenuItem::go_to_submenu(
                TR::words__power.into(),
                DeviceMenuId::Power,
            ));
        }

        self.register_submenu(DeviceMenuId::Root, Submenu::new(items).with_battery());
    }

    fn add_submenu(&mut self, submenu: Submenu) -> u8 {
        unwrap!(self.submenus.push(submenu));
        self.submenus.len() as u8 - 1
    }

    fn add_subscreen(&mut self, screen: Subscreen) -> u8 {
        unwrap!(self.subscreens.push(screen));
        self.subscreens.len() as u8 - 1
    }

    fn set_active_subscreen(&mut self, idx: u8) {
        assert!(usize::from(idx) < self.subscreens.len());
        self.active_subscreen = idx;
        self.build_active_subscreen();
    }

    fn activate_subscreen(&mut self, idx: u8, ctx: &mut EventCtx) {
        self.set_active_subscreen(idx);
        self.place(self.bounds);
        if let ActiveScreen::Menu(screen, ..) = self.active_screen.deref_mut() {
            screen.initialize_screen(ctx);
        }
    }

    fn build_active_subscreen(&mut self) {
        match self.subscreens[usize::from(self.active_subscreen)] {
            Subscreen::Submenu(submenu_index, id) => {
                let submenu = &self.submenus[usize::from(submenu_index)];
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

    fn handle_submenu(&mut self, ctx: &mut EventCtx, idx: u8) -> Option<DeviceMenuMsg> {
        match self.subscreens[usize::from(self.active_subscreen)] {
            Subscreen::Submenu(submenu_index, ..) => {
                match self.submenus[usize::from(submenu_index)].items[usize::from(idx)].action {
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
        let parent = match self.subscreens[usize::from(self.active_subscreen)] {
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
        let subscreen = &self.subscreens[usize::from(self.active_subscreen)];
        match (subscreen, self.active_screen.deref_mut()) {
            (Subscreen::Submenu(..), ActiveScreen::Menu(menu, ..)) => {
                match menu.event(ctx, event) {
                    Some(VerticalMenuScreenMsg::Selected(button_idx)) => {
                        return self.handle_submenu(ctx, button_idx as u8);
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
