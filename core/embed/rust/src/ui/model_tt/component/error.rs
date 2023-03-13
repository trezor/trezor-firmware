use crate::ui::{
    component::{
        text::paragraphs::{ParagraphStrType, ParagraphVecShort, Paragraphs},
        Child, Component, Event, EventCtx, Label, Never, Pad,
    },
    constant::screen,
    display::{self, Icon},
    geometry::{Alignment::Center, Point, Rect, TOP_CENTER},
};

use crate::ui::model_tt::{
    constant::WIDTH,
    theme::{
        FATAL_ERROR_COLOR, FATAL_ERROR_HIGHLIGHT_COLOR, ICON_WARNING40, RESULT_FOOTER_HEIGHT,
        RESULT_FOOTER_START, RESULT_PADDING, TEXT_ERROR_BOLD, WHITE,
    },
};

const TITLE_AREA_START: i16 = 70;
const ICON_TOP: i16 = 27;

pub struct ErrorScreen<T> {
    bg: Pad,
    title: Child<Label<T>>,
    message: Child<Paragraphs<ParagraphVecShort<T>>>,
    footer: Child<Paragraphs<ParagraphVecShort<T>>>,
}

impl<T: ParagraphStrType> ErrorScreen<T> {
    pub fn new(
        title: T,
        message: Paragraphs<ParagraphVecShort<T>>,
        footer: Paragraphs<ParagraphVecShort<T>>,
    ) -> Self {
        let title = Label::new(title, Center, TEXT_ERROR_BOLD);
        Self {
            bg: Pad::with_background(FATAL_ERROR_COLOR).with_clear(),
            title: Child::new(title),
            message: Child::new(message),
            footer: Child::new(footer),
        }
    }
}

impl<T: ParagraphStrType> Component for ErrorScreen<T> {
    type Msg = Never;

    fn place(&mut self, bounds: Rect) -> Rect {
        self.bg.place(screen());

        let title_area = Rect::new(
            Point::new(RESULT_PADDING, TITLE_AREA_START),
            Point::new(WIDTH - RESULT_PADDING, RESULT_FOOTER_START),
        );

        self.title.place(title_area);

        let (_, message_area) = title_area.split_top(self.title.inner().area().height());

        self.message.place(message_area);

        let bottom_area = Rect::new(
            Point::new(RESULT_PADDING, RESULT_FOOTER_START),
            Point::new(
                WIDTH - RESULT_PADDING,
                RESULT_FOOTER_START + RESULT_FOOTER_HEIGHT,
            ),
        );
        self.footer.place(bottom_area);

        bounds
    }

    fn event(&mut self, _ctx: &mut EventCtx, _event: Event) -> Option<Self::Msg> {
        None
    }

    fn paint(&mut self) {
        self.bg.paint();

        let icon = Icon::new(ICON_WARNING40);
        icon.draw(
            Point::new(screen().center().x, ICON_TOP),
            TOP_CENTER,
            WHITE,
            FATAL_ERROR_COLOR,
        );
        self.title.paint();
        self.message.paint();

        display::rect_fill_rounded(
            Rect::new(
                Point::new(RESULT_PADDING, RESULT_FOOTER_START),
                Point::new(
                    WIDTH - RESULT_PADDING,
                    RESULT_FOOTER_START + RESULT_FOOTER_HEIGHT,
                ),
            ),
            FATAL_ERROR_HIGHLIGHT_COLOR,
            FATAL_ERROR_COLOR,
            2,
        );
        self.footer.paint();
    }
}
