use super::ffi;

pub fn connected() -> bool {
    unsafe {
        let mut state = ffi::ble_state_t {
            connected: false,
            peer_count: 0,
            connectable: false,
            pairing: false,
            pairing_requested: false,
            state_known: false,
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
        let len = bytes.len().min(cmd.data.adv_start.name.len());

        cmd.data.adv_start.name[..len].copy_from_slice(&bytes[..len]);

        ffi::ble_issue_command(&mut cmd as _);
    }
}

pub fn allow_pairing(mut code: u32) {
    const CODE_LEN: u8 = 6;
    let mut cmd = ffi::ble_command_t {
        cmd_type: ffi::ble_command_type_t_BLE_ALLOW_PAIRING,
        data_len: CODE_LEN,
        data: ffi::ble_command_data_t { raw: [0; 32] },
    };
    unsafe {
        for i in (0..CODE_LEN).rev() {
            let digit = b'0' + ((code % 10) as u8);
            code /= 10;
            cmd.data.raw[i as usize] = digit;
        }
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
