use crate::ui::{
    component::{text::paragraphs::Paragraphs, Child, Component, Event, EventCtx, Never, Pad},
    constant::{HEIGHT, WIDTH},
    display::Color,
    geometry::{Point, Rect},
};

pub struct ResultScreen {
    bg: Pad,
    small_pad: Pad,
    fg_color: Color,
    bg_color: Color,
    message_top: Child<Paragraphs<&'static str>>,
    message_bottom: Child<Paragraphs<&'static str>>,
}

impl ResultScreen {
    pub fn new(
        fg_color: Color,
        bg_color: Color,
        message_top: Paragraphs<&'static str>,
        message_bottom: Paragraphs<&'static str>,
        complete_draw: bool,
    ) -> Self {
        let mut instance = Self {
            bg: Pad::with_background(bg_color),
            small_pad: Pad::with_background(bg_color),
            fg_color,
            bg_color,
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
            .place(Rect::new(Point::new(0, 0), Point::new(WIDTH, 30)));

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

        // display::icon(
        //     Point::new(screen().center().x, 45),
        //     self.icon,
        //     self.fg_color,
        //     self.bg_color,
        // );
        // display::rect_fill(
        //     Rect::from_top_left_and_size(Point::new(12, 149), Offset::new(216, 1)),
        //     self.fg_color,
        // );
        self.message_top.paint();
        self.message_bottom.paint();
    }

    fn bounds(&self, _sink: &mut dyn FnMut(Rect)) {}
}
