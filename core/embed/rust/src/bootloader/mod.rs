#[cfg(all(feature = "button", feature = "power_manager"))]
use crate::ui::event::ButtonEvent;
#[cfg(feature = "button")]
use crate::ui::layout::simplified::button_eval;

use crate::{
    trezorhal::{
        bootloader::{bootloader_process_usb, BootloaderWFResult},
        sysevent::{sysevents_poll, Syshandle},
    },
    ui::{
        component::{base::AttachType, Component, Event, EventCtx},
        layout::simplified::{render, ReturnToC},
        CommonUI, ModelUI,
    },
};

#[cfg(feature = "ble")]
use crate::trezorhal::bootloader::bootloader_process_ble;

#[cfg(feature = "power_manager")]
use crate::{
    time::Instant,
    trezorhal::power_manager::{hibernate, is_usb_connected, suspend},
    ui::display::fade_backlight_duration,
    ui::event::PhysicalButton,
};

#[cfg(all(feature = "haptic", feature = "power_manager"))]
use crate::trezorhal::haptic::{play, HapticEffect};

#[cfg(feature = "debuglink")]
use crate::trezorhal::bootloader::{
    debuglink_notify_layout_change, debuglink_process, DebuglinkResult,
};

use heapless::Vec;

#[cfg(feature = "power_manager")]
use crate::time::Duration;
#[cfg(feature = "power_manager")]
const FADE_TIME: Duration = Duration::from_millis(30000);
#[cfg(feature = "power_manager")]
const SUSPEND_TIME: Duration = Duration::from_millis(40000);
#[cfg(feature = "power_manager")]
const HIBERNATE_TIME: Duration = Duration::from_millis(3000);

pub fn run(
    frame: &mut impl Component<Msg = impl ReturnToC>,
    fade_transition: bool,
    communication: bool,
) -> (u32, u32) {
    frame.place(ModelUI::SCREEN);

    let e = Event::Attach(AttachType::Initial);
    let mut ctx = EventCtx::new();

    let msg = frame.event(&mut ctx, e);

    if let Some(message) = msg {
        return (
            BootloaderWFResult::OkUiAction.return_to_c(),
            message.return_to_c(),
        );
    }

    if fade_transition {
        ModelUI::fadeout();
    }
    render(frame);
    ModelUI::fadein();

    #[cfg(feature = "debuglink")]
    {
        debuglink_notify_layout_change();
    }

    #[cfg(all(feature = "power_manager", feature = "haptic"))]
    let mut haptic_played = false;
    #[cfg(feature = "power_manager")]
    let mut button_pressed_time = None;
    #[cfg(feature = "power_manager")]
    let mut start = Instant::now();
    let mut faded = false;

    // flush any pending events
    #[cfg(feature = "button")]
    while button_eval().is_some() {}

    let mut ifaces: Vec<Syshandle, 16> = Vec::new();

    #[cfg(feature = "ble")]
    unwrap!(ifaces.push(Syshandle::Ble));

    #[cfg(feature = "button")]
    unwrap!(ifaces.push(Syshandle::Button));

    #[cfg(feature = "touch")]
    unwrap!(ifaces.push(Syshandle::Touch));

    #[cfg(feature = "power_manager")]
    unwrap!(ifaces.push(Syshandle::PowerManager));

    #[cfg(feature = "debuglink")]
    unwrap!(ifaces.push(Syshandle::UsbDebug));

    if communication {
        unwrap!(ifaces.push(Syshandle::UsbWire));

        #[cfg(feature = "ble")]
        unwrap!(ifaces.push(Syshandle::BleIface));
    }

    loop {
        #[cfg(feature = "power_manager")]
        let mut do_suspend = false;

        #[cfg(all(feature = "power_manager", feature = "haptic"))]
        {
            if let Some(t) = button_pressed_time {
                if let Some(elapsed) = Instant::now().checked_duration_since(t) {
                    if elapsed >= HIBERNATE_TIME && !haptic_played {
                        play(HapticEffect::BootloaderEntry);
                        haptic_played = true;
                    }
                }
            }
        }

        let event = sysevents_poll(ifaces.as_slice());

        if let Some(e) = event {
            if faded {
                ModelUI::fadein();
                faded = false;
            }

            #[cfg(feature = "debuglink")]
            if e == Event::USBDebug {
                let res = debuglink_process();

                if res == DebuglinkResult::Repaint {
                    render(frame);
                }

                continue;
            }

            if e == Event::USBWire {
                let res = bootloader_process_usb();
                if res == BootloaderWFResult::Ok {
                    continue;
                }

                return (res.return_to_c(), 0);
            }

            #[cfg(feature = "ble")]
            if e == Event::BLEIface {
                let res = bootloader_process_ble();
                if res == BootloaderWFResult::Ok {
                    continue;
                }

                return (res.return_to_c(), 0);
            }

            #[cfg(feature = "power_manager")]
            {
                start = Instant::now();

                if e == Event::Button(ButtonEvent::ButtonPressed(PhysicalButton::Power)) {
                    button_pressed_time = Some(Instant::now());

                    #[cfg(feature = "haptic")]
                    {
                        haptic_played = false;
                    }
                } else if e == Event::Button(ButtonEvent::ButtonReleased(PhysicalButton::Power)) {
                    if let Some(t) = button_pressed_time {
                        if let Some(elapsed) = Instant::now().checked_duration_since(t) {
                            ModelUI::fadeout();
                            faded = true;
                            if elapsed >= HIBERNATE_TIME {
                                hibernate();
                            } else {
                                do_suspend = true;
                            }
                        }
                    }
                }
            }

            let mut ctx = EventCtx::new();

            let msg = frame.event(&mut ctx, e);

            if let Some(message) = msg {
                return (
                    BootloaderWFResult::OkUiAction.return_to_c(),
                    message.return_to_c(),
                );
            }
            render(frame);
        } else {
            #[cfg(feature = "power_manager")]
            {
                if is_usb_connected() {
                    continue;
                }

                let elapsed = Instant::now().checked_duration_since(start);

                if let Some(elapsed) = elapsed {
                    if elapsed >= FADE_TIME && !faded {
                        faded = true;
                        fade_backlight_duration(ModelUI::get_backlight_low(), 200);
                    }
                    if elapsed >= SUSPEND_TIME {
                        do_suspend = true;
                    }
                }
            }
        }

        #[cfg(feature = "power_manager")]
        if do_suspend {
            suspend();
            render(frame);
            if faded {
                ModelUI::fadein();
                faded = false;
            }
            start = Instant::now();
            button_pressed_time = None;
        }
    }
}
