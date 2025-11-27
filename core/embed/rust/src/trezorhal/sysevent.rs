#![allow(unused_imports)]

use super::ffi;
use core::mem::{self, MaybeUninit};

use crate::ui::component::Event;
pub use ffi::{sysevents_t, syshandle_t};

#[cfg(feature = "ble")]
use crate::trezorhal::ble::ble_parse_event;
#[cfg(feature = "ble")]
use crate::ui::event::BLEEvent;

#[cfg(feature = "touch")]
use crate::trezorhal::touch::touch_get_event;
#[cfg(feature = "touch")]
use crate::ui::event::TouchEvent;

#[cfg(feature = "power_manager")]
use crate::trezorhal::power_manager::pm_parse_event;
#[cfg(feature = "power_manager")]
use crate::ui::event::PMEvent;

#[cfg(feature = "button")]
use crate::trezorhal::button::button_parse_event;
#[cfg(feature = "button")]
use crate::trezorhal::ffi::button_get_event;
use crate::trezorhal::time::ticks_ms;
#[cfg(feature = "button")]
use crate::ui::event::ButtonEvent;

#[derive(PartialEq, Debug, Eq, Clone, Copy)]
pub enum Syshandle {
    UsbWire = ffi::syshandle_t_SYSHANDLE_USB_WIRE as _,
    UsbDebug = ffi::syshandle_t_SYSHANDLE_USB_DEBUG as _,
    UsbWebauthn = ffi::syshandle_t_SYSHANDLE_USB_WEBAUTHN as _,
    UsbVcp = ffi::syshandle_t_SYSHANDLE_USB_VCP as _,
    BleIface = ffi::syshandle_t_SYSHANDLE_BLE_IFACE_0 as _,
    PowerManager = ffi::syshandle_t_SYSHANDLE_POWER_MANAGER as _,
    Button = ffi::syshandle_t_SYSHANDLE_BUTTON as _,
    Touch = ffi::syshandle_t_SYSHANDLE_TOUCH as _,
    Usb = ffi::syshandle_t_SYSHANDLE_USB as _,
    Ble = ffi::syshandle_t_SYSHANDLE_BLE as _,
    Syscall = ffi::syshandle_t_SYSHANDLE_SYSCALL as _,
}

impl Syshandle {
    pub fn set_in(self, mask: &mut ffi::syshandle_mask_t) {
        *mask |= 1 << self as u32;
    }

    pub fn is_set_in(self, mask: &ffi::syshandle_mask_t) -> bool {
        mask & (1 << self as u32) != 0
    }
}

#[cfg(feature = "ble")]
impl ffi::ble_event_t {
    pub fn get() -> Option<Self> {
        let mut ble_event = MaybeUninit::zeroed();
        unsafe {
            let event_available = ffi::ble_get_event(ble_event.as_mut_ptr());
            // SAFETY: We only assume_init after the C call returns a success.
            event_available.then_some(ble_event.assume_init())
        }
    }
}

#[cfg(feature = "button")]
impl ffi::button_event_t {
    pub fn get() -> Option<Self> {
        let mut button_event = MaybeUninit::zeroed();
        unsafe {
            let event_available = ffi::button_get_event(button_event.as_mut_ptr());
            // SAFETY: We only assume_init after the C call returns a success.
            event_available.then_some(button_event.assume_init())
        }
    }
}

pub type Sysevents = ffi::sysevents_t;

impl Sysevents {
    pub fn zeroed() -> Self {
        Self {
            read_ready: 0,
            write_ready: 0,
        }
    }

    pub fn reading_from(ifaces: &[Syshandle]) -> Self {
        let mut awaited = Self::zeroed();
        for iface in ifaces {
            iface.set_in(&mut awaited.read_ready);
        }
        awaited
    }

    pub fn writing_to(ifaces: &[Syshandle]) -> Self {
        let mut awaited = Self::zeroed();
        for iface in ifaces {
            iface.set_in(&mut awaited.write_ready);
        }
        awaited
    }
}

pub fn parse_event(signalled: &sysevents_t) -> Option<Event> {
    #[cfg(feature = "ble")]
    if Syshandle::Ble.is_set_in(&signalled.read_ready) {
        if let Some(ble_event) = ffi::ble_event_t::get() {
            let ble_event = ble_parse_event(ble_event);
            return Some(Event::BLE(ble_event));
        }
    }
    #[cfg(feature = "button")]
    if Syshandle::Button.is_set_in(&signalled.read_ready) {
        if let Some(button_event) = ffi::button_event_t::get() {
            let (btn, evt) = button_parse_event(button_event);
            return Some(Event::Button(unwrap!(ButtonEvent::new(evt, btn))));
        }
    }
    #[cfg(feature = "touch")]
    if Syshandle::Touch.is_set_in(&signalled.read_ready) {
        let touch_event = touch_get_event();

        if touch_event != 0 {
            let (event_type, ex, ey) = {
                let event_type = touch_event >> 24;

                let ex = (touch_event >> 12) & 0xFFF;
                let ey = touch_event & 0xFFF;
                (event_type, ex, ey)
            };
            return Some(Event::Touch(unwrap!(TouchEvent::new(event_type, ex, ey))));
        }
    }

    #[cfg(feature = "power_manager")]
    if signalled.read_ready & (1 << ffi::syshandle_t_SYSHANDLE_POWER_MANAGER) != 0 {
        let mut pm_event: ffi::pm_event_t = unsafe { mem::zeroed() };
        let event_available = unsafe { ffi::pm_get_events(&mut pm_event) };
        if event_available {
            let pm_event = pm_parse_event(pm_event);
            return Some(Event::PM(pm_event));
        }
    }

    if signalled.read_ready & (1 << ffi::syshandle_t_SYSHANDLE_USB_DEBUG) != 0 {
        return Some(Event::USBDebug);
    }

    if signalled.read_ready & (1 << ffi::syshandle_t_SYSHANDLE_USB_WIRE) != 0 {
        return Some(Event::USBWire);
    }

    #[cfg(feature = "ble")]
    if signalled.read_ready & (1 << ffi::syshandle_t_SYSHANDLE_BLE_IFACE_0) != 0 {
        return Some(Event::BLEIface);
    }

    None
}

pub fn sysevents_poll(ifaces: &[Syshandle]) -> Option<Event> {
    let awaited = Sysevents::reading_from(ifaces);
    let mut signalled = Sysevents::zeroed();

    // SAFETY: safe.
    unsafe { ffi::sysevents_poll(&awaited as _, &mut signalled as _, ticks_ms() + 100) };

    parse_event(&signalled)
}
