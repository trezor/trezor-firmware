mod welcome;

use crate::ui::{
    component::{base::Component, Event, Label},
    constant::screen,
    display,
    display::Color,
    event::{
        TouchEvent,
        TouchEvent::{TouchEnd, TouchMove, TouchStart},
    },
    geometry::{Alignment, Offset, Rect, Point},
    layout::simplified::{process_frame_event, render, show},
    shape::{self, render_on_display},
    ui_prodtest::{ProdtestLayoutType, ProdtestUI},
    CommonUI,
};
use heapless::Vec;

use super::{
    cshape::ScreenBorder, fonts, prodtest::welcome::Welcome, theme, theme::TEXT_NORMAL, UIEckhart,
};

const SCREEN: Rect = UIEckhart::SCREEN;
const PROGRESS_TEXT_ORIGIN: Point = SCREEN.top_left().ofs(Offset::new(theme::PADDING, 38));
const PROGRESS_TEXT_ORIGIN2: Point = SCREEN.top_left().ofs(Offset::new(theme::PADDING, 38 * 2));
const PROGRESS_TEXT_ORIGIN3: Point = SCREEN.top_left().ofs(Offset::new(theme::PADDING, 38 * 3));

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

    fn screen_large_label(text1: &str, text2: &str, text3: &str) {

        display::sync();

        let mut label1 = Label::new(text1.into(), Alignment::Start, TEXT_NORMAL);
        let mut label2 = Label::new(text2.into(), Alignment::Start, TEXT_NORMAL);
        let mut label3 = Label::new(text3.into(), Alignment::Start, TEXT_NORMAL);
        render_on_display(None, Some(Color::black()), |target| {
            label1.place(Rect::from_top_left_and_size(
                PROGRESS_TEXT_ORIGIN,
                Offset::new(
                    SCREEN.width() - 2 * theme::PADDING,
                    4 * fonts::FONT_SATOSHI_REGULAR_38.text_height(),
                ),
            ));
            label1.render(target);

            label2.place(Rect::from_top_left_and_size(
                PROGRESS_TEXT_ORIGIN2,
                Offset::new(
                    SCREEN.width() - 2 * theme::PADDING,
                    4 * fonts::FONT_SATOSHI_REGULAR_38.text_height(),
                ),
            ));
            label2.render(target);

            label3.place(Rect::from_top_left_and_size(
                PROGRESS_TEXT_ORIGIN3,
                Offset::new(
                    SCREEN.width() - 2 * theme::PADDING,
                    4 * fonts::FONT_SATOSHI_REGULAR_38.text_height(),
                ),
            ));
            label3.render(target);

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
