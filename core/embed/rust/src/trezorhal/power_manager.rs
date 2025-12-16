use super::ffi;
use core::ptr::null_mut;

#[cfg(feature = "ui")]
use crate::ui::event::PMEvent;

#[derive(PartialEq, Eq, Copy, Clone)]
pub enum ChargingState {
    Discharging,
    Charging,
    Idle,
}

#[cfg(feature = "ui")]
pub fn pm_parse_event(event: ffi::pm_event_t) -> PMEvent {
    let mut pm_event = PMEvent::default();

    unsafe {
        pm_event.usb_connected_changed = event.flags.usb_connected_changed();
        pm_event.wireless_connected_changed = event.flags.wireless_connected_changed();
        pm_event.ntc_connected_changed = event.flags.ntc_connected_changed();
        pm_event.charging_limited_changed = event.flags.charging_limited_changed();
        pm_event.soc_updated = event.flags.soc_updated();
        pm_event.battery_temp_jump_detected = event.flags.battery_temp_jump_detected();
        pm_event.battery_ocv_jump_detected = event.flags.battery_ocv_jump_detected();
        pm_event.charging_status_changed = event.flags.charging_status_changed();
        pm_event.power_status_changed = event.flags.power_status_changed();
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

pub fn is_usb_connected() -> bool {
    let mut state: ffi::pm_state_t = unsafe { core::mem::zeroed() };
    unsafe { ffi::pm_get_state(&mut state as _) };
    state.usb_connected
}

pub fn is_ntc_connected() -> bool {
    let mut state: ffi::pm_state_t = unsafe { core::mem::zeroed() };
    unsafe { ffi::pm_get_state(&mut state as _) };
    state.ntc_connected
}

pub fn is_charging_limited() -> bool {
    let mut state: ffi::pm_state_t = unsafe { core::mem::zeroed() };
    unsafe { ffi::pm_get_state(&mut state as _) };
    state.charging_limited
}

pub fn suspend() {
    unsafe { ffi::pm_suspend(null_mut()) };
}

pub fn hibernate() {
    unsafe { ffi::pm_hibernate() };
}

pub fn charging_enable() {
    unsafe { ffi::pm_charging_enable() };
}
pub fn charging_disable() {
    unsafe { ffi::pm_charging_disable() };
}
