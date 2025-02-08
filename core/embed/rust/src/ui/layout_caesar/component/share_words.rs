use crate::{
    strutil::{ShortString, TString},
    translations::TR,
    ui::{
        component::{
            text::util::text_multiline, Child, Component, Event, EventCtx, Never, PaginateFull,
        },
        display::Font,
        geometry::{Alignment, Offset, Rect},
        shape::{self, Renderer},
        util::Pager,
    },
};

use heapless::Vec;
#[cfg(feature = "ui_debug")]
use ufmt::uwrite;

use super::{super::fonts, scrollbar::SCROLLBAR_SPACE, theme, ScrollBar};

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
    scrollbar: Child<ScrollBar>,
    share_words: Vec<TString<'a>, MAX_WORDS>,
    pager: Pager,
}

impl<'a> ShareWords<'a> {
    pub fn new(share_words: Vec<TString<'a>, MAX_WORDS>) -> Self {
        let total_page_count = {
            let words_screen = if share_words.len() % WORDS_PER_PAGE == 0 {
                share_words.len() / WORDS_PER_PAGE
            } else {
                share_words.len() / WORDS_PER_PAGE + 1
            };
            // One page after the words
            words_screen + 1
        };
        Self {
            area: Rect::zero(),
            scrollbar: Child::new(ScrollBar::new(total_page_count)),
            share_words,
            pager: Pager::new(total_page_count as u16),
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
        let (top_area, _) = bounds.split_top(theme::FONT_HEADER.line_height());

        let (_, scrollbar_area) =
            top_area.split_right(self.scrollbar.inner().overall_width() + SCROLLBAR_SPACE);

        self.scrollbar.place(scrollbar_area);

        self.area = bounds;
        self.area
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        self.scrollbar.event(ctx, event);
        None
    }

    fn render<'s>(&'s self, target: &mut impl Renderer<'s>) {
        // Showing scrollbar in all cases
        // Individual pages are responsible for not colliding with it
        self.scrollbar.render(target);
        if self.pager().is_last() {
            self.render_final_page(target);
        } else {
            self.render_words(target);
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
        self.scrollbar.change_page(to_page);
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
