#![allow(unused_imports)]

use super::ffi;
use core::mem;

use crate::ui::component::Event;
pub use ffi::poll_event_t;

#[cfg(feature = "ble")]
use crate::trezorhal::{ble::ble_parse_event, button::button_parse_event};

#[cfg(feature = "touch")]
use crate::ui::event::TouchEvent;
#[cfg(feature = "button")]
use crate::ui::event::{BLEEvent, ButtonEvent};

pub fn parse_event(iface: i16, event: poll_event_t) -> Option<Event> {
    match iface {
        #[cfg(feature = "ble")]
        252 => {
            let ble_event = unsafe { event.event.ble_event };
            let ble_event = ble_parse_event(ble_event);
            Some(Event::BLE(ble_event))
        }
        #[cfg(feature = "button")]
        254 => {
            let btn_event = unsafe { event.event.button_event };
            let (btn, evt) = button_parse_event(btn_event);
            Some(Event::Button(unwrap!(ButtonEvent::new(evt, btn))))
        }
        #[cfg(feature = "touch")]
        255 => {
            let (event_type, ex, ey) = unsafe {
                let event_type = event.event.touch_event >> 24;

                let ex = (event.event.touch_event >> 12) & 0xFFF;
                let ey = event.event.touch_event & 0xFFF;
                (event_type, ex, ey)
            };
            Some(Event::Touch(unwrap!(TouchEvent::new(event_type, ex, ey))))
        }
        _ => None,
    }
}

pub fn poll_event(ifaces: &[u16]) -> Option<Event> {
    //
    // int16_t poll_events(const uint16_t* ifaces, size_t ifaces_num,
    //                     poll_event_t* event, uint32_t timeout_ms);

    let mut e: poll_event_t = unsafe { mem::zeroed() };

    let iface = unsafe { ffi::poll_events(ifaces.as_ptr(), ifaces.len() as _, &mut e, 100) };

    parse_event(iface, e)
}
