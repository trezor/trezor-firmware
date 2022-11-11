use crate::ui::{
    component::{
        text::paragraphs::{ParagraphVecShort, Paragraphs},
        Child, Component, Event, EventCtx, Never, Pad,
    },
    constant::{screen, HEIGHT, WIDTH},
    display,
    display::Color,
    geometry::{Offset, Point, Rect},
};

pub struct ResultScreen {
    bg: Pad,
    small_pad: Pad,
    fg_color: Color,
    bg_color: Color,
    icon: &'static [u8],
    message_top: Child<Paragraphs<ParagraphVecShort<&'static str>>>,
    message_bottom: Child<Paragraphs<ParagraphVecShort<&'static str>>>,
}

impl ResultScreen {
    pub fn new(
        fg_color: Color,
        bg_color: Color,
        icon: &'static [u8],
        message_top: Paragraphs<ParagraphVecShort<&'static str>>,
        message_bottom: Paragraphs<ParagraphVecShort<&'static str>>,
        complete_draw: bool,
    ) -> Self {
        let mut instance = Self {
            bg: Pad::with_background(bg_color),
            small_pad: Pad::with_background(bg_color),
            fg_color,
            bg_color,
            icon,
            message_top: Child::new(message_top),
            message_bottom: Child::new(message_bottom),
        };

        if complete_draw {
            instance.bg.clear();
        } else {
            instance.small_pad.clear();
        }
        instance
    }
}

impl Component for ResultScreen {
    type Msg = Never;

    fn place(&mut self, bounds: Rect) -> Rect {
        self.bg
            .place(Rect::new(Point::new(0, 0), Point::new(WIDTH, HEIGHT)));

        self.message_top
            .place(Rect::new(Point::new(0, 26), Point::new(WIDTH, 40)));

        let bottom_area = Rect::new(Point::new(0, 40), Point::new(WIDTH, HEIGHT));

        self.small_pad.place(bottom_area);
        self.message_bottom.place(bottom_area);

        bounds
    }

    fn event(&mut self, _ctx: &mut EventCtx, _event: Event) -> Option<Self::Msg> {
        None
    }

    fn paint(&mut self) {
        self.bg.paint();
        self.small_pad.paint();

        display::icon(
            screen().top_center() + Offset::y(12),
            self.icon,
            self.fg_color,
            self.bg_color,
        );

        self.message_top.paint();
        self.message_bottom.paint();
    }

    fn bounds(&self, _sink: &mut dyn FnMut(Rect)) {}
}
