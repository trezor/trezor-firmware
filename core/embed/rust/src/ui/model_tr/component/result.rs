use crate::ui::{
    component::{Child, Component, Event, EventCtx, Label, Never, Pad},
    constant::{screen, HEIGHT, WIDTH},
    display::{Color, Icon},
    geometry::{Alignment2D, Offset, Point, Rect},
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
    message_top: Child<Label<&'static str>>,
    message_bottom: Child<Label<&'a str>>,
}

impl<'a> ResultScreen<'a> {
    pub fn new(
        fg_color: Color,
        bg_color: Color,
        icon: Icon,
        title: Label<&'static str>,
        content: Label<&'a str>,
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

impl<'a> Component for ResultScreen<'a> {
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

    fn paint(&mut self) {
        self.bg.paint();
        self.small_pad.paint();

        self.icon.draw(
            screen().top_center() + Offset::y(ICON_TOP),
            Alignment2D::CENTER,
            self.fg_color,
            self.bg_color,
        );

        self.message_top.paint();
        self.message_bottom.paint();
    }
}
