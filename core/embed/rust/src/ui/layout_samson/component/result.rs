use crate::ui::{
    component::{Child, Component, Event, EventCtx, Label, Never, Pad},
    constant::{screen, HEIGHT, WIDTH},
    display::{Color, Icon},
    geometry::{Alignment2D, Offset, Point, Rect},
    shape,
    shape::Renderer,
};

const MESSAGE_AREA_START: i16 = 24 + 11;
const MESSAGE_AREA_START_2L: i16 = 24 + 7;
const FOOTER_AREA_START: i16 = MESSAGE_AREA_START + 10;
const FOOTER_AREA_START_2L: i16 = MESSAGE_AREA_START_2L + 10;
const ICON_TOP: i16 = 12;

pub struct ResultScreen<'a> {
    bg: Pad,
    small_pad: Pad,
    fg_color: Color,
    bg_color: Color,
    icon: Icon,
    message_top: Child<Label<'static>>,
    message_bottom: Child<Label<'a>>,
}

impl<'a> ResultScreen<'a> {
    pub fn new(
        fg_color: Color,
        bg_color: Color,
        icon: Icon,
        title: Label<'static>,
        content: Label<'a>,
        complete_draw: bool,
    ) -> Self {
        let mut instance = Self {
            bg: Pad::with_background(bg_color),
            small_pad: Pad::with_background(bg_color),
            fg_color,
            bg_color,
            icon,
            message_top: Child::new(title),
            message_bottom: Child::new(content),
        };

        if complete_draw {
            instance.bg.clear();
        } else {
            instance.small_pad.clear();
        }
        instance
    }
}

impl Component for ResultScreen<'_> {
    type Msg = Never;

    fn place(&mut self, bounds: Rect) -> Rect {
        self.bg.place(bounds);

        let bottom_area = Rect::new(Point::new(0, FOOTER_AREA_START), Point::new(WIDTH, HEIGHT));

        self.message_bottom.place(bottom_area);
        let h = self.message_bottom.inner().text_height(WIDTH);

        if h > 8 {
            self.message_top.place(Rect::new(
                Point::new(0, MESSAGE_AREA_START_2L),
                Point::new(WIDTH, FOOTER_AREA_START_2L),
            ));

            let bottom_area = Rect::new(
                Point::new(0, FOOTER_AREA_START_2L),
                Point::new(WIDTH, FOOTER_AREA_START_2L + h),
            );
            self.message_bottom.place(bottom_area);
        } else {
            self.message_top.place(Rect::new(
                Point::new(0, MESSAGE_AREA_START),
                Point::new(WIDTH, FOOTER_AREA_START),
            ));

            let bottom_area = Rect::new(
                Point::new(0, FOOTER_AREA_START),
                Point::new(WIDTH, FOOTER_AREA_START + h),
            );
            self.message_bottom.place(bottom_area);
        }

        self.small_pad.place(bottom_area);

        bounds
    }

    fn event(&mut self, _ctx: &mut EventCtx, _event: Event) -> Option<Self::Msg> {
        None
    }

    fn render<'s>(&'s self, target: &mut impl Renderer<'s>) {
        self.bg.render(target);
        self.small_pad.render(target);

        shape::ToifImage::new(screen().top_center() + Offset::y(ICON_TOP), self.icon.toif)
            .with_align(Alignment2D::CENTER)
            .with_fg(self.fg_color)
            .render(target);

        self.message_top.render(target);
        self.message_bottom.render(target);
    }
}
