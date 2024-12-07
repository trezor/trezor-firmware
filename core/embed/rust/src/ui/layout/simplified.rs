#[cfg(feature = "button")]
use crate::trezorhal::io::io_button_get_event;
#[cfg(feature = "touch")]
use crate::trezorhal::io::io_touch_get_event;
#[cfg(feature = "button")]
use crate::ui::event::ButtonEvent;
#[cfg(feature = "touch")]
use crate::ui::event::TouchEvent;
use crate::ui::{
    component::{Component, Event, EventCtx, Never},
    display,
    ui_features::ModelUI,
    UIFeaturesCommon,
};

use num_traits::ToPrimitive;

use crate::ui::{display::color::Color, shape::render_on_display};

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
    let event = io_button_get_event();
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
    let event = io_touch_get_event();
    if event == 0 {
        return None;
    }
    let event_type = event >> 24;
    let ex = ((event >> 12) & 0xFFF) as i16;
    let ey = (event & 0xFFF) as i16;

    TouchEvent::new(event_type, ex as _, ey as _).ok()
}

fn render(frame: &mut impl Component) {
    display::sync();
    render_on_display(None, Some(Color::black()), |target| {
        frame.render(target);
    });
    display::refresh();
}

pub fn run(frame: &mut impl Component<Msg = impl ReturnToC>) -> u32 {
    frame.place(ModelUI::SCREEN);
    ModelUI::fadeout();
    render(frame);
    ModelUI::fadein();

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
            render(frame);
        }
    }
}

pub fn show(frame: &mut impl Component, fading: bool) {
    frame.place(ModelUI::SCREEN);

    if fading {
        ModelUI::fadeout()
    };

    render(frame);

    if fading {
        ModelUI::fadein()
    };
}
