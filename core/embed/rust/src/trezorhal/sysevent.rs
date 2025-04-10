#![allow(unused_imports)]

use super::ffi;
use core::mem;

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

#[cfg(feature = "button")]
use crate::trezorhal::button::button_parse_event;
#[cfg(feature = "button")]
use crate::trezorhal::ffi::button_get_event;
#[cfg(feature = "button")]
use crate::ui::event::ButtonEvent;

#[derive(PartialEq, Debug, Eq, Clone, Copy)]
pub enum Syshandle {
    Button = ffi::syshandle_t_SYSHANDLE_BUTTON as _,
    Touch = ffi::syshandle_t_SYSHANDLE_TOUCH as _,
    Ble = ffi::syshandle_t_SYSHANDLE_BLE as _,
}

pub fn parse_event(signalled: &sysevents_t) -> Option<Event> {
    #[cfg(feature = "ble")]
    if signalled.read_ready & (1 << ffi::syshandle_t_SYSHANDLE_BLE) != 0 {
        let mut ble_event: ffi::ble_event_t = unsafe { mem::zeroed() };
        let event_available = unsafe { ffi::ble_get_event(&mut ble_event) };
        if event_available {
            let ble_event = ble_parse_event(ble_event);
            return Some(Event::BLE(ble_event));
        }
    }
    #[cfg(feature = "button")]
    if signalled.read_ready & (1 << ffi::syshandle_t_SYSHANDLE_BUTTON) != 0 {
        let mut button_event: ffi::button_event_t = unsafe { mem::zeroed() };
        let event_available = unsafe { button_get_event(&mut button_event) };
        if event_available {
            let (btn, evt) = button_parse_event(button_event);
            return Some(Event::Button(unwrap!(ButtonEvent::new(evt, btn))));
        }
    }
    #[cfg(feature = "touch")]
    if signalled.read_ready & (1 << ffi::syshandle_t_SYSHANDLE_TOUCH) != 0 {
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

    None
}

pub fn sysevents_poll(ifaces: &[Syshandle]) -> Option<Event> {
    let mut awaited: sysevents_t = unsafe { mem::zeroed() };

    for i in ifaces {
        let bit: u32 = 1 << *i as u32;
        awaited.read_ready |= bit;
    }

    let mut signalled: sysevents_t = unsafe { mem::zeroed() };

    unsafe { ffi::sysevents_poll(&awaited as _, &mut signalled as _, 100) };

    parse_event(&signalled)
}
