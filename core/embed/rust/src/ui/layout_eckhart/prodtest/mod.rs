mod welcome;

use heapless::Vec;

use super::cshape::ScreenBorder;
use super::prodtest::welcome::Welcome;
use super::{fonts, UIEckhart};
use crate::ui::component::Event;
use crate::ui::constant::screen;
use crate::ui::display;
use crate::ui::display::Color;
use crate::ui::event::TouchEvent;
use crate::ui::event::TouchEvent::{TouchEnd, TouchMove, TouchStart};
use crate::ui::geometry::{Alignment, Insets, Offset, Rect};
use crate::ui::layout::simplified::{process_frame_event, show};
use crate::ui::shape::{self, render_on_display};
use crate::ui::ui_prodtest::{ProdtestLayoutType, ProdtestUI};

#[allow(clippy::large_enum_variant)]
pub enum ProdtestLayout {
    Welcome(Welcome),
}

impl ProdtestLayoutType for ProdtestLayout {
    fn event(&mut self, event: Option<Event>) -> u32 {
        match self {
            ProdtestLayout::Welcome(f) => process_frame_event::<Welcome>(f, event),
        }
    }

    fn show(&mut self) -> u32 {
        match self {
            ProdtestLayout::Welcome(f) => show(f, false),
        }
    }

    fn init_welcome(id: Option<&'static str>) -> Self {
        Self::Welcome(Welcome::new(id))
    }
}

impl ProdtestUI for UIEckhart {
    type CLayoutType = ProdtestLayout;

    fn screen_prodtest_show_text(text: &str) {
        display::sync();
        render_on_display(None, Some(Color::black()), |target| {
            shape::Text::new(screen().center(), text, fonts::FONT_SATOSHI_REGULAR_22)
                .with_fg(Color::white())
                .with_align(Alignment::Center)
                .render(target);
        });

        display::refresh();
    }

    fn screen_prodtest_signal_meter(percent: u8, label: &str) {
        display::sync();

        let percent = percent.min(100);
        let color = match percent {
            80..=100 => Color::rgb(0, 200, 0),
            60..=79 => Color::rgb(140, 200, 0),
            40..=59 => Color::rgb(255, 180, 0),
            20..=39 => Color::rgb(255, 100, 0),
            _ => Color::rgb(220, 0, 0),
        };

        let percent_text = uformat!("{}%", percent);

        let screen = screen();
        let (title_area, rest) = screen.split_top(60);
        let (_, rest) = rest.split_top(20);
        let (percent_area, rest) = rest.split_top(90);
        let (_, rest) = rest.split_top(20);
        let (bar_area, rest) = rest.split_top(48);
        let (_, label_area) = rest.split_top(20);
        let bar_area = bar_area.inset(Insets::sides(40));

        render_on_display(None, Some(Color::black()), |target| {
            shape::Text::new(
                title_area.top_center(),
                "MCU FREQUENCY",
                fonts::FONT_SATOSHI_REGULAR_22,
            )
            .with_fg(Color::rgb(160, 160, 160))
            .with_align(Alignment::Center)
            .render(target);

            shape::Text::new(
                percent_area.center(),
                &percent_text,
                fonts::FONT_SATOSHI_EXTRALIGHT_72,
            )
            .with_fg(color)
            .with_align(Alignment::Center)
            .render(target);

            shape::Bar::new(bar_area)
                .with_fg(Color::rgb(80, 80, 80))
                .with_thickness(2)
                .with_radius(8)
                .render(target);

            let inner = bar_area.shrink(4);
            let fill_width = (inner.width() as u32 * percent as u32 / 100) as i16;
            if fill_width > 0 {
                let fill = inner.with_width(fill_width);
                shape::Bar::new(fill)
                    .with_bg(color)
                    .with_radius(6)
                    .render(target);
            }

            shape::Text::new(
                label_area.top_center(),
                label,
                fonts::FONT_SATOSHI_REGULAR_22,
            )
            .with_fg(color)
            .with_align(Alignment::Center)
            .render(target);
        });

        display::refresh();
    }

    fn screen_prodtest_border() {
        display::sync();
        let border = ScreenBorder::new(Color::white());
        render_on_display(None, Some(Color::black()), |target| {
            border.render(u8::MAX, target);
        });

        display::refresh();
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
