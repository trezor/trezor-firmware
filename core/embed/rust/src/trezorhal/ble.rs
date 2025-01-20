use super::ffi;

pub fn connected() -> bool {
    unsafe {
        let mut state = ffi::ble_state_t {
            connected: false,
            peer_count: 0,
            connectable: false,
            pairing: false,
            pairing_requested: false,
        };
        ffi::ble_get_state(&mut state as _);

        state.connected
    }
}

pub fn pairing_mode(name: &str) {
    unsafe {
        let mut cmd = ffi::ble_command_t {
            cmd_type: ffi::ble_command_type_t_BLE_PAIRING_MODE,
            data_len: 0,
            data: ffi::ble_command_data_t { raw: [0; 32] },
        };

        let bytes = name.as_bytes();

        // Determine how many bytes we can copy (min of buffer size and string length).
        let len = bytes.len().min(cmd.data.name.len());

        cmd.data.name[..len].copy_from_slice(&bytes[..len]);

        ffi::ble_issue_command(&mut cmd as _);
    }
}

pub fn allow_pairing() {
    unsafe {
        let mut cmd = ffi::ble_command_t {
            cmd_type: ffi::ble_command_type_t_BLE_ALLOW_PAIRING,
            data_len: 0,
            data: ffi::ble_command_data_t { raw: [0; 32] },
        };
        ffi::ble_issue_command(&mut cmd as _);
    }
}

pub fn reject_pairing() {
    unsafe {
        let mut cmd = ffi::ble_command_t {
            cmd_type: ffi::ble_command_type_t_BLE_REJECT_PAIRING,
            data_len: 0,
            data: ffi::ble_command_data_t { raw: [0; 32] },
        };
        ffi::ble_issue_command(&mut cmd as _);
    }
}
