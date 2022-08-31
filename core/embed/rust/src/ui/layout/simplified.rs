#[cfg(feature = "button")]
use crate::trezorhal::io::io_button_read;
#[cfg(feature = "touch")]
use crate::trezorhal::io::io_touch_read;
#[cfg(feature = "button")]
use crate::ui::event::ButtonEvent;
#[cfg(feature = "touch")]
use crate::ui::event::TouchEvent;
use crate::ui::{
    component::{Component, Event, EventCtx, Never},
    constant::SCREEN,
    display,
};
use num_traits::ToPrimitive;

#[cfg(feature = "backlight")]
use crate::ui::model::theme::{BACKLIGHT_DIM, BACKLIGHT_NORMAL};

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
    let event = io_button_read();
    if event == 0 {
        return None;
    }

    let event_type = event >> 24;
    let event_btn = event & 0xFFFFFF;

    let event = ButtonEvent::new(event_type, event_btn);

    if let Ok(event) = event {
        return Some(event);
    }
    None
}

#[cfg(feature = "touch")]
fn touch_eval() -> Option<TouchEvent> {
    let event = io_touch_read();
    if event == 0 {
        return None;
    }
    let event_type = event >> 24;
    let ex = ((event >> 12) & 0xFFF) as i16;
    let ey = (event & 0xFFF) as i16;

    TouchEvent::new(event_type, ex as _, ey as _).ok()
}

pub fn fadein() {
    #[cfg(feature = "backlight")]
    display::fade_backlight_duration(BACKLIGHT_NORMAL, 150);
}

pub fn fadeout() {
    #[cfg(feature = "backlight")]
    display::fade_backlight_duration(BACKLIGHT_DIM, 150);
}

pub fn run<F>(frame: &mut F) -> u32
where
    F: Component,
    F::Msg: ReturnToC,
{
    frame.place(SCREEN);
    fadeout();
    display::sync();
    frame.paint();
    display::refresh();
    fadein();

    #[cfg(feature = "button")]
    while button_eval().is_some() {}

    loop {
        #[cfg(all(feature = "button", not(feature = "touch")))]
        let event = button_eval();
        #[cfg(feature = "touch")]
        let event = touch_eval();
        if let Some(e) = event {
            let mut ctx = EventCtx::new();
            #[cfg(all(feature = "button", not(feature = "touch")))]
            let msg = frame.event(&mut ctx, Event::Button(e));
            #[cfg(feature = "touch")]
            let msg = frame.event(&mut ctx, Event::Touch(e));

            if let Some(message) = msg {
                return message.return_to_c();
            }
            display::sync();
            frame.paint();
            display::refresh();
        }
    }
}

pub fn show<F>(frame: &mut F, fading: bool)
where
    F: Component,
{
    frame.place(SCREEN);
    if fading {
        fadeout()
    };
    display::sync();
    frame.paint();
    display::refresh();
    if fading {
        fadein()
    };
}
