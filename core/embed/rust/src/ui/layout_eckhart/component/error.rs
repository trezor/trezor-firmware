#[cfg(feature = "rgb_led")]
use crate::ui::led::LedState;
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
        ACTION_BAR_HEIGHT, HEADER_HEIGHT, LED_RED, PADDING, RED, SIDE_INSETS, TEXT_NORMAL,
        TEXT_SMALL, TEXT_SMALL_GREY, TEXT_SMALL_GREY_EXTRA_LIGHT, TEXT_SMALL_RED,
        TEXT_VERTICAL_SPACING,
    },
    WAIT_FOR_RESTART_MESSAGE,
};

/// Full-screen component showing Eckhart RSOD. To keep it minimal, this screen
/// does not use any other components.
pub struct ErrorScreen<'a> {
    header: Label<'a>,
    title: Label<'a>,
    message: Label<'a>,
    footer: Label<'a>,
    wait_for_restart: Label<'a>,
    screen_border: ScreenBorder,
}

impl<'a> ErrorScreen<'a> {
    pub fn new(title: TString<'a>, message: TString<'a>, footer: TString<'a>) -> Self {
        let title = Label::left_aligned(title, TEXT_NORMAL);
        let message = Label::left_aligned(message, TEXT_SMALL);
        let footer = Label::left_aligned(footer, TEXT_SMALL_GREY_EXTRA_LIGHT);
        Self {
            header: Label::left_aligned("Failure".into(), TEXT_SMALL_RED).vertically_centered(),
            title,
            message,
            footer,
            screen_border: ScreenBorder::new(RED),
            wait_for_restart: Label::centered(WAIT_FOR_RESTART_MESSAGE.into(), TEXT_SMALL_GREY)
                .vertically_centered(),
        }
    }
}

impl<'a> Component for ErrorScreen<'a> {
    type Msg = Never;

    fn place(&mut self, _bounds: Rect) -> Rect {
        const AREA: Rect = SCREEN.inset(SIDE_INSETS);

        let (header_area, area) = AREA.split_top(HEADER_HEIGHT);
        let (area, actionbar_area) = area.split_bottom(ACTION_BAR_HEIGHT);
        let area = area.inset(Insets::bottom(PADDING));

        let title_height = self.title.text_height(area.width());
        let message_height = self.message.text_height(area.width());
        let footer_height = self.footer.text_height(area.width());
        let (title_area, area) = area.split_top(title_height);
        let (message_area, area) = area
            .inset(Insets::top(TEXT_VERTICAL_SPACING))
            .split_top(message_height);
        let (_, footer_area) = area.split_bottom(footer_height);

        self.header.place(header_area);
        self.title.place(title_area);
        self.message.place(message_area);
        self.footer.place(footer_area);
        self.wait_for_restart.place(actionbar_area);
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
        self.wait_for_restart.render(target);
        self.screen_border.render(u8::MAX, target);
        #[cfg(feature = "rgb_led")]
        target.set_led_state(LedState::Static(LED_RED));
    }
}
