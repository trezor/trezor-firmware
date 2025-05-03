#[derive(Default, Copy, Clone, PartialEq, Eq)]
#[cfg_attr(feature = "debug", derive(ufmt::derive::uDebug))]
pub struct PMEvent {
    pub state_changed: bool,
    pub usb_connected: bool,
    pub usb_disconnected: bool,
    pub wireless_connected: bool,
    pub wireless_disconnected: bool,
    pub entered_mode_active: bool,
    pub entered_mode_power_save: bool,
    pub entered_mode_shutting_down: bool,
    pub entered_mode_charging: bool,
    pub entered_mode_suspend: bool,
    pub entered_mode_hibernate: bool,
    pub soc_updated: bool,
}
