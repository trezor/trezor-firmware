use crate::{
    strutil::TString,
    ui::{
        component::{Component, Event, EventCtx, Never, PaginateFull},
        display::Font,
        geometry::{Offset, Rect},
        shape::{self, Renderer},
        util::Pager,
    },
};

use super::super::{fonts, theme};

use heapless::Vec;
#[cfg(feature = "ui_debug")]
use ufmt::uwrite;

const WORDS_PER_PAGE: usize = 4;
const TOP_PADDING_OFFSET: i16 = 13;
const WORD_FONT: Font = fonts::FONT_MONO;
const MAX_WORDS: usize = 33; // super-shamir has 33 words, all other have less

/// Showing the given share words.
pub struct ShareWords<'a> {
    area: Rect,
    share_words: Vec<TString<'a>, MAX_WORDS>,
    pager: Pager,
}

impl<'a> ShareWords<'a> {
    pub fn new(share_words: Vec<TString<'a>, MAX_WORDS>) -> Self {
        let total_page_count = (share_words.len() + WORDS_PER_PAGE - 1) / WORDS_PER_PAGE;
        Self {
            area: Rect::zero(),
            share_words,
            pager: Pager::new(total_page_count as u16),
        }
    }
}

impl<'a> Component for ShareWords<'a> {
    type Msg = Never;

    fn place(&mut self, bounds: Rect) -> Rect {
        self.area = bounds;
        bounds
    }

    fn event(&mut self, _ctx: &mut EventCtx, _event: Event) -> Option<Self::Msg> {
        None
    }

    fn render<'s>(&'s self, target: &mut impl Renderer<'s>) {
        let line_height = WORD_FONT.line_height();
        let ordinal_largest_on_this_page =
            (WORDS_PER_PAGE * (self.pager.current() as usize + 1)).min(self.share_words.len());
        let is_largest_double_digit = ordinal_largest_on_this_page >= 10;
        let mut y_offset = self.area.top_left().y + TOP_PADDING_OFFSET;

        for (word_idx, word) in self
            .share_words
            .iter()
            .enumerate()
            .skip(self.pager().current() as usize * WORDS_PER_PAGE)
            .take(WORDS_PER_PAGE)
        {
            let ordinal = word_idx + 1;
            let base = self.area.top_left() + Offset::y(y_offset);
            word.map(|w| {
                let double_digit = ordinal >= 10;
                let text_fmt = if double_digit || !is_largest_double_digit {
                    uformat!("{}. {}", ordinal, w)
                } else {
                    uformat!(" {}. {}", ordinal, w)
                };
                shape::Text::new(base, &text_fmt, WORD_FONT)
                    .with_fg(theme::FG)
                    .render(target);
            });
            y_offset += line_height;
        }
    }
}

impl<'a> PaginateFull for ShareWords<'a> {
    fn pager(&self) -> Pager {
        self.pager
    }

    fn change_page(&mut self, active_page: u16) {
        let to_page = active_page.min(self.pager.total() - 1);
        self.pager.set_current(to_page);
    }
}

// DEBUG-ONLY SECTION BELOW

#[cfg(feature = "ui_debug")]
impl<'a> crate::trace::Trace for ShareWords<'a> {
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.component("ShareWords");
        let mut content = heapless::String::<64>::new();
        for (word_idx, word) in self
            .share_words
            .iter()
            .enumerate()
            .skip(self.pager().current() as usize * WORDS_PER_PAGE)
            .take(WORDS_PER_PAGE)
        {
            let ordinal = word_idx + 1;
            word.map(|w| unwrap!(uwrite!(content, "{}. {}\n", ordinal, w)));
        }
        t.string("screen_content", content.as_str().into());
    }
}
