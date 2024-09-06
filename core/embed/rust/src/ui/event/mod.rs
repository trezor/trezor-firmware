#[cfg(feature = "button")]
pub mod button;
#[cfg(feature = "touch")]
pub mod touch;

#[cfg(feature = "button")]
pub use button::{ButtonEvent, PhysicalButton};
#[cfg(feature = "touch")]
pub use touch::{SwipeEvent, TouchEvent};

#[derive(Copy, Clone, PartialEq, Eq)]
#[cfg_attr(feature = "debug", derive(ufmt::derive::uDebug))]
pub enum USBEvent {
    /// USB host has connected/disconnected.
    Connected(bool),
}
