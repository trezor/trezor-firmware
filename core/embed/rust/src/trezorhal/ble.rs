use super::ffi;

pub fn connected() -> bool {
    unsafe {
        let mut state = ffi::ble_state_t {
            connected: false,
            peer_count: 0,
        };
        ffi::ble_get_state(&mut state as _);

        state.connected
    }
}

pub fn pairing_mode() {
    unsafe {
        ffi::ble_issue_command(ffi::ble_command_t_BLE_PAIRING_MODE);
    }
}

pub fn allow_pairing() {
    unsafe {
        ffi::ble_issue_command(ffi::ble_command_t_BLE_ALLOW_PAIRING);
    }
}

pub fn reject_pairing() {
    unsafe {
        ffi::ble_issue_command(ffi::ble_command_t_BLE_REJECT_PAIRING);
    }
}
