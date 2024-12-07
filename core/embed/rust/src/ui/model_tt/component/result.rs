use crate::{
    strutil::TString,
    ui::{
        component::{text::TextStyle, Child, Component, Event, EventCtx, Label, Never, Pad},
        constant::screen,
        display::{Color, Font, Icon},
        geometry::{Alignment2D, Insets, Offset, Point, Rect},
        model_tt::theme::FG,
        shape,
        shape::Renderer,
    },
};

use crate::ui::model_tt::{
    constant::WIDTH,
    theme::{RESULT_FOOTER_START, RESULT_PADDING},
};

const MESSAGE_AREA_START: i16 = 97;
const ICON_CENTER_Y: i16 = 62;

pub struct ResultStyle {
    pub fg_color: Color,
    pub bg_color: Color,
    pub divider_color: Color,
}

impl ResultStyle {
    pub const fn new(fg_color: Color, bg_color: Color, divider_color: Color) -> Self {
        Self {
            fg_color,
            bg_color,
            divider_color,
        }
    }

    pub const fn message_style(&self) -> TextStyle {
        TextStyle::new(Font::NORMAL, self.fg_color, self.bg_color, FG, FG)
    }

    pub const fn title_style(&self) -> TextStyle {
        TextStyle::new(Font::BOLD_UPPER, self.fg_color, self.bg_color, FG, FG)
    }
}

pub struct ResultFooter<'a> {
    style: &'a ResultStyle,
    text: Label<'a>,
    area: Rect,
}

impl<'a> ResultFooter<'a> {
    pub fn new(text: Label<'a>, style: &'a ResultStyle) -> Self {
        Self {
            style,
            text,
            area: Rect::zero(),
        }
    }
}

impl ResultFooter<'_> {
    pub const fn split_bounds() -> (Rect, Rect) {
        let main_area = Rect::new(
            Point::new(RESULT_PADDING, 0),
            Point::new(WIDTH - RESULT_PADDING, RESULT_FOOTER_START),
        );
        let footer_area = Rect::new(
            Point::new(RESULT_PADDING, RESULT_FOOTER_START),
            Point::new(WIDTH - RESULT_PADDING, screen().height()),
        );
        (main_area, footer_area)
    }
}

impl Component for ResultFooter<'_> {
    type Msg = Never;

    fn place(&mut self, bounds: Rect) -> Rect {
        self.area = bounds;
        self.text.place(bounds);
        bounds
    }

    fn event(&mut self, _ctx: &mut EventCtx, _event: Event) -> Option<Self::Msg> {
        None
    }

    fn render<'s>(&'s self, target: &mut impl Renderer<'s>) {
        // divider line
        let bar = Rect::from_center_and_size(
            Point::new(self.area.center().x, self.area.y0),
            Offset::new(self.area.width(), 1),
        );
        shape::Bar::new(bar)
            .with_fg(self.style.divider_color)
            .render(target);

        // footer text
        self.text.render(target);
    }
}

pub struct ResultScreen<'a> {
    bg: Pad,
    footer_pad: Pad,
    style: &'a ResultStyle,
    icon: Icon,
    message: Child<Label<'a>>,
    footer: Child<ResultFooter<'a>>,
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
            message: Child::new(Label::centered(message, style.message_style())),
            footer: Child::new(ResultFooter::new(footer, style)),
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
