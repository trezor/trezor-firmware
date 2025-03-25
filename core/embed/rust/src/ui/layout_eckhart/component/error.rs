use crate::{
    strutil::TString,
    ui::{
        component::{Component, Event, EventCtx, Label, Never},
        constant::SCREEN,
        geometry::{Insets, Rect},
        shape::Renderer,
    },
};

use super::super::{
    cshape::ScreenBorder,
    theme::{
        ACTION_BAR_HEIGHT, HEADER_HEIGHT, RED, SIDE_INSETS, TEXT_NORMAL, TEXT_SMALL,
        TEXT_SMALL_GREY, TEXT_SMALL_RED, TEXT_VERTICAL_SPACING,
    },
};

/// Full-screen component showing Eckhart RSOD. To keep it minimal, this screen
/// does not use any other components.
pub struct ErrorScreen<'a> {
    header: Label<'a>,
    title: Label<'a>,
    message: Label<'a>,
    footer: Label<'a>,
    screen_border: ScreenBorder,
}

impl<'a> ErrorScreen<'a> {
    pub fn new(title: TString<'a>, message: TString<'a>, footer: TString<'a>) -> Self {
        let header = Label::left_aligned("Failure".into(), TEXT_SMALL_RED).vertically_centered();
        let title = Label::left_aligned(title, TEXT_NORMAL);
        let message = Label::left_aligned(message, TEXT_SMALL);
        let footer = Label::centered(footer, TEXT_SMALL_GREY).vertically_centered();

        Self {
            header,
            title,
            message,
            footer,
            screen_border: ScreenBorder::new(RED),
        }
    }
}

impl<'a> Component for ErrorScreen<'a> {
    type Msg = Never;

    fn place(&mut self, _bounds: Rect) -> Rect {
        let area = SCREEN.inset(SIDE_INSETS);

        let (header_area, area) = area.split_top(HEADER_HEIGHT);
        let (area, footer_area) = area.split_bottom(ACTION_BAR_HEIGHT);

        let title_height = self.title.text_height(area.width());
        let message_height = self.message.text_height(area.width());
        let (title_area, area) = area.split_top(title_height);
        let (message_area, _) = area
            .inset(Insets::top(TEXT_VERTICAL_SPACING))
            .split_top(message_height);

        self.header.place(header_area);
        self.title.place(title_area);
        self.message.place(message_area);
        self.footer.place(footer_area);
        SCREEN
    }

    fn event(&mut self, _ctx: &mut EventCtx, _event: Event) -> Option<Self::Msg> {
        None
    }

    fn render<'s>(&'s self, target: &mut impl Renderer<'s>) {
        self.header.render(target);
        self.title.render(target);
        self.message.render(target);
        self.footer.render(target);
        self.screen_border.render(u8::MAX, target);
    }
}
