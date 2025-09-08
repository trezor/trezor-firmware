#[cfg(feature = "micropython")]
mod micropython;

#[cfg(feature = "ui")]
use crate::ui::event::BLEEvent;

use super::ffi;
use crate::{error::Error, trezorhal::ffi::bt_le_addr_t};
use core::ptr;

pub const ADV_NAME_LEN: usize = ffi::BLE_ADV_NAME_LEN as usize;
pub const BLE_MAX_BONDS: usize = ffi::BLE_MAX_BONDS as usize;
pub const PAIRING_CODE_LEN: usize = ffi::BLE_PAIRING_CODE_LEN as usize;
pub const RX_PACKET_SIZE: usize = ffi::BLE_RX_PACKET_SIZE as usize;
pub const TX_PACKET_SIZE: usize = ffi::BLE_TX_PACKET_SIZE as usize;

const COMMAND_FAILED: Error = Error::RuntimeError(c"BLE command failed");
const WRITE_FAILED: Error = Error::RuntimeError(c"BLE write failed");

// NOTE: replace with floor_char_boundary when stable
fn prefix_utf8_bytes(text: &str, max_len: usize) -> &[u8] {
    let mut i = text.len().min(max_len);
    while !text.is_char_boundary(i) {
        i -= 1;
    }
    &text.as_bytes()[..i]
}

pub fn res_to_result(res: bool) -> Result<(), Error> {
    if res {
        Ok(())
    } else {
        Err(COMMAND_FAILED)
    }
}

#[cfg(feature = "ui")]
pub fn ble_parse_event(event: ffi::ble_event_t) -> BLEEvent {
    match event.type_ {
        ffi::ble_event_type_t_BLE_CONNECTED => BLEEvent::Connected,
        ffi::ble_event_type_t_BLE_DISCONNECTED => BLEEvent::Disconnected,
        ffi::ble_event_type_t_BLE_PAIRING_REQUEST => {
            let code: u32 = event
                .data
                .iter()
                .take(6)
                .map(|&b| (b - b'0'))
                .fold(0, |acc, d| acc * 10 + d as u32);
            BLEEvent::PairingRequest(code)
        }
        ffi::ble_event_type_t_BLE_PAIRING_CANCELLED => BLEEvent::PairingCanceled,
        ffi::ble_event_type_t_BLE_PAIRING_COMPLETED => BLEEvent::PairingCompleted,
        ffi::ble_event_type_t_BLE_PAIRING_NOT_NEEDED => BLEEvent::PairingNotNeeded,
        ffi::ble_event_type_t_BLE_CONNECTION_CHANGED => BLEEvent::ConnectionChanged,
        _ => panic!(),
    }
}

impl bt_le_addr_t {
    fn zero() -> bt_le_addr_t {
        bt_le_addr_t {
            type_: 0,
            addr: [0; 6],
        }
    }

    fn new(type_: u8, addr: [u8; 6]) -> bt_le_addr_t {
        bt_le_addr_t { type_, addr }
    }
}

fn state() -> ffi::ble_state_t {
    let mut state = ffi::ble_state_t {
        connected: false,
        peer_count: 0,
        connectable: false,
        pairing: false,
        pairing_requested: false,
        state_known: false,
        connected_addr: bt_le_addr_t::zero(),
    };
    unsafe { ffi::ble_get_state(&mut state as _) };
    state
}

pub fn pairing_mode(name: &str) -> Result<(), Error> {
    let res = unsafe { ffi::ble_enter_pairing_mode(name.as_ptr(), name.len()) };
    res_to_result(res)
}

pub fn switch_on(name: &str) -> Result<(), Error> {
    unsafe { ffi::ble_set_name(name.as_ptr(), name.len()) };
    let res = unsafe { ffi::ble_switch_on() };
    res_to_result(res)
}

pub fn switch_off() -> Result<(), Error> {
    let res = unsafe { ffi::ble_switch_off() };
    res_to_result(res)
}

pub fn allow_pairing(code: u32) -> Result<(), Error> {
    let mut tmp_code = code;
    let mut pairing_code: [u8; PAIRING_CODE_LEN] = [0; PAIRING_CODE_LEN];
    for i in (0..PAIRING_CODE_LEN).rev() {
        let digit = b'0' + ((tmp_code % 10) as u8);
        tmp_code /= 10;
        pairing_code[i] = digit;
    }

    let res = unsafe { ffi::ble_allow_pairing(pairing_code.as_ptr()) };
    res_to_result(res)
}

pub fn reject_pairing() -> Result<(), Error> {
    let res = unsafe { ffi::ble_reject_pairing() };
    res_to_result(res)
}

pub fn erase_bonds() -> Result<(), Error> {
    let res = unsafe { ffi::ble_erase_bonds() };
    res_to_result(res)
}

pub fn unpair(addr: Option<&bt_le_addr_t>) -> Result<(), Error> {
    let ptr: *const bt_le_addr_t = match addr {
        Some(a) => a as *const bt_le_addr_t,
        None => ptr::null(),
    };

    if !unsafe { ffi::ble_unpair(ptr) } {
        return Err(COMMAND_FAILED);
    }
    Ok(())
}

pub fn disconnect() -> Result<(), Error> {
    let res = unsafe { ffi::ble_disconnect() };
    res_to_result(res)
}

pub fn set_name(name: &str) {
    let bytes = prefix_utf8_bytes(name, ADV_NAME_LEN);
    unsafe { ffi::ble_set_name(bytes.as_ptr(), bytes.len()) }
}

pub fn set_high_speed(enable: bool) {
    unsafe { ffi::ble_set_high_speed(enable) }
}

pub fn start_comm() {
    unsafe { ffi::ble_start() }
}

pub fn peer_count() -> u8 {
    state().peer_count
}

pub fn is_started() -> bool {
    state().state_known
}

pub fn is_connectable() -> bool {
    state().connectable
}

pub fn is_connected() -> bool {
    state().connected
}

pub fn is_pairing() -> bool {
    state().pairing
}

pub fn is_pairing_requested() -> bool {
    state().pairing_requested
}

pub fn connected_addr() -> bt_le_addr_t {
    state().connected_addr
}

pub fn get_bonds<F, T>(f: F) -> T
where
    F: Fn(&[bt_le_addr_t]) -> T,
{
    let mut bonds = [bt_le_addr_t::zero(); BLE_MAX_BONDS];
    let size = unsafe { ffi::ble_get_bond_list(bonds.as_mut_ptr(), bonds.len()) };
    f(&bonds[..size.into()])
}

pub fn write(bytes: &[u8]) -> Result<(), Error> {
    let len = bytes.len() as u16;
    let success = unsafe { ffi::ble_write(bytes.as_ptr(), len) };
    if success {
        Ok(())
    } else {
        Err(WRITE_FAILED)
    }
}

pub fn read(buf: &mut [u8], max_len: usize) -> Result<usize, Error> {
    let len: u16 = max_len.try_into()?;
    let read_len = unsafe { super::ffi::ble_read(buf.as_mut_ptr(), len) };
    Ok(read_len.try_into()?)
}
