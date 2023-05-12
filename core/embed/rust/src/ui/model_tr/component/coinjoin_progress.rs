use crate::{
    micropython::buffer::StrBuffer,
    ui::{
        component::{base::Never, Component, Event, EventCtx},
        display::{text_multiline_split_words, Font},
        geometry::{Alignment, Rect},
    },
};

use super::theme;

const HEADER: &str = "COINJOIN IN PROGRESS";
const FOOTER: &str = "Don't disconnect your Trezor";

pub struct CoinJoinProgress {
    text: StrBuffer,
    area: Rect,
}

impl CoinJoinProgress {
    pub fn new(text: StrBuffer, _indeterminate: bool) -> Self {
        Self {
            text,
            area: Rect::zero(),
        }
    }
}

impl Component for CoinJoinProgress {
    type Msg = Never;

    fn place(&mut self, bounds: Rect) -> Rect {
        self.area = bounds;
        bounds
    }

    fn event(&mut self, _ctx: &mut EventCtx, _event: Event) -> Option<Self::Msg> {
        None
    }

    fn paint(&mut self) {
        // Trying to paint all three parts into the area, stopping if any of them
        // doesn't fit.
        let mut possible_rest = text_multiline_split_words(
            self.area,
            HEADER,
            Font::NORMAL,
            theme::FG,
            theme::BG,
            Alignment::Center,
        );
        if let Some(rest) = possible_rest {
            possible_rest = text_multiline_split_words(
                rest,
                self.text.as_ref(),
                Font::MONO,
                theme::FG,
                theme::BG,
                Alignment::Center,
            );
        } else {
            return;
        }
        if let Some(rest) = possible_rest {
            text_multiline_split_words(
                rest,
                FOOTER,
                Font::BOLD,
                theme::FG,
                theme::BG,
                Alignment::Center,
            );
        }
    }
}

#[cfg(feature = "ui_debug")]
impl crate::trace::Trace for CoinJoinProgress {
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.component("CoinJoinProgress");
        t.string("text", self.text.as_ref());
    }
}
