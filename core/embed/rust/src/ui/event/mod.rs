#[cfg(feature = "button")]
pub mod button;
#[cfg(feature = "touch")]
pub mod touch;

pub mod usb;

#[cfg(feature = "ble")]
mod ble;

#[cfg(feature = "power_manager")]
mod power_manager;

#[cfg(feature = "ble")]
pub use ble::BLEEvent;
#[cfg(feature = "button")]
pub use button::{ButtonEvent, PhysicalButton};
#[cfg(feature = "power_manager")]
pub use power_manager::PMEvent;
#[cfg(feature = "touch")]
pub use touch::{SwipeEvent, TouchEvent};

pub use usb::USBEvent;
