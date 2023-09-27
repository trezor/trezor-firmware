use crate::{
    strutil::StringType,
    ui::{
        component::{text::TextStyle, Child, Component, Event, EventCtx, Label, Never, Pad},
        constant::screen,
        display::{self, Color, Font, Icon},
        geometry::{Alignment2D, Insets, Offset, Point, Rect},
        model_tt::theme::FG,
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
        TextStyle::new(Font::BOLD, self.fg_color, self.bg_color, FG, FG)
    }
}

pub struct ResultFooter<'a, T> {
    style: &'a ResultStyle,
    text: Label<T>,
    area: Rect,
}

impl<'a, T: AsRef<str>> ResultFooter<'a, T> {
    pub fn new(text: Label<T>, style: &'a ResultStyle) -> Self {
        Self {
            style,
            text,
            area: Rect::zero(),
        }
    }

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

impl<T: AsRef<str>> Component for ResultFooter<'_, T> {
    type Msg = Never;

    fn place(&mut self, bounds: Rect) -> Rect {
        self.area = bounds;
        self.text.place(bounds);
        bounds
    }

    fn paint(&mut self) {
        // divider line
        let bar = Rect::from_center_and_size(
            Point::new(self.area.center().x, self.area.y0),
            Offset::new(self.area.width(), 1),
        );
        display::rect_fill(bar, self.style.divider_color);

        // footer text
        self.text.paint();
    }

    fn event(&mut self, _ctx: &mut EventCtx, _event: Event) -> Option<Self::Msg> {
        None
    }
}

pub struct ResultScreen<'a, T> {
    bg: Pad,
    footer_pad: Pad,
    style: &'a ResultStyle,
    icon: Icon,
    message: Child<Label<T>>,
    footer: Child<ResultFooter<'a, &'a str>>,
}

impl<'a, T: StringType> ResultScreen<'a, T> {
    pub fn new(
        style: &'a ResultStyle,
        icon: Icon,
        message: T,
        footer: Label<&'a str>,
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

impl<'a, T: StringType> Component for ResultScreen<'a, T> {
    type Msg = Never;

    fn place(&mut self, _bounds: Rect) -> Rect {
        self.bg.place(screen());

        let (main_area, footer_area) = ResultFooter::<&'a str>::split_bounds();

        self.footer_pad.place(footer_area);
        self.footer.place(footer_area);

        let message_area = main_area.inset(Insets::top(MESSAGE_AREA_START));
        self.message.place(message_area);

        screen()
    }

    fn event(&mut self, _ctx: &mut EventCtx, _event: Event) -> Option<Self::Msg> {
        None
    }

    fn paint(&mut self) {
        self.bg.paint();
        self.footer_pad.paint();

        self.icon.draw(
            Point::new(screen().center().x, ICON_CENTER_Y),
            Alignment2D::CENTER,
            self.style.fg_color,
            self.style.bg_color,
        );
        self.message.paint();
        self.footer.paint();
    }
}
