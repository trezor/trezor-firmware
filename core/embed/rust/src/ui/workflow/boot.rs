use crate::{
    trezorhal::storage::{ensure_not_wipe_pin, get_pin_remaining, has_pin, init, unlock},
    ui::{
        display,
        layout::native::RustLayout,
        model::component::{PinKeyboard, PinKeyboardMsg},
    },
};
use heapless::String;

#[cfg(feature = "sd_card")]
use crate::sdsalt::sd_card;
#[cfg(all(feature = "ui_debug", not(feature = "emulator")))]
use crate::trezorhal::storage::wipe;
use crate::{
    micropython::buffer::StrBuffer,
    storage::{get_device_name, get_rotation, get_sd_salt_auth_key, init_unlocked},
    trezorhal::storage::set_pin_delay_callback,
};

pub enum BootState {
    NotConnected,
    RepeatPinEntry,
}

#[cfg(not(feature = "sd_card"))]
use crate::trezorhal::storage::ExternalSalt;
use crate::ui::{model::component::Lockscreen, workflow::pin::show_pin_timeout};

#[cfg(not(feature = "sd_card"))]
fn sd_card(_: &[u8]) -> Option<ExternalSalt> {
    None
}

pub fn boot_workflow() {
    init();

    #[cfg(all(feature = "ui_debug", not(feature = "emulator")))]
    wipe();

    let mut state = BootState::NotConnected;

    let sd_salt_auth_key = get_sd_salt_auth_key();

    if !(has_pin() || sd_salt_auth_key.is_some()) {
        unlock("", None);
        init_unlocked();
        set_pin_delay_callback(show_pin_timeout);
        return;
    }

    set_pin_delay_callback(show_pin_timeout);

    let device_name = get_device_name();

    let rotation = get_rotation();

    display::set_orientation(rotation as _);

    let mut homescreen = RustLayout::new(Lockscreen::new(device_name.as_str(), true, false));

    let mut sd_salt = None;

    loop {
        match state {
            BootState::NotConnected => {
                loop {
                    homescreen.process();
                    if let Some(key) = sd_salt_auth_key.as_ref() {
                        let res = sd_card(key.as_slice());
                        if res.is_none() {
                            homescreen =
                                RustLayout::new(Lockscreen::new(device_name.as_str(), true, false));
                            continue;
                        }
                        sd_salt = res;
                    };

                    if has_pin() {
                        let mut remaining: String<16> = String::from(get_pin_remaining());
                        unwrap!(remaining.push_str(" tries left"));
                        let mut pin = RustLayout::new(PinKeyboard::<StrBuffer>::new(
                            "Enter PIN".into(),
                            unsafe {
                                StrBuffer::from_ptr_and_len(remaining.as_ptr(), remaining.len())
                            },
                            None,
                            true,
                        ));

                        let msg = pin.process();

                        match msg {
                            PinKeyboardMsg::Confirmed => {
                                let pin_str = pin.inner().pin();

                                // todo replicating upy behavior, but unnecessary call?
                                ensure_not_wipe_pin(pin_str);

                                let unlocked = unlock(pin_str, sd_salt.as_ref());
                                if unlocked {
                                    init_unlocked();
                                    return;
                                } else {
                                    state = BootState::RepeatPinEntry;
                                    break;
                                }
                            }
                            PinKeyboardMsg::Cancelled => {
                                homescreen = RustLayout::new(Lockscreen::new(
                                    device_name.as_str(),
                                    true,
                                    false,
                                ));
                            }
                        }
                    } else {
                        let unlocked = unlock("", sd_salt.as_ref());
                        if unlocked {
                            init_unlocked();
                            return;
                        } else {
                            // shouldn't happen, the SD salt was already evaluated to be correct
                            // nothing else to do, shutdown
                            fatal_error!("Wrong SD salt", "Wrong SD salt, reboot the device")
                        }
                    }
                }
            }
            BootState::RepeatPinEntry => loop {
                let mut remaining: String<16> = String::from(get_pin_remaining());
                unwrap!(remaining.push_str(" tries left"));
                let mut pin = RustLayout::new(PinKeyboard::<StrBuffer>::new(
                    "Wrong PIN".into(),
                    unsafe { StrBuffer::from_ptr_and_len(remaining.as_ptr(), remaining.len()) },
                    None,
                    true,
                ));

                let msg = pin.process();
                match msg {
                    PinKeyboardMsg::Confirmed => {
                        let pin_str = pin.inner().pin();
                        let unlocked = unlock(pin_str, sd_salt.as_ref());
                        if unlocked {
                            init_unlocked();
                            return;
                        }
                    }
                    PinKeyboardMsg::Cancelled => {
                        homescreen =
                            RustLayout::new(Lockscreen::new(device_name.as_str(), true, false));
                        state = BootState::NotConnected;
                        break;
                    }
                }
            },
        }
    }
}
