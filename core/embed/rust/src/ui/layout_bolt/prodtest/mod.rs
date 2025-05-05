mod welcome;

use crate::ui::{
    component::Event,
    constant::screen,
    display,
    display::Color,
    event::{
        TouchEvent,
        TouchEvent::{TouchEnd, TouchMove, TouchStart},
    },
    geometry::{Alignment, Offset, Rect},
    layout::simplified::{get_layout, init_layout, process_frame_event, show},
    layout_bolt::{fonts, prodtest::welcome::Welcome, theme, UIBolt},
    shape,
    shape::render_on_display,
    ui_prodtest::ProdtestUI,
};
use heapless::Vec;

#[allow(clippy::large_enum_variant)]
enum ProdtestLayout {
    Welcome(Welcome),
}

impl ProdtestLayout {
    fn process_event(&mut self, event: Option<Event>) -> u32 {
        match self {
            ProdtestLayout::Welcome(f) => process_frame_event::<Welcome>(f, event),
        }
    }
}

impl ProdtestUI for UIBolt {
    fn screen_prodtest_event(buf: &mut [u8], event: Option<Event>) -> u32 {
        let layout = get_layout::<ProdtestLayout>(buf);
        layout.process_event(event)
    }

    fn screen_prodtest_welcome(buf: &mut [u8], id: Option<&'static str>) {
        let mut welcome = Welcome::new(id);

        show(&mut welcome, true);

        init_layout(buf, ProdtestLayout::Welcome(welcome));
    }

    fn screen_prodtest_show_text(text: &str) {
        display::sync();
        render_on_display(None, Some(Color::black()), |target| {
            shape::Text::new(screen().center(), text, fonts::FONT_BOLD_UPPER)
                .with_fg(Color::white())
                .with_align(Alignment::Center)
                .render(target);
        });

        display::refresh();
        display::fade_backlight_duration(theme::backlight::get_backlight_normal(), 150);
    }

    fn screen_prodtest_border() {
        display::sync();
        render_on_display(None, Some(Color::black()), |target| {
            let area = screen();
            shape::Bar::new(area)
                .with_fg(Color::white())
                .with_thickness(1)
                .render(target);
        });

        display::refresh();
        display::fade_backlight_duration(theme::backlight::get_backlight_normal(), 150);
    }

    fn screen_prodtest_bars(colors: &str) {
        display::sync();

        let num_colors = colors.chars().count();

        let width = if num_colors > 0 {
            screen().width() / num_colors as i16
        } else {
            0
        };

        render_on_display(None, Some(Color::black()), |target| {
            for (i, c) in colors.chars().enumerate() {
                let color = match c {
                    'r' | 'R' => Color::rgb(255, 0, 0),
                    'g' | 'G' => Color::rgb(0, 255, 0),
                    'b' | 'B' => Color::rgb(0, 0, 255),
                    'w' | 'W' => Color::white(),
                    _ => Color::black(),
                };

                let area = Rect::from_top_left_and_size(
                    screen().top_left() + Offset::x(i as i16 * width),
                    Offset::new(width, screen().height()),
                );

                shape::Bar::new(area)
                    .with_fg(color)
                    .with_bg(color)
                    .render(target);
            }
        });

        display::refresh();
        display::fade_backlight_duration(theme::backlight::get_backlight_normal(), 150);
    }

    fn screen_prodtest_touch(area: Rect) {
        display::sync();
        render_on_display(None, Some(Color::black()), |target| {
            shape::Bar::new(area)
                .with_fg(Color::white())
                .with_bg(Color::white())
                .render(target);
        });

        display::refresh();
        display::set_backlight(theme::backlight::get_backlight_normal());
    }

    fn screen_prodtest_draw(events: Vec<TouchEvent, 256>) {
        display::sync();

        render_on_display(None, Some(Color::black()), |target| {
            for ev in events.iter() {
                match ev {
                    TouchStart(p) => {
                        shape::Bar::new(Rect::from_center_and_size(*p, Offset::new(3, 3)))
                            .with_bg(Color::rgb(0, 255, 0))
                            .render(target);
                    }
                    TouchMove(p) => {
                        shape::Bar::new(Rect::from_center_and_size(*p, Offset::new(1, 1)))
                            .with_bg(Color::white())
                            .render(target);
                    }
                    TouchEnd(p) => {
                        shape::Bar::new(Rect::from_center_and_size(*p, Offset::new(3, 3)))
                            .with_bg(Color::rgb(255, 0, 0))
                            .render(target);
                    }
                }
            }
        });

        display::refresh();
    }
}
