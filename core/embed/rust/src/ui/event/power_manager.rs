#[derive(Default, Copy, Clone, PartialEq, Eq)]
#[cfg_attr(feature = "debug", derive(ufmt::derive::uDebug))]
pub struct PMEvent {
    pub power_status_changed: bool,
    pub charging_status_changed: bool,
    pub usb_connected_changed: bool,
    pub wireless_connected_changed: bool,
    pub soc_updated: bool,
}

impl PMEvent {
    pub fn from_packed_flags(flags: u32) -> Self {
        PMEvent {
            power_status_changed: (flags & (1 << 0)) != 0,
            charging_status_changed: (flags & (1 << 1)) != 0,
            usb_connected_changed: (flags & (1 << 2)) != 0,
            wireless_connected_changed: (flags & (1 << 3)) != 0,
            soc_updated: (flags & (1 << 4)) != 0,
        }
    }
}
