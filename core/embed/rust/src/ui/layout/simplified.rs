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

use num_traits::ToPrimitive;

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
pub fn button_eval() -> Option<ButtonEvent> {
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

pub fn show(frame: &mut impl Component<Msg = impl ReturnToC>, fading: bool) -> u32 {
    frame.place(ModelUI::SCREEN);

    let e = Event::Attach(AttachType::Initial);
    let mut ctx = EventCtx::new();

    let msg = frame.event(&mut ctx, e);

    if let Some(message) = msg {
        return message.return_to_c();
    }

    #[cfg(feature = "backlight")]
    if fading && display::get_backlight() > 0 {
        ModelUI::fadeout()
    };

    render(frame);

    if fading {
        ModelUI::fadein()
    };

    #[cfg(feature = "ui_debug")]
    {
        use crate::trezorhal::bootloader::debuglink_notify_layout_change;
        debuglink_notify_layout_change();
    }

    0
}
