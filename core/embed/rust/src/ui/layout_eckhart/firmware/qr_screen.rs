use crate::{
    strutil::TString,
    ui::{
        component::{swipe_detect::SwipeConfig, Component, Event, EventCtx, Qr},
        flow::Swipable,
        geometry::{Insets, Rect},
        shape::{self, Renderer},
        util::Pager,
    },
};

use super::super::{
    constant::SCREEN,
    firmware::{theme, ActionBar, Header, HeaderMsg},
};

pub enum QrMsg {
    Cancelled,
}

pub struct QrScreen {
    header: Header,
    qr: Qr,
    action_bar: Option<ActionBar>,
    pad: Rect,
}

impl QrScreen {
    const QR_PADDING: i16 = 8;
    const QR_HEIGHT: i16 = 300;
    const QR_PAD_RADIUS: i16 = 12;

    pub fn new(qr: Qr) -> Self {
        Self {
            header: Header::new(TString::empty()),
            qr,
            action_bar: None,
            pad: Rect::zero(),
        }
    }

    pub fn with_header(mut self, header: Header) -> Self {
        self.header = header;
        self
    }

    pub fn with_action_bar(mut self, action_bar: ActionBar) -> Self {
        self.action_bar = Some(action_bar);
        self
    }
}

impl Component for QrScreen {
    type Msg = QrMsg;

    fn place(&mut self, bounds: Rect) -> Rect {
        // assert full screen
        debug_assert_eq!(bounds.height(), SCREEN.height());
        debug_assert_eq!(bounds.width(), SCREEN.width());

        let (header_area, mut rest) = bounds.split_top(Header::HEADER_HEIGHT);
        if let Some(action_bar) = &mut self.action_bar {
            let action_bar_area;
            (rest, action_bar_area) = rest.split_bottom(ActionBar::ACTION_BAR_HEIGHT);
            action_bar.place(action_bar_area);
        }
        let (qr_pad, _) = rest.split_top(Self::QR_HEIGHT + 2 * Self::QR_PADDING);

        let side_padding = (SCREEN.width() - Self::QR_HEIGHT - 2 * Self::QR_PADDING) / 2;
        let qr_pad = qr_pad.inset(Insets::sides(side_padding));

        self.pad = qr_pad;

        self.header.place(header_area);
        self.qr.place(qr_pad.shrink(Self::QR_PADDING));

        bounds
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        if let Some(HeaderMsg::Cancelled) = self.header.event(ctx, event) {
            return Some(QrMsg::Cancelled);
        }
        None
    }

    fn render<'s>(&'s self, target: &mut impl Renderer<'s>) {
        // Render white QR pad
        shape::Bar::new(self.pad)
            .with_bg(theme::FG)
            .with_fg(theme::FG)
            .with_radius(Self::QR_PAD_RADIUS)
            .render(target);

        self.header.render(target);
        self.qr.render(target);
        self.action_bar.render(target);
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

#[cfg(test)]
mod tests {
    use super::{super::super::constant::SCREEN, *};

    #[test]
    fn test_component_heights_fit_screen() {
        assert!(
            QrScreen::QR_HEIGHT
                + 2 * QrScreen::QR_PADDING
                + Header::HEADER_HEIGHT
                + ActionBar::ACTION_BAR_HEIGHT
                <= SCREEN.height(),
            "Components overflow the screen height",
        );
    }
}
