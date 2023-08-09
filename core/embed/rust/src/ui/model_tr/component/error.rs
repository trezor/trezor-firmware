use crate::ui::{
    component::{Child, Component, Event, EventCtx, Label, Never, Pad},
    constant::{screen, WIDTH},
    display,
    geometry::{Alignment2D, Offset, Point, Rect},
};

use super::super::{
    theme,
    theme::{BG, FG, TITLE_AREA_HEIGHT},
};

const FOOTER_AREA_HEIGHT: i16 = 20;
const DIVIDER_POSITION: i16 = 43;

pub struct ErrorScreen<T> {
    bg: Pad,
    show_icons: bool,
    title: Child<Label<T>>,
    message: Child<Label<T>>,
    footer: Child<Label<T>>,
    area: Rect,
}

impl<T: AsRef<str>> ErrorScreen<T> {
    pub fn new(title: T, message: T, footer: T) -> Self {
        let title = Label::centered(title, theme::TEXT_BOLD);
        let message = Label::centered(message, theme::TEXT_NORMAL).vertically_centered();
        let footer = Label::centered(footer, theme::TEXT_NORMAL).vertically_centered();

        Self {
            bg: Pad::with_background(BG).with_clear(),
            show_icons: true,
            title: Child::new(title),
            message: Child::new(message),
            footer: Child::new(footer),
            area: Rect::zero(),
        }
    }
}

impl<T: AsRef<str>> Component for ErrorScreen<T> {
    type Msg = Never;

    fn place(&mut self, bounds: Rect) -> Rect {
        self.bg.place(screen());

        let title_area = Rect::new(screen().top_left(), screen().top_right() + Offset::y(11));
        self.title.place(title_area);

        let text_width = self.title.inner().max_size().x;

        if text_width > title_area.width() - 2 * TITLE_AREA_HEIGHT {
            self.show_icons = false;
        }

        let top_offset = if self.show_icons {
            Offset::y(11)
        } else {
            Offset::y(8)
        };

        let message_area = Rect::new(
            title_area.top_left() + top_offset,
            Point::new(title_area.bottom_right().x, DIVIDER_POSITION),
        );
        self.message.place(message_area);

        let footer_area = Rect::new(
            screen().bottom_left() + Offset::y(-FOOTER_AREA_HEIGHT),
            screen().bottom_right(),
        );
        self.footer.place(footer_area);

        self.area = bounds;
        screen()
    }

    fn event(&mut self, _ctx: &mut EventCtx, _event: Event) -> Option<Self::Msg> {
        None
    }

    fn paint(&mut self) {
        self.bg.paint();

        if self.show_icons {
            theme::ICON_WARN_TITLE.draw(screen().top_left(), Alignment2D::TOP_LEFT, FG, BG);
            theme::ICON_WARN_TITLE.draw(screen().top_right(), Alignment2D::TOP_RIGHT, FG, BG);
        }
        self.title.paint();
        self.message.paint();

        // // divider line
        display::dotted_line(Point::new(0, DIVIDER_POSITION), WIDTH, FG, 3);

        self.footer.paint();
    }
}
