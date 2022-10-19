use crate::ui::{
    component::{
        text::paragraphs::{ParagraphStrType, ParagraphVecShort, Paragraphs},
        Child, Component, Event, EventCtx, Never, Pad,
    },
    constant::{screen, HEIGHT, WIDTH},
    display::{Color, Icon},
    geometry::{Offset, Point, Rect, CENTER},
};

pub struct ResultScreen<T> {
    bg: Pad,
    small_pad: Pad,
    fg_color: Color,
    bg_color: Color,
    icon: Icon,
    message_top: Child<Paragraphs<ParagraphVecShort<T>>>,
    message_bottom: Child<Paragraphs<ParagraphVecShort<T>>>,
}

impl<T: ParagraphStrType> ResultScreen<T> {
    pub fn new(
        fg_color: Color,
        bg_color: Color,
        icon: Icon,
        message_top: Paragraphs<ParagraphVecShort<T>>,
        message_bottom: Paragraphs<ParagraphVecShort<T>>,
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

impl<T: ParagraphStrType> Component for ResultScreen<T> {
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

        self.icon.draw(
            screen().top_center() + Offset::y(12),
            CENTER,
            self.fg_color,
            self.bg_color,
        );

        self.message_top.paint();
        self.message_bottom.paint();
    }
}
