use crate::ui::{
    component::{Child, Component, Event, EventCtx, Label, Never, Pad},
    constant::screen,
    display,
    geometry::{Alignment::Center, Offset, Point, Rect, TOP_LEFT, TOP_RIGHT},
};

use super::super::{
    theme,
    theme::{BG, FG, TITLE_AREA_HEIGHT},
};

const FOOTER_AREA_HEIGHT: i16 = 20;
const MESSAGE_AREA_HEIGHT: i16 = 32;
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
        let title = Label::new(title, Center, theme::TEXT_BOLD);
        let message = Label::new(message, Center, theme::TEXT_NORMAL).vertically_aligned(Center);
        let footer = Label::new(footer, Center, theme::TEXT_NORMAL).vertically_aligned(Center);

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

        let message_area = Rect::new(
            title_area.bottom_left(),
            title_area.bottom_right() + Offset::y(MESSAGE_AREA_HEIGHT),
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
            theme::ICON_WARN_TITLE.draw(screen().top_left(), TOP_LEFT, FG, BG);
            theme::ICON_WARN_TITLE.draw(screen().top_right(), TOP_RIGHT, FG, BG);
        }
        self.title.paint();
        self.message.paint();
        // divider line
        let bar = Rect::from_center_and_size(
            Point::new(self.area.center().x, DIVIDER_POSITION),
            Offset::new(self.area.width(), 1),
        );
        display::rect_fill(bar, FG);

        self.footer.paint();
    }
}
