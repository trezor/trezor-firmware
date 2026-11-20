use num_traits::ToPrimitive;

use crate::maybe_trace::MaybeTrace;
#[cfg(feature = "button")]
use crate::trezorhal::button::button_get_event;
use crate::ui::component::base::AttachType;
use crate::ui::component::{Component, Event, EventCtx, Never};
use crate::ui::display::color::Color;
#[cfg(feature = "button")]
use crate::ui::event::ButtonEvent;
#[cfg(feature = "touch")]
use crate::ui::event::TouchEvent;
use crate::ui::shape::render_on_display;
use crate::ui::{display, CommonUI, ModelUI};

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
    button_get_event().map(|(event_btn, event_type)| ButtonEvent::new(event_type, event_btn))
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

pub fn render(frame: &mut (impl Component + MaybeTrace)) {
    display::sync();
    render_on_display(None, Some(Color::black()), |target| {
        frame.render(target);
    });
    display::refresh();

    // keep the layout the debug link reports in step with the display
    #[cfg(all(feature = "debuglink", feature = "bootloader", feature = "ui_debug"))]
    crate::trezorhal::bootloader::debuglink_set_layout(frame);
}

/// Report a progress screen, which is drawn without a component, to the
/// debug link. `new_screen` is set on the first frame of the screen, so that
/// waiting for the next layout ends when it comes up.
#[allow(unused_variables)]
pub fn debuglink_report_progress(
    title: &str,
    content: Option<&str>,
    progress: u16,
    new_screen: bool,
) {
    #[cfg(all(feature = "debuglink", feature = "bootloader", feature = "ui_debug"))]
    {
        use crate::trezorhal::bootloader::{debuglink_notify_layout_change, debuglink_set_layout};

        struct ProgressTrace<'a> {
            title: &'a str,
            content: Option<&'a str>,
            progress: u16,
        }

        impl crate::trace::Trace for ProgressTrace<'_> {
            fn trace(&self, t: &mut dyn crate::trace::Tracer) {
                t.component("Progress");
                t.string("title", self.title.into());
                if let Some(content) = self.content {
                    t.string("screen_content", content.into());
                }
                t.int("progress", self.progress.into());
            }
        }

        debuglink_set_layout(&ProgressTrace {
            title,
            content,
            progress,
        });
        if new_screen {
            debuglink_notify_layout_change();
        }
    }
}

pub fn process_frame_event<A>(frame: &mut A, event: Option<Event>) -> u32
where
    A: Component + MaybeTrace,
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

pub fn show(frame: &mut (impl Component<Msg = impl ReturnToC> + MaybeTrace), fading: bool) -> u32 {
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

    #[cfg(all(feature = "debuglink", feature = "bootloader"))]
    {
        use crate::trezorhal::bootloader::debuglink_notify_layout_change;
        debuglink_notify_layout_change();
    }

    0
}
