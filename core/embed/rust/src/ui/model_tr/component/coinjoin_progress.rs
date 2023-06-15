use crate::{
    strutil::StringType,
    ui::{
        component::{
            base::Never,
            text::util::{text_multiline, text_multiline_bottom},
            Component, Event, EventCtx,
        },
        display::Font,
        geometry::{Alignment, Insets, Rect},
    },
};

use super::theme;

const HEADER: &str = "COINJOIN IN PROGRESS";
const FOOTER: &str = "Do not disconnect your Trezor!";
const FOOTER_TEXT_MARGIN: i16 = 8;

pub struct CoinJoinProgress<T> {
    text: T,
    area: Rect,
    indeterminate: bool,
}

impl<T> CoinJoinProgress<T>
where
    T: StringType,
{
    pub fn new(text: T, indeterminate: bool) -> Self {
        Self {
            text,
            area: Rect::zero(),
            indeterminate,
        }
    }
}

impl<T> Component for CoinJoinProgress<T>
where
    T: StringType,
{
    type Msg = Never;

    fn place(&mut self, bounds: Rect) -> Rect {
        self.area = bounds;
        bounds
    }

    fn event(&mut self, _ctx: &mut EventCtx, _event: Event) -> Option<Self::Msg> {
        None
    }

    fn paint(&mut self) {
        // TOP
        if self.indeterminate {
            text_multiline(
                self.area,
                HEADER,
                Font::BOLD,
                theme::FG,
                theme::BG,
                Alignment::Center,
            );
        }

        // CENTER

        // BOTTOM
        let top_rest = text_multiline_bottom(
            self.area,
            FOOTER,
            Font::BOLD,
            theme::FG,
            theme::BG,
            Alignment::Center,
        );
        if let Some(rest) = top_rest {
            text_multiline_bottom(
                rest.inset(Insets::bottom(FOOTER_TEXT_MARGIN)),
                self.text.as_ref(),
                Font::NORMAL,
                theme::FG,
                theme::BG,
                Alignment::Center,
            );
        }
    }
}

#[cfg(feature = "ui_debug")]
impl<T> crate::trace::Trace for CoinJoinProgress<T>
where
    T: StringType,
{
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.component("CoinJoinProgress");
        t.string("header", HEADER);
        t.string("text", self.text.as_ref());
        t.string("footer", FOOTER);
    }
}
