use heapless::Vec;
#[cfg(feature = "ui_debug")]
use ufmt::uwrite;

use super::super::fonts;
use super::theme;
use crate::strutil::{ShortString, TString};
use crate::translations::TR;
use crate::ui::component::text::util::text_multiline;
use crate::ui::component::{Component, Event, EventCtx, Never, Paginate};
use crate::ui::display::Font;
use crate::ui::geometry::{Alignment, Offset, Rect};
use crate::ui::shape::{self, Renderer};
use crate::ui::util::Pager;

const WORDS_PER_PAGE: usize = 3;
const EXTRA_LINE_HEIGHT: i16 = -2;
const NUMBER_X_OFFSET: i16 = 0;
const WORD_X_OFFSET: i16 = 25;
const NUMBER_FONT: Font = fonts::FONT_DEMIBOLD;
const WORD_FONT: Font = fonts::FONT_BIG;
const INFO_TOP_OFFSET: i16 = 20;
const MAX_WORDS: usize = 33; // super-shamir has 33 words, all other have less

/// Showing the given share words.
pub struct ShareWords<'a> {
    area: Rect,
    share_words: Vec<TString<'a>, MAX_WORDS>,
    pager: Pager,
}

impl<'a> ShareWords<'a> {
    pub fn new(share_words: Vec<TString<'a>, MAX_WORDS>) -> Self {
        let total_page_count = {
            let words_screen = share_words.len().div_ceil(WORDS_PER_PAGE);
            // One page after the words
            words_screen as u16 + 1
        };
        Self {
            area: Rect::zero(),
            share_words,
            pager: Pager::new(total_page_count),
        }
    }

    fn word_index(&self) -> usize {
        self.pager.current() as usize * WORDS_PER_PAGE
    }

    fn get_final_text(&self) -> ShortString {
        TR::share_words__wrote_down_all.map_translated(|wrote_down_all| {
            TR::share_words__words_in_order.map_translated(|in_order| {
                uformat!("{}{}{}", wrote_down_all, self.share_words.len(), in_order)
            })
        })
    }

    /// Display the final page with user confirmation.
    fn render_final_page<'s>(&'s self, target: &mut impl Renderer<'s>) {
        let final_text = self.get_final_text();
        text_multiline(
            target,
            self.area.split_top(INFO_TOP_OFFSET).1,
            final_text.as_str().into(),
            fonts::FONT_NORMAL,
            theme::FG,
            theme::BG,
            Alignment::Start,
        );
    }

    /// Display current set of recovery words.
    fn render_words<'s>(&'s self, target: &mut impl Renderer<'s>) {
        let mut y_offset = 0;
        // Showing the word index and the words itself
        for (word_idx, word) in self
            .share_words
            .iter()
            .enumerate()
            .skip(self.pager().current() as usize * WORDS_PER_PAGE)
            .take(WORDS_PER_PAGE)
        {
            let ordinal = word_idx + 1;
            y_offset += NUMBER_FONT.line_height() + EXTRA_LINE_HEIGHT;
            let base = self.area.top_left() + Offset::y(y_offset);

            let ordinal_txt = uformat!("{}.", ordinal);
            shape::Text::new(base + Offset::x(NUMBER_X_OFFSET), &ordinal_txt, NUMBER_FONT)
                .with_fg(theme::FG)
                .render(target);
            word.map(|w| {
                shape::Text::new(base + Offset::x(WORD_X_OFFSET), w, WORD_FONT)
                    .with_fg(theme::FG)
                    .render(target);
            });
        }
    }
}

impl<'a> Component for ShareWords<'a> {
    type Msg = Never;

    fn place(&mut self, bounds: Rect) -> Rect {
        self.area = bounds;
        self.area
    }

    fn event(&mut self, _ctx: &mut EventCtx, _event: Event) -> Option<Self::Msg> {
        None
    }

    fn render<'s>(&'s self, target: &mut impl Renderer<'s>) {
        if self.pager().is_last() {
            self.render_final_page(target);
        } else {
            self.render_words(target);
        }
    }
}

impl<'a> Paginate for ShareWords<'a> {
    fn pager(&self) -> Pager {
        self.pager
    }

    fn change_page(&mut self, active_page: u16) {
        self.pager.set_current(active_page);
    }
}

// DEBUG-ONLY SECTION BELOW

#[cfg(feature = "ui_debug")]
impl<'a> crate::trace::Trace for ShareWords<'a> {
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.component("ShareWords");
        let content = if self.pager().is_last() {
            self.get_final_text()
        } else {
            let mut content = ShortString::new();
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
            content
        };
        t.string("screen_content", content.as_str().into());
    }
}
