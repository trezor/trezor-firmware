use crate::ui::{
    component::{
        text::paragraphs::{ParagraphStrType, ParagraphVecShort, Paragraphs},
        Child, Component, Event, EventCtx, Never, Pad,
    },
    constant::screen,
    display::{self, Color, Icon},
    geometry::{Point, Rect, CENTER},
};

use crate::ui::model_tt::{
    constant::WIDTH,
    theme::{RESULT_FOOTER_HEIGHT, RESULT_FOOTER_START, RESULT_PADDING},
};

const MESSAGE_AREA_START: i16 = 82;
const ICON_CENTER_Y: i16 = 62;

pub struct ResultScreen<T> {
    bg: Pad,
    footer_pad: Pad,
    fg_color: Color,
    bg_color: Color,
    msg_area_color: Color,
    icon: Icon,
    message: Child<Paragraphs<ParagraphVecShort<T>>>,
    footer: Option<Child<Paragraphs<ParagraphVecShort<T>>>>,
}

impl<T: ParagraphStrType> ResultScreen<T> {
    pub fn new(
        fg_color: Color,
        bg_color: Color,
        msg_area_color: Color,
        icon: Icon,
        message: Paragraphs<ParagraphVecShort<T>>,
        footer: Option<Paragraphs<ParagraphVecShort<T>>>,
        complete_draw: bool,
    ) -> Self {
        let mut instance = Self {
            bg: Pad::with_background(bg_color),
            footer_pad: Pad::with_background(bg_color),
            fg_color,
            bg_color,
            msg_area_color,
            icon,
            message: Child::new(message),
            footer: footer.map(Child::new),
        };

        if complete_draw {
            instance.bg.clear();
        } else {
            instance.footer_pad.clear();
        }
        instance
    }
}

impl<T: ParagraphStrType> Component for ResultScreen<T> {
    type Msg = Never;

    fn place(&mut self, bounds: Rect) -> Rect {
        self.bg.place(screen());

        let message_arae = if let Some(footer) = &mut self.footer {
            let footer_area = Rect::new(
                Point::new(RESULT_PADDING, RESULT_FOOTER_START),
                Point::new(
                    WIDTH - RESULT_PADDING,
                    RESULT_FOOTER_START + RESULT_FOOTER_HEIGHT,
                ),
            );
            self.footer_pad.place(footer_area);
            footer.place(footer_area);
            Rect::new(
                Point::new(RESULT_PADDING, MESSAGE_AREA_START),
                Point::new(WIDTH - RESULT_PADDING, RESULT_FOOTER_START),
            )
        } else {
            Rect::new(
                Point::new(RESULT_PADDING, MESSAGE_AREA_START),
                Point::new(
                    WIDTH - RESULT_PADDING,
                    RESULT_FOOTER_START + RESULT_FOOTER_HEIGHT,
                ),
            )
        };

        self.message.place(message_arae);

        bounds
    }

    fn event(&mut self, _ctx: &mut EventCtx, _event: Event) -> Option<Self::Msg> {
        None
    }

    fn paint(&mut self) {
        self.bg.paint();
        self.footer_pad.paint();

        self.icon.draw(
            Point::new(screen().center().x, ICON_CENTER_Y),
            CENTER,
            self.fg_color,
            self.bg_color,
        );
        self.message.paint();

        if let Some(bottom) = &mut self.footer {
            display::rect_fill_rounded(
                Rect::new(
                    Point::new(RESULT_PADDING, RESULT_FOOTER_START),
                    Point::new(
                        WIDTH - RESULT_PADDING,
                        RESULT_FOOTER_START + RESULT_FOOTER_HEIGHT,
                    ),
                ),
                self.msg_area_color,
                self.bg_color,
                2,
            );
            bottom.paint();
        }
    }
}
