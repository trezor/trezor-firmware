use super::super::component::{ResultFooter, ResultStyle};
use crate::strutil::TString;
use crate::ui::component::{Component, Event, EventCtx, Label, Never, Pad};
use crate::ui::constant::screen;
use crate::ui::display::Icon;
use crate::ui::geometry::{Alignment2D, Insets, Point, Rect};
use crate::ui::shape::{self, Renderer};

const MESSAGE_AREA_START: i16 = 97;
const ICON_CENTER_Y: i16 = 62;

pub struct ResultScreen<'a> {
    bg: Pad,
    footer_pad: Pad,
    style: &'a ResultStyle,
    icon: Icon,
    message: Label<'a>,
    footer: ResultFooter<'a>,
}

impl<'a> ResultScreen<'a> {
    pub fn new(
        style: &'a ResultStyle,
        icon: Icon,
        message: TString<'a>,
        footer: Label<'a>,
        complete_draw: bool,
    ) -> Self {
        let mut instance = Self {
            bg: Pad::with_background(style.bg_color),
            footer_pad: Pad::with_background(style.bg_color),
            style,
            icon,
            message: Label::centered(message, style.message_style()),
            footer: ResultFooter::new(footer, style),
        };

        if complete_draw {
            instance.bg.clear();
        } else {
            instance.footer_pad.clear();
        }
        instance
    }
}

impl<'a> Component for ResultScreen<'a> {
    type Msg = Never;

    fn place(&mut self, _bounds: Rect) -> Rect {
        self.bg.place(screen());

        let (main_area, footer_area) = ResultFooter::split_bounds();

        self.footer_pad.place(footer_area);
        self.footer.place(footer_area);

        let message_area = main_area.inset(Insets::top(MESSAGE_AREA_START));
        self.message.place(message_area);

        screen()
    }

    fn event(&mut self, _ctx: &mut EventCtx, _event: Event) -> Option<Self::Msg> {
        None
    }

    fn render<'s>(&'s self, target: &mut impl Renderer<'s>) {
        self.bg.render(target);
        self.footer_pad.render(target);

        shape::ToifImage::new(
            Point::new(screen().center().x, ICON_CENTER_Y),
            self.icon.toif,
        )
        .with_align(Alignment2D::CENTER)
        .with_fg(self.style.fg_color)
        .with_bg(self.style.bg_color)
        .render(target);

        self.message.render(target);
        self.footer.render(target);
    }
}
