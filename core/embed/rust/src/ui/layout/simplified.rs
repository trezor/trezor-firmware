#[cfg(feature = "button")]
use crate::trezorhal::button::button_get_event;
#[cfg(feature = "button")]
use crate::ui::event::ButtonEvent;
#[cfg(feature = "touch")]
use crate::ui::event::TouchEvent;
use crate::ui::{
    component::{base::AttachType, Component, EventCtx, Never},
    display, CommonUI, ModelUI,
};

use crate::ui::{component::Event, display::color::Color, shape::render_on_display};

use crate::trezorhal::sysevent::{sysevents_poll, Syshandle};

#[cfg(feature = "power_manager")]
use crate::{
    time::{Duration, Instant},
    trezorhal::power_manager::{hibernate, is_usb_connected, suspend},
    ui::display::fade_backlight_duration,
    ui::event::PhysicalButton,
};

#[cfg(all(feature = "haptic", feature = "power_manager"))]
use crate::trezorhal::haptic::{play, HapticEffect};

use heapless::Vec;
use num_traits::ToPrimitive;

#[cfg(feature = "power_manager")]
const FADE_TIME: Duration = Duration::from_millis(30000);
#[cfg(feature = "power_manager")]
const SUSPEND_TIME: Duration = Duration::from_millis(40000);

pub trait ReturnToC {
    fn return_to_c(self) -> u32;
}

impl ReturnToC for Never {
    fn return_to_c(self) -> u32 {
        unreachable!()
    }
}

impl<T> ReturnToC for T
where
    T: ToPrimitive,
{
    fn return_to_c(self) -> u32 {
        self.to_u32().unwrap()
    }
}

#[cfg(feature = "button")]
fn button_eval() -> Option<ButtonEvent> {
    let event = button_get_event();
    let (event_btn, event_type) = event?;
    let event = ButtonEvent::new(event_type, event_btn);

    if let Ok(event) = event {
        return Some(event);
    }
    None
}

#[cfg(feature = "touch")]
pub fn touch_unpack(event: u32) -> Option<TouchEvent> {
    if event == 0 {
        return None;
    }
    let event_type = event >> 24;
    let ex = ((event >> 12) & 0xFFF) as i16;
    let ey = (event & 0xFFF) as i16;

    TouchEvent::new(event_type, ex as _, ey as _).ok()
}

pub fn render(frame: &mut impl Component) {
    display::sync();
    render_on_display(None, Some(Color::black()), |target| {
        frame.render(target);
    });
    display::refresh();
}

pub fn process_frame_event<A>(frame: &mut A, event: Option<Event>) -> u32
where
    A: Component,
    A::Msg: ReturnToC,
{
    if let Some(event) = event {
        let mut ctx = EventCtx::new();
        let msg = frame.event(&mut ctx, event);
        if let Some(message) = msg {
            return message.return_to_c();
        }
    }

    render(frame);

    0
}

pub fn run(frame: &mut impl Component<Msg = impl ReturnToC>) -> u32 {
    frame.place(ModelUI::SCREEN);

    let e = Event::Attach(AttachType::Initial);
    let mut ctx = EventCtx::new();

    let msg = frame.event(&mut ctx, e);

    if let Some(message) = msg {
        return message.return_to_c();
    }

    ModelUI::fadeout();
    render(frame);
    ModelUI::fadein();

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

    loop {
        let event = sysevents_poll(ifaces.as_slice());

        if let Some(e) = event {
            if faded {
                ModelUI::fadein();
                faded = false;
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
                            if elapsed.to_secs() >= 3 {
                                #[cfg(feature = "haptic")]
                                {
                                    if !haptic_played {
                                        play(HapticEffect::BootloaderEntry);
                                        haptic_played = true;
                                    }
                                }
                                hibernate();
                            } else {
                                suspend();
                                render(frame);
                                ModelUI::fadein();

                                faded = false;
                                button_pressed_time = None;
                                start = Instant::now();
                            }
                        }
                    }
                }
            }

            let mut ctx = EventCtx::new();

            let msg = frame.event(&mut ctx, e);

            if let Some(message) = msg {
                return message.return_to_c();
            }
            render(frame);
        } else {
            #[cfg(feature = "power_manager")]
            {
                #[cfg(feature = "haptic")]
                {
                    if let Some(t) = button_pressed_time {
                        if let Some(elapsed) = Instant::now().checked_duration_since(t) {
                            if elapsed.to_secs() >= 3 && !haptic_played {
                                play(HapticEffect::BootloaderEntry);
                                haptic_played = true;
                            }
                        }
                    }
                }

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
        }
    }
}

pub fn show(frame: &mut impl Component<Msg = impl ReturnToC>, fading: bool) -> u32 {
    frame.place(ModelUI::SCREEN);

    let e = Event::Attach(AttachType::Initial);
    let mut ctx = EventCtx::new();

    let msg = frame.event(&mut ctx, e);

    if let Some(message) = msg {
        return message.return_to_c();
    }

    if fading && display::backlight() > 0 {
        ModelUI::fadeout()
    };

    render(frame);

    if fading {
        ModelUI::fadein()
    };

    0
}
