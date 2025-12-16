#[derive(Default, Copy, Clone, PartialEq, Eq)]
#[cfg_attr(feature = "debug", derive(ufmt::derive::uDebug))]
pub struct PMEvent {
    pub power_status_changed: bool,
    pub charging_status_changed: bool,
    pub usb_connected_changed: bool,
    pub wireless_connected_changed: bool,
    pub ntc_connected_changed: bool,
    pub charging_limited_changed: bool,
    pub battery_temp_jump_detected: bool,
    pub battery_ocv_jump_detected: bool,
    pub soc_updated: bool,
}

impl PMEvent {
    pub fn from_packed_flags(flags: u32) -> Self {
        PMEvent {
            power_status_changed: (flags & (1 << 0)) != 0,
            charging_status_changed: (flags & (1 << 1)) != 0,
            usb_connected_changed: (flags & (1 << 2)) != 0,
            wireless_connected_changed: (flags & (1 << 3)) != 0,
            ntc_connected_changed: (flags & (1 << 4)) != 0,
            charging_limited_changed: (flags & (1 << 5)) != 0,
            battery_temp_jump_detected: (flags & (1 << 6)) != 0,
            battery_ocv_jump_detected: (flags & (1 << 7)) != 0,
            soc_updated: (flags & (1 << 8)) != 0,
        }
    }
}
