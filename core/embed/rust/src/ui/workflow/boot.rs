use core::slice;
use cstr_core::CStr;
use heapless::String;
use crate::trezorhal::alloc::alloc_only;
use crate::trezorhal::storage::{storage_get, storage_get_length, storage_get_remaining, storage_init, storage_unlock, storage_wipe};
use crate::ui::{constant, display, Homescreen, HomescreenMsg, PinKeyboard, PinKeyboardMsg};
use crate::ui::constant::screen;
use crate::ui::geometry::{Point, Rect};
use crate::ui::layout::native::RustLayout;
use crate::ui::model_tt::theme;

pub enum BootState {
    NotInitialized,
    NotConnected,
    RepeatPinEntry,
    Locked,
    Unlocked,
}

static mut PREV_SECONDS: u32 = 0xFFFFFFFF;
static mut PREV_PROGRESS: u32 = 0xFFFFFFFF;


unsafe extern "C" fn show_pin_timeout(seconds: u32, progress: u32, message: *const u8) -> u32 {
    unsafe {

        //todo
        // if callable(keepalive_callback):
        //     keepalive_callback()

        if progress == 0 {
            if progress != PREV_PROGRESS {
                display::rect_fill(screen(), theme::BG);
                PREV_SECONDS = 0xFFFFFFFF;
            }

            let msg = CStr::from_ptr(message as _).to_str().unwrap();
            display::text_center(Point::new(screen().center().x, 37), msg, theme::FONT_BOLD, theme::FG, theme::BG);
        }

        if progress != PREV_PROGRESS {
            display::loader(progress as _, 0, theme::FG, theme::BG, None);
        }

        let mut s : String<16> = String::new();

        if seconds != PREV_SECONDS {
            match seconds {
                0 => {unwrap!(s.push_str("Done"))}
                1 => {unwrap!(s.push_str("1 second left"))}
                _ => {
                    let sec: String<16> = String::from(seconds);
                    unwrap!(s.push_str(sec.as_str()));
                    unwrap!(s.push_str(" seconds left"))
                }
            };

            display::rect_fill(Rect::new(
                Point::new(0, constant::HEIGHT - 42),
                Point::new(constant::WIDTH, constant::HEIGHT - 42 + 25)),
                               theme::BG,
            );
            display::text_center(Point::new(screen().center().x, constant::HEIGHT - 22),
                                 s.as_str(),
                                 theme::FONT_BOLD,
                                 theme::FG,
                                 theme::BG,
            );
        }

        display::pixeldata_dirty();

        PREV_SECONDS = seconds;
        PREV_PROGRESS = progress;

    }
    0
}


pub fn boot_workflow() {


    storage_init(Some(show_pin_timeout));

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

    let avatar: &[u8] = if let Ok(len) = avatar_len_res {
        let mut data = alloc_only(len);
        storage_get(0x8106, &mut data).unwrap();
        data
    } else {
        theme::IMAGE_HOMESCREEN
    };

    let rotation_len_res = storage_get_length(0x810F);
    let rotation: u16 = if let Ok(len) = rotation_len_res {
        let mut data = [0;2];
        storage_get(0x810F, &mut data).unwrap();
        u16::from_be_bytes(data)
    } else {
        0
    };

    display::set_orientation(rotation as _);


    let mut homescreen = RustLayout::new(Homescreen::new(device_name.as_str(), avatar));

    loop {
        match state {
            BootState::NotInitialized => {}
            BootState::NotConnected => {
                loop {
                    let msg = homescreen.process();
                    if let HomescreenMsg::UnlockRequested = msg {
                        let remaining: String<16> = String::from(storage_get_remaining());
                        let mut pin = RustLayout::new(PinKeyboard::new(
                            "Enter your PIN",
                            remaining.as_str(),
                            None,
                            true,
                        ));

                        let msg = pin.process();

                        match msg {
                            PinKeyboardMsg::Confirmed => {
                                let pin_str = pin.inner().pin();
                                let unlocked = storage_unlock(pin_str);
                                if unlocked {
                                    homescreen = RustLayout::new(Homescreen::new("Unlocked", avatar));
                                    state = BootState::Unlocked;
                                    break;
                                } else {
                                    state = BootState::RepeatPinEntry;
                                    break;
                                }
                            }
                            PinKeyboardMsg::Cancelled => {
                                homescreen = RustLayout::new(Homescreen::new(device_name.as_str(), avatar));
                            }

                        }
                    }
                }
            }
            BootState::RepeatPinEntry => {
                loop {
                    let remaining: String<16> = String::from(storage_get_remaining());
                    let mut pin = RustLayout::new(PinKeyboard::new(
                        "Wrong PIN, enter again",
                        remaining.as_str(),
                        None,
                        true
                    ));

                    let msg = pin.process();
                    match msg {
                        PinKeyboardMsg::Confirmed => {
                            let pin_str = pin.inner().pin();
                            let unlocked = storage_unlock(pin_str);
                            if unlocked {
                                homescreen = RustLayout::new(Homescreen::new("Unlocked", avatar));
                                state = BootState::NotConnected;
                                break;
                            }
                        }
                        PinKeyboardMsg::Cancelled => {
                            homescreen = RustLayout::new(Homescreen::new("Unlocked", avatar));
                            state = BootState::NotConnected;
                            break;
                        }
                    }
                }
            }
            BootState::Locked => {}
            BootState::Unlocked => {
                homescreen.process_and_finish();
                break;
            }
        }
    }
}
