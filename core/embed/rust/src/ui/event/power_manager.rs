#[derive(Default, Copy, Clone, PartialEq, Eq)]
#[cfg_attr(feature = "debug", derive(ufmt::derive::uDebug))]
pub struct PMEvent {
    pub power_status_changed: bool,
    pub charging_status_changed: bool,
    pub usb_connected_changed: bool,
    pub wireless_connected_changed: bool,
    pub soc_updated: bool,
}
