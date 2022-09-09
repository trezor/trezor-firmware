use cstr_core::CStr;
use heapless::{String, Vec};
use crate::trezorhal::alloc::alloc_only;
use crate::trezorhal::storage::{storage_delete, storage_ensure_not_wipe_pin, storage_get, storage_get_length, storage_get_remaining, storage_has_pin, storage_init, storage_set, storage_set_counter, storage_unlock};
use crate::ui::{display, LockScreen, LockScreenMsg, PinKeyboard, PinKeyboardMsg, pin::show_pin_timeout};
use crate::ui::layout::native::RustLayout;

pub enum BootState {
    NotInitialized,
    NotConnected,
    RepeatPinEntry,
}



pub fn get_flag(key: u16) -> bool {

    let mut buf = [0u8];
    let len = storage_get(key, &mut buf);
    if matches!(len, Ok(1)) {
        return buf[0] != 0;
    }
    false
}

fn migrate_from_version_01() {

    // Make the U2F counter public and writable even when storage is locked.
    // U2F counter wasn't public, so we are intentionally not using storage.device module.
    let mut data: [u8;4] = [0;4];
    let counter_res = storage_get(0x109, &mut data);
    if let Ok(_) = counter_res {
        let counter = u32::from_be_bytes(data);

        unwrap!(storage_set_counter(0xC109, counter));
        // Delete the old, non-public U2F_COUNTER.
        storage_delete(0x109);
    }
    unwrap!(storage_set(0x101, &[2;1]));
}


fn init_unlocked() {

    let len_res = storage_get_length(0x101);

    if let Ok(_) = len_res {
        // Check for storage version upgrade.
        let mut data: [u8;1] = [0;1];
        unwrap!(storage_get(0x101, &mut data));

        //todo constant
        if data[0] == 1 {
            migrate_from_version_01();
        }

        // In FWs <= 2.3.1 'version' denoted whether the device is initialized or not.
        // In 2.3.2 we have introduced a new field 'initialized' for that.
        if get_flag(0x101) && !get_flag(0x8113) {
            unwrap!(storage_set(0x8113, &[1;1]));
        }
    }

}


pub fn boot_workflow() {


    storage_init(show_pin_timeout);

    //todo if debug and not emulator
    //storage_wipe();

    let mut state = BootState::NotConnected;

    let device_name_len_res = storage_get_length(0x8104);

    let device_name: String<16> = if let Ok(len) = device_name_len_res {
        let mut data: [u8; 17] =[0;17];
        storage_get(0x8104, &mut data).unwrap();
        let text = unsafe {
            CStr::from_bytes_with_nul_unchecked(&data[..=len])
                .to_str()
                .unwrap()
        };
        String::from(text)
    } else {
        String::from("My Trezor")
    };

    let avatar_len_res = storage_get_length(0x8106);

    let avatar: Option<&[u8]> = if let Ok(len) = avatar_len_res {
        let mut data = alloc_only(len);
        storage_get(0x8106, &mut data).unwrap();
        Some(data)
    } else {
        None
    };

    let rotation_len_res = storage_get_length(0x810F);
    let rotation: u16 = if let Ok(_) = rotation_len_res {
        let mut data = [0;2];
        storage_get(0x810F, &mut data).unwrap();
        u16::from_be_bytes(data)
    } else {
        0
    };

    display::set_orientation(rotation as _);

    let sd_salt_res = storage_get_length(0x810F);
    let sd_salt_auth_key: Option<Vec<u8, 16>> = if let Ok(sd_salt_len) = sd_salt_res {
        let mut data = [0;16];
        storage_get(0x8112, &mut data).unwrap();
        Some(unwrap!(Vec::from_slice(&data)))
    } else {
        None
    };

    if !(storage_has_pin() || sd_salt_auth_key.is_some()){
        return;
    }

    let mut homescreen = RustLayout::new(
        LockScreen::new(
            device_name.as_str(),
             avatar,
            Some("Not connected"),
            Some("Tap to connect"),
        )
    );

    loop {
        match state {
            BootState::NotInitialized => {}
            BootState::NotConnected => {
                loop {
                    let msg = homescreen.process();
                    if let LockScreenMsg::UnlockRequested = msg {
                        let mut remaining: String<16> = String::from(storage_get_remaining());
                        unwrap!(remaining.push_str(" tries left"));
                        let mut pin = RustLayout::new(PinKeyboard::new(
                            "Enter PIN",
                            remaining.as_str(),
                            None,
                            true,
                        ));

                        let msg = pin.process();

                        match msg {
                            PinKeyboardMsg::Confirmed => {
                                let pin_str = pin.inner().pin();

                                // todo replicating upy behavior, but unnecessary call?
                                storage_ensure_not_wipe_pin(pin_str);

                                let unlocked = storage_unlock(pin_str);
                                if unlocked {
                                    init_unlocked();
                                    return;
                                } else {
                                    state = BootState::RepeatPinEntry;
                                    break;
                                }
                            }
                            PinKeyboardMsg::Cancelled => {
                                homescreen = RustLayout::new(LockScreen::new(
                                    device_name.as_str(),
                                    avatar,
                                    Some("Not connected"),
                                    Some("Tap to connect")));
                            }
                        }
                    }
                }
            }
            BootState::RepeatPinEntry => {
                loop {
                    let mut remaining: String<16> = String::from(storage_get_remaining());
                    unwrap!(remaining.push_str(" tries left"));
                    let mut pin = RustLayout::new(PinKeyboard::new(
                        "Wrong PIN",
                        remaining.as_str(),
                        None,
                        true
                    ));

                    let msg = pin.process();
                    match msg {
                        PinKeyboardMsg::Confirmed => {
                            let pin_str = pin.inner().pin();
                            let unlocked = storage_unlock(pin_str);
                            if unlocked
                            {
                                init_unlocked();
                                return;
                            }
                        }
                        PinKeyboardMsg::Cancelled => {
                            homescreen = RustLayout::new(LockScreen::new(device_name.as_str(), avatar,
                                                                         Some("Not connected"),
                                                                         Some("Tap to connect")));
                            state = BootState::NotConnected;
                            break;
                        }
                    }
                }
            }
        }
    }
}
