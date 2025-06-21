use crate::ui::{
    component::{Component, Event, EventCtx, Label, Never},
    geometry::{Alignment2D, Rect},
    shape::{self, Renderer},
};

use super::super::{constant::SCREEN, theme};

pub struct UpdateScreen {
    text_header: Label<'static>,
    text_message: Label<'static>,
    text_footer: Label<'static>,
    icon_area: Rect,
}

impl UpdateScreen {
    const UPDATE_HEADER: &'static str = "Update done";
    const UPDATE_MESSAGE: &'static str = "Completing final steps...";
    const UPDATE_FOOTER: &'static str = "Wait";

    pub fn new() -> Self {
        Self {
            text_header: Label::left_aligned(Self::UPDATE_HEADER.into(), theme::TEXT_SMALL_GREY)
                .vertically_centered(),
            text_message: Label::left_aligned(Self::UPDATE_MESSAGE.into(), theme::TEXT_NORMAL),
            text_footer: Label::centered(Self::UPDATE_FOOTER.into(), theme::TEXT_SMALL_GREY)
                .vertically_centered(),
            icon_area: Rect::zero(),
        }
    }
}

impl Component for UpdateScreen {
    type Msg = Never;

    fn place(&mut self, _bounds: Rect) -> Rect {
        const ICON_RIGHT_MARGIN: i16 = 16;

        let rest = SCREEN.inset(theme::SIDE_INSETS);
        let (header_area, rest) = rest.split_top(theme::HEADER_HEIGHT);
        let (message_area, footer_area) = rest.split_bottom(theme::ACTION_BAR_HEIGHT);
        let icon_width_with_margin = theme::ICON_DONE.toif.width() + ICON_RIGHT_MARGIN;
        let (icon_area, title_area) = header_area.split_left(icon_width_with_margin);

        self.icon_area = icon_area;

        self.text_header.place(title_area);
        self.text_message.place(message_area);
        self.text_footer.place(footer_area);

        SCREEN
    }

    fn event(&mut self, _ctx: &mut EventCtx, _event: Event) -> Option<Self::Msg> {
        None
    }

    fn render<'s>(&'s self, target: &mut impl Renderer<'s>) {
        shape::ToifImage::new(self.icon_area.left_center(), theme::ICON_DONE.toif)
            .with_fg(theme::GREY)
            .with_align(Alignment2D::CENTER_LEFT)
            .render(target);
        self.text_header.render(target);
        self.text_message.render(target);
        self.text_footer.render(target);
    }
}
