#[cfg(feature = "micropython")]
mod micropython;

use crate::error::Error;
use core::mem::size_of;

use super::{ffi, model};

pub const ADV_NAME_LEN: usize = ffi::BLE_ADV_NAME_LEN as usize;
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

fn state() -> ffi::ble_state_t {
    let mut state = ffi::ble_state_t {
        connected: false,
        peer_count: 0,
        connectable: false,
        pairing: false,
        pairing_requested: false,
        state_known: false,
    };
    unsafe { ffi::ble_get_state(&mut state as _) };
    state
}

fn issue_command(
    cmd_type: ffi::ble_command_type_t,
    cmd_data: ffi::ble_command_data_t,
) -> Result<(), Error> {
    let data_len = match cmd_type {
        ffi::ble_command_type_t_BLE_ALLOW_PAIRING => PAIRING_CODE_LEN,
        ffi::ble_command_type_t_BLE_PAIRING_MODE | ffi::ble_command_type_t_BLE_SWITCH_ON => {
            size_of::<ffi::ble_adv_start_cmd_data_t>()
        }
        _ => 0,
    };
    let mut cmd = ffi::ble_command_t {
        cmd_type,
        data_len: unwrap!(data_len.try_into()),
        data: cmd_data,
    };
    if unsafe { ffi::ble_issue_command(&mut cmd as _) } {
        Ok(())
    } else {
        Err(COMMAND_FAILED)
    }
}

fn data_advname(name: &str) -> ffi::ble_command_data_t {
    let mut data = ffi::ble_command_data_t {
        adv_start: ffi::ble_adv_start_cmd_data_t {
            name: [0u8; ADV_NAME_LEN],
            static_mac: false,
        },
    };
    let bytes = prefix_utf8_bytes(name, ADV_NAME_LEN);
    unsafe {
        data.adv_start.name[..bytes.len()].copy_from_slice(bytes);
    }
    data
}

fn data_code(mut code: u32) -> ffi::ble_command_data_t {
    let mut pairing_code: [u8; PAIRING_CODE_LEN] = [0; PAIRING_CODE_LEN];
    for i in (0..PAIRING_CODE_LEN).rev() {
        let digit = b'0' + ((code % 10) as u8);
        code /= 10;
        pairing_code[i] = digit;
    }
    ffi::ble_command_data_t { pairing_code }
}

const fn data_none() -> ffi::ble_command_data_t {
    ffi::ble_command_data_t { raw: [0; 32] }
}

pub fn pairing_mode(name: &str) -> Result<(), Error> {
    issue_command(ffi::ble_command_type_t_BLE_PAIRING_MODE, data_advname(name))
}

pub fn connectable_mode(name: &str) -> Result<(), Error> {
    issue_command(ffi::ble_command_type_t_BLE_SWITCH_ON, data_advname(name))
}

pub fn stop_advertising() -> Result<(), Error> {
    issue_command(ffi::ble_command_type_t_BLE_SWITCH_OFF, data_none())
}

pub fn allow_pairing(code: u32) -> Result<(), Error> {
    issue_command(ffi::ble_command_type_t_BLE_ALLOW_PAIRING, data_code(code))
}

pub fn reject_pairing() -> Result<(), Error> {
    issue_command(ffi::ble_command_type_t_BLE_REJECT_PAIRING, data_none())
}

pub fn erase_bonds() -> Result<(), Error> {
    issue_command(ffi::ble_command_type_t_BLE_ERASE_BONDS, data_none())
}

pub fn unpair() -> Result<(), Error> {
    issue_command(ffi::ble_command_type_t_BLE_UNPAIR, data_none())
}

pub fn disconnect() -> Result<(), Error> {
    issue_command(ffi::ble_command_type_t_BLE_DISCONNECT, data_none())
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
