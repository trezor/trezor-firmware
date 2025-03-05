use crate::ui::{
    component::{base::Component, Qr},
    constant::screen,
    display,
    display::Color,
    event::{
        TouchEvent,
        TouchEvent::{TouchEnd, TouchMove, TouchStart},
    },
    geometry::{Alignment, Offset, Rect},
    layout_bolt::{fonts, theme, UIBolt},
    shape,
    shape::render_on_display,
    ui_prodtest::ProdtestUI,
};
use heapless::Vec;

impl ProdtestUI for UIBolt {
    fn screen_prodtest_welcome() {
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

    fn screen_prodtest_info(id: &str) {
        display::sync();
        let qr = Qr::new(id, true);
        let mut qr = unwrap!(qr).with_border(4);

        // place the qr in the middle of the screen and size it to half the screen
        let qr_width = screen().width() / 2;

        let qr_area = Rect::from_center_and_size(screen().center(), Offset::uniform(qr_width));
        qr.place(qr_area);

        render_on_display(None, Some(Color::black()), |target| {
            let area = screen();
            shape::Bar::new(area).with_fg(Color::white()).render(target);

            qr.render(target);

            shape::Text::new(
                screen().bottom_center() - Offset::y(10),
                id,
                fonts::FONT_BOLD_UPPER,
            )
            .with_fg(Color::white())
            .with_align(Alignment::Center)
            .render(target);
        });

        display::refresh();
        display::fade_backlight_duration(theme::backlight::get_backlight_normal(), 150);
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
