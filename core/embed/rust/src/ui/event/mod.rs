#[cfg(feature = "button")]
pub mod button;
#[cfg(feature = "touch")]
pub mod touch;

pub mod usb;

#[cfg(feature = "ble")]
mod ble;

#[cfg(feature = "ble")]
pub use ble::BLEEvent;
#[cfg(feature = "button")]
pub use button::{ButtonEvent, PhysicalButton};
#[cfg(feature = "touch")]
pub use touch::{SwipeEvent, TouchEvent};

pub use usb::USBEvent;
