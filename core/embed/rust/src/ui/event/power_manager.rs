#[derive(Default, Copy, Clone, PartialEq, Eq)]
pub struct PMEvent {
    pub state_changed: bool,
    pub usb_connected: bool,
    pub usb_disconnected: bool,
    pub wireless_connected: bool,
    pub wireless_disconnected: bool,
    pub entered_mode_active: bool,
    pub entered_mode_power_save: bool,
    pub entered_mode_shutting_down: bool,
    pub soc_updated: bool,
}
