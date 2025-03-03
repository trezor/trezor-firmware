use super::ffi;
use crate::ui::event::BLEEvent;

pub fn ble_parse_event(event: ffi::ble_event_t) -> BLEEvent {
    match event.type_ {
        ffi::ble_event_type_t_BLE_CONNECTED => BLEEvent::Connected,
        ffi::ble_event_type_t_BLE_DISCONNECTED => BLEEvent::Disconnected,
        ffi::ble_event_type_t_BLE_PAIRING_REQUEST => {
            let code: u32 = event.data
                .iter()
                .take(6)
                .map(|&b| (b - b'0'))
                .fold(0, |acc, d| acc * 10 + d as u32);
            BLEEvent::PairingRequest(code)
        }
        ffi::ble_event_type_t_BLE_PAIRING_CANCELLED => BLEEvent::PairingCanceled,
        _ => panic!(),
    }
}

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
