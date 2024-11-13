use crate::{
    strutil::TString,
    ui::{
        component::{Child, Component, Event, EventCtx, Label, Never, Pad},
        constant::{screen, WIDTH},
        geometry::{Alignment2D, Offset, Point, Rect},
        model_tr::cshape,
        shape,
        shape::Renderer,
    },
};

use super::super::{
    theme,
    theme::{BG, FG, TITLE_AREA_HEIGHT},
};

const FOOTER_AREA_HEIGHT: i16 = 20;
const DIVIDER_POSITION: i16 = 43;

pub struct ErrorScreen<'a> {
    bg: Pad,
    show_icons: bool,
    title: Child<Label<'a>>,
    message: Child<Label<'a>>,
    footer: Child<Label<'a>>,
    area: Rect,
}

impl<'a> ErrorScreen<'a> {
    pub fn new(title: TString<'a>, message: TString<'a>, footer: TString<'a>) -> Self {
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

impl Component for ErrorScreen<'_> {
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

    fn render<'s>(&'s self, target: &mut impl Renderer<'s>) {
        self.bg.render(target);

        if self.show_icons {
            shape::ToifImage::new(screen().top_left(), theme::ICON_WARN_TITLE.toif)
                .with_align(Alignment2D::TOP_LEFT)
                .with_fg(FG)
                .render(target);

            shape::ToifImage::new(screen().top_right(), theme::ICON_WARN_TITLE.toif)
                .with_align(Alignment2D::TOP_RIGHT)
                .with_fg(FG)
                .render(target);
        }
        self.title.render(target);
        self.message.render(target);

        cshape::HorizontalLine::new(Point::new(0, DIVIDER_POSITION), WIDTH)
            .with_step(3)
            .with_color(FG)
            .render(target);

        self.footer.render(target);
    }
}
