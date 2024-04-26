use crate::ui::{
    component::{Event, TimerToken},
    display::{self, Color, Font},
    event::TouchEvent,
    geometry::{Offset, Point, Rect},
    shape::{self, Viewport},
};

use crate::{
    time::{Duration, Stopwatch},
    trezorhal::io::io_touch_read,
};
use core::fmt::Write;
use heapless::String;

use super::{screen1::build_screen1, screen2::build_screen2, screen3::build_screen3};

fn render_time_overlay(duration: Duration) {
    shape::render_on_display(
        Some(Viewport::new(Rect::new(
            Point::new(200, 0),
            Point::new(240, 20),
        ))),
        Some(Color::rgb(0, 0, 255)),
        |target| {
            let text_color = Color::rgb(255, 255, 0);

            let mut info = String::<128>::new();
            write!(info, "{}", duration.to_millis()).unwrap();

            let font = Font::NORMAL;
            let pt = Point::new(200, font.vert_center(0, 20, "A"));
            shape::Text::new(pt, info.as_str())
                .with_fg(text_color)
                .with_font(font)
                .render(target);
        },
    );
}

fn touch_event() -> Option<TouchEvent> {
    let event = io_touch_read();
    if event == 0 {
        return None;
    }
    let event_type = event >> 24;
    let ex = ((event >> 12) & 0xFFF) as i16;
    let ey = (event & 0xFFF) as i16;

    TouchEvent::new(event_type, ex as _, ey as _).ok()
}

// Animates the split point between two screens
// (ranging from -240 to 0)

#[derive(Default)]
struct ScreenTransitionAnim {
    timer: Stopwatch,
}

impl ScreenTransitionAnim {
    pub fn is_active(&self) -> bool {
        self.timer.is_running()
    }

    pub fn eval(&self) -> i16 {
        let anim = pareen::constant(0.0)
            .seq_ease_in_out(
                0.0,
                pareen::easer::functions::Back,
                1.5,
                pareen::constant(-240.0),
            )
            .seq_ease_in_out(
                5.0,
                pareen::easer::functions::Back,
                0.75,
                pareen::constant(0.0),
            )
            .dur(10.0)
            .repeat();

        anim.eval(self.timer.elapsed().into()) as i16
    }
}

extern "C" fn void() {}

#[no_mangle]
extern "C" fn drawlib_demo() {
    let screen1 = build_screen1().unwrap();
    let screen2 = build_screen2().unwrap();
    let screen3 = build_screen3().unwrap();

    screen1.obj_event(Event::Attach).unwrap();
    screen2.obj_event(Event::Attach).unwrap();
    screen3.obj_event(Event::Attach).unwrap();

    let mut anim = ScreenTransitionAnim::default();
    anim.timer.start();

    loop {
        //screen1.obj_event(Event::Timer(TimerToken::INVALID)).unwrap();
        //screen2.obj_event(Event::Timer(TimerToken::INVALID)).unwrap();

        if let Some(e) = touch_event() {
            screen1.obj_event(Event::Touch(e)).unwrap();
            screen2.obj_event(Event::Touch(e)).unwrap();
            screen3.obj_event(Event::Touch(e)).unwrap();
        }

        let split = anim.eval();

        display::sync();

        let stopwatch = Stopwatch::new_started();

        //screen1.obj_paint_if_requested();

        //screen1.obj_render(Offset::x(split));
        //screen2.obj_render(Offset::x(240 + split));

        screen3.obj_render(Offset::x(0));

        render_time_overlay(stopwatch.elapsed());

        display::refresh();
    }
}
