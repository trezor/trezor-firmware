use super::ffi;

use crate::ui::event::PMEvent;

pub enum ChargingState {
    Discharging,
    Charging,
    Idle,
}

pub fn pm_parse_event(event: ffi::pm_event_t) -> PMEvent {
    let mut pm_event = PMEvent::default();

    unsafe {
        pm_event.usb_connected = event.flags.usb_connected();
        pm_event.usb_disconnected = event.flags.usb_disconnected();
        pm_event.wireless_connected = event.flags.wireless_connected();
        pm_event.wireless_disconnected = event.flags.wireless_disconnected();
        pm_event.entered_mode_active = event.flags.entered_mode_active();
        pm_event.entered_mode_power_save = event.flags.entered_mode_power_save();
        pm_event.entered_mode_shutting_down = event.flags.entered_mode_shutting_down();
        pm_event.entered_mode_charging = event.flags.entered_mode_charging();
        pm_event.entered_mode_suspend = event.flags.entered_mode_suspend();
        pm_event.entered_mode_hibernate = event.flags.entered_mode_hibernate();
        pm_event.soc_updated = event.flags.soc_updated();
        pm_event.state_changed = event.flags.state_changed();
    }
    pm_event
}

pub fn soc() -> u8 {
    let mut state: ffi::pm_state_t = unsafe { core::mem::zeroed() };
    unsafe { ffi::pm_get_state(&mut state as _) };
    state.soc
}

pub fn charging_state() -> ChargingState {
    let mut state: ffi::pm_state_t = unsafe { core::mem::zeroed() };
    unsafe { ffi::pm_get_state(&mut state as _) };
    match state.charging_status {
        ffi::pm_charging_status_t_PM_BATTERY_DISCHARGING => ChargingState::Discharging,
        ffi::pm_charging_status_t_PM_BATTERY_CHARGING => ChargingState::Charging,
        ffi::pm_charging_status_t_PM_BATTERY_IDLE => ChargingState::Idle,
        _ => panic!("Unknown charging status"),
    }
}
