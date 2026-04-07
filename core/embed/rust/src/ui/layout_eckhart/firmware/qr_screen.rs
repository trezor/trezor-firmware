use crate::{
    strutil::TString,
    ui::{
        component::{swipe_detect::SwipeConfig, Component, Event, EventCtx, Label, Pad, Qr},
        flow::Swipable,
        geometry::{Alignment, Insets, Rect},
        shape::Renderer,
        util::Pager,
    },
};

use super::super::{
    component::{Button, ButtonMsg},
    constant::SCREEN,
    firmware::{theme, Header},
};

pub enum QrMsg {
    Cancelled,
}

pub struct QrScreen {
    title: Label<'static>,
    close_button: Button,
    qr: Qr,
    pad: Pad,
}

impl QrScreen {
    const BUTTON_WIDTH: i16 = 80; // [px]
    pub fn new(title: TString<'static>, qr: Qr) -> Self {
        Self {
            title: Label::new(title, Alignment::Start, theme::TEXT_SMALL_BLACK)
                .vertically_centered(),
            qr,
            pad: Pad::with_background(theme::FG),
            close_button: Button::with_icon(theme::ICON_CLOSE)
                .styled(theme::button_header_inverted()),
        }
    }
}

impl Component for QrScreen {
    type Msg = QrMsg;

    fn place(&mut self, bounds: Rect) -> Rect {
        // assert full screen
        debug_assert_eq!(bounds.height(), SCREEN.height());
        debug_assert_eq!(bounds.width(), SCREEN.width());

        let (header_area, mut qr_area) = bounds.split_top(Header::HEADER_HEIGHT);
        let (mut title_area, button_area) = header_area.split_right(Self::BUTTON_WIDTH);
        title_area = title_area.inset(Insets::left(theme::SIDE_INSETS.left));

        qr_area = qr_area.inset(theme::SIDE_INSETS);
        qr_area = qr_area.with_height(qr_area.width());

        self.pad.place(bounds);
        self.title.place(title_area);
        self.close_button.place(button_area);
        self.qr.place(qr_area);

        bounds
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        if let Some(ButtonMsg::Clicked) = self.close_button.event(ctx, event) {
            return Some(QrMsg::Cancelled);
        }

        None
    }

    fn render<'s>(&'s self, target: &mut impl Renderer<'s>) {
        self.pad.render(target);
        self.title.render(target);
        self.close_button.render(target);
        self.qr.render(target);
    }
}

#[cfg(feature = "micropython")]
impl Swipable for QrScreen {
    fn get_swipe_config(&self) -> SwipeConfig {
        SwipeConfig::new()
    }

    fn get_pager(&self) -> Pager {
        Pager::single_page()
    }
}

#[cfg(feature = "ui_debug")]
impl crate::trace::Trace for QrScreen {
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.component("QrScreen");
    }
}
