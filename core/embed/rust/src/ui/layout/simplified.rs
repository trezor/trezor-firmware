#[cfg(feature = "button")]
use crate::trezorhal::button::button_get_event;
#[cfg(feature = "button")]
use crate::ui::event::ButtonEvent;
#[cfg(feature = "touch")]
use crate::ui::event::TouchEvent;
use crate::ui::{
    component::{Component, EventCtx, Never},
    display, CommonUI, ModelUI,
};
use core::{
    mem::{align_of, size_of, MaybeUninit},
    ptr,
};

use crate::ui::{component::Event, display::color::Color, shape::render_on_display};
use num_traits::ToPrimitive;

use crate::trezorhal::poll::poll_event;
use heapless::Vec;

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

pub(crate) fn render(frame: &mut impl Component) {
    display::sync();
    render_on_display(None, Some(Color::black()), |target| {
        frame.render(target);
    });
    display::refresh();
}

fn convert_layout<A>(buf: &mut [u8]) -> *mut MaybeUninit<A> {
    let required_size = size_of::<A>();
    let required_align = align_of::<A>();

    let ptr = buf.as_mut_ptr();
    let addr = ptr as usize;

    // Check alignment and size
    if addr % required_align != 0 || buf.len() < required_size {
        panic!("Buffer is not aligned or too small");
    }

    // SAFETY: we have just verified alignment and size
    let connect_ptr = ptr as *mut MaybeUninit<A>;
    connect_ptr
}

pub fn init_layout<A>(buf: &mut [u8], frame: A) -> &mut A {
    let frame_ptr: *mut MaybeUninit<A> = convert_layout(buf);

    let frame = unsafe {
        // Construct in-place
        ptr::write(frame_ptr as *mut A, frame);

        // Get mutable reference to initialized object
        &mut *frame_ptr.cast::<A>()
    };

    frame
}

pub fn process_event<A>(buf: &mut [u8], event: Option<Event>) -> u32
where
    A: Component,
    A::Msg: ReturnToC,
{
    let frame_ptr: *mut MaybeUninit<A> = convert_layout(buf);

    let frame = unsafe {
        // Get mutable reference to initialized object
        &mut *frame_ptr.cast::<A>()
    };

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
    ModelUI::fadeout();
    render(frame);
    ModelUI::fadein();

    // flush any pending events
    #[cfg(feature = "button")]
    while button_eval().is_some() {}

    let mut ifaces: Vec<u16, 16> = Vec::new();

    #[cfg(feature = "ble")]
    unwrap!(ifaces.push(252));

    #[cfg(feature = "button")]
    unwrap!(ifaces.push(254));

    #[cfg(feature = "touch")]
    unwrap!(ifaces.push(255));

    loop {
        let event = poll_event(ifaces.as_slice());

        if let Some(e) = event {
            let mut ctx = EventCtx::new();

            let msg = frame.event(&mut ctx, e);

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
