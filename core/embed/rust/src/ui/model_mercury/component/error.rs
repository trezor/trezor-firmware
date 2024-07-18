use crate::{
    strutil::TString,
    ui::{
        component::{Component, Event, EventCtx, Label, Never, Pad},
        constant::screen,
        geometry::{Alignment2D, Point, Rect},
        shape,
        shape::Renderer,
    },
};

use super::{
    constant::WIDTH,
    theme::{FATAL_ERROR_COLOR, ICON_WARNING40, RESULT_FOOTER_START, RESULT_PADDING, WHITE},
    ResultFooter, ResultStyle,
};

const ICON_TOP: i16 = 23;
const TITLE_AREA_START: i16 = 70;
const MESSAGE_AREA_START: i16 = 116;

#[cfg(feature = "bootloader")]
const STYLE: &ResultStyle = &crate::ui::model_mercury::theme::bootloader::RESULT_WIPE;
#[cfg(not(feature = "bootloader"))]
const STYLE: &ResultStyle = &super::theme::RESULT_ERROR;

pub struct ErrorScreen<'a> {
    bg: Pad,
    title: Label<'a>,
    message: Label<'a>,
    footer: ResultFooter<'a>,
}

impl<'a> ErrorScreen<'a> {
    pub fn new(title: TString<'a>, message: TString<'a>, footer: TString<'a>) -> Self {
        let title = Label::centered(title, STYLE.title_style());
        let message = Label::centered(message, STYLE.message_style());
        let footer = ResultFooter::new(
            Label::centered(footer, STYLE.title_style()).vertically_centered(),
            STYLE,
        );

        Self {
            bg: Pad::with_background(FATAL_ERROR_COLOR).with_clear(),
            title,
            message,
            footer,
        }
    }
}

impl<'a> Component for ErrorScreen<'a> {
    type Msg = Never;

    fn place(&mut self, _bounds: Rect) -> Rect {
        self.bg.place(screen());

        let title_area = Rect::new(
            Point::new(RESULT_PADDING, TITLE_AREA_START),
            Point::new(WIDTH - RESULT_PADDING, MESSAGE_AREA_START),
        );
        self.title.place(title_area);

        let message_area = Rect::new(
            Point::new(RESULT_PADDING, MESSAGE_AREA_START),
            Point::new(WIDTH - RESULT_PADDING, RESULT_FOOTER_START),
        );
        self.message.place(message_area);

        let (_, bottom_area) = ResultFooter::<'a>::split_bounds();
        self.footer.place(bottom_area);

        screen()
    }

    fn event(&mut self, _ctx: &mut EventCtx, _event: Event) -> Option<Self::Msg> {
        None
    }

    fn paint(&mut self) {
        self.bg.paint();

        let icon = ICON_WARNING40;
        icon.draw(
            Point::new(screen().center().x, ICON_TOP),
            Alignment2D::TOP_CENTER,
            WHITE,
            FATAL_ERROR_COLOR,
        );
        self.title.paint();
        self.message.paint();
        self.footer.paint();
    }

    fn render<'s>(&'s self, target: &mut impl Renderer<'s>) {
        self.bg.render(target);

        let icon = ICON_WARNING40;
        shape::ToifImage::new(Point::new(screen().center().x, ICON_TOP), icon.toif)
            .with_fg(WHITE)
            .with_bg(FATAL_ERROR_COLOR)
            .with_align(Alignment2D::TOP_CENTER)
            .render(target);

        self.title.render(target);
        self.message.render(target);
        self.footer.render(target);
    }
}
