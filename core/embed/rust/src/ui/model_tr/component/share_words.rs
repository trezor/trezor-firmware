use crate::{
    strutil::{ShortString, TString},
    translations::TR,
    ui::{
        component::{
            text::util::{text_multiline, text_multiline2},
            Child, Component, Event, EventCtx, Never, Paginate,
        },
        display::Font,
        geometry::{Alignment, Offset, Rect},
        shape::{self, Renderer},
    },
};

use heapless::Vec;
use ufmt::uwrite;

use super::{common::display_left, scrollbar::SCROLLBAR_SPACE, theme, ScrollBar};

const WORDS_PER_PAGE: usize = 3;
const EXTRA_LINE_HEIGHT: i16 = -2;
const NUMBER_X_OFFSET: i16 = 0;
const WORD_X_OFFSET: i16 = 25;
const NUMBER_FONT: Font = Font::DEMIBOLD;
const WORD_FONT: Font = Font::BIG;
const INFO_TOP_OFFSET: i16 = 20;
const MAX_WORDS: usize = 33; // super-shamir has 33 words, all other have less

/// Showing the given share words.
pub struct ShareWords<'a> {
    area: Rect,
    scrollbar: Child<ScrollBar>,
    share_words: Vec<TString<'a>, MAX_WORDS>,
    page_index: usize,
}

impl<'a> ShareWords<'a> {
    pub fn new(share_words: Vec<TString<'a>, MAX_WORDS>) -> Self {
        let mut instance = Self {
            area: Rect::zero(),
            scrollbar: Child::new(ScrollBar::to_be_filled_later()),
            share_words,
            page_index: 0,
        };
        let page_count = instance.total_page_count();
        let scrollbar = ScrollBar::new(page_count);
        instance.scrollbar = Child::new(scrollbar);
        instance
    }

    fn word_index(&self) -> usize {
        self.page_index * WORDS_PER_PAGE
    }

    fn is_final_page(&self) -> bool {
        self.page_index == self.total_page_count() - 1
    }

    fn total_page_count(&self) -> usize {
        let word_screens = if self.share_words.len() % WORDS_PER_PAGE == 0 {
            self.share_words.len() / WORDS_PER_PAGE
        } else {
            self.share_words.len() / WORDS_PER_PAGE + 1
        };
        // One page after the words
        word_screens + 1
    }

    fn get_final_text(&self) -> ShortString {
        TR::share_words__wrote_down_all.map_translated(|wrote_down_all| {
            TR::share_words__words_in_order.map_translated(|in_order| {
                uformat!("{}{}{}", wrote_down_all, self.share_words.len(), in_order)
            })
        })
    }

    /// Display the final page with user confirmation.
    fn paint_final_page(&mut self) {
        let final_text = self.get_final_text();
        text_multiline(
            self.area.split_top(INFO_TOP_OFFSET).1,
            final_text.as_str().into(),
            Font::NORMAL,
            theme::FG,
            theme::BG,
            Alignment::Start,
        );
    }

    /// Display the final page with user confirmation.
    fn render_final_page<'s>(&'s self, target: &mut impl Renderer<'s>) {
        let final_text = self.get_final_text();
        text_multiline2(
            target,
            self.area.split_top(INFO_TOP_OFFSET).1,
            final_text.as_str().into(),
            Font::NORMAL,
            theme::FG,
            theme::BG,
            Alignment::Start,
        );
    }

    /// Display current set of recovery words.
    fn paint_words(&mut self) {
        let mut y_offset = 0;
        // Showing the word index and the words itself
        for i in 0..WORDS_PER_PAGE {
            y_offset += NUMBER_FONT.line_height() + EXTRA_LINE_HEIGHT;
            let index = self.word_index() + i;
            if index >= self.share_words.len() {
                break;
            }
            let baseline = self.area.top_left() + Offset::y(y_offset);
            let ordinal = uformat!("{}.", index + 1);
            display_left(baseline + Offset::x(NUMBER_X_OFFSET), &ordinal, NUMBER_FONT);
            let word = &self.share_words[index];
            word.map(|w| {
                display_left(baseline + Offset::x(WORD_X_OFFSET), w, WORD_FONT);
            });
        }
    }

    /// Display current set of recovery words.
    fn render_words<'s>(&'s self, target: &mut impl Renderer<'s>) {
        let mut y_offset = 0;
        // Showing the word index and the words itself
        for i in 0..WORDS_PER_PAGE {
            y_offset += NUMBER_FONT.line_height() + EXTRA_LINE_HEIGHT;
            let index = self.word_index() + i;
            if index >= self.share_words.len() {
                break;
            }
            let word = &self.share_words[index];
            let baseline = self.area.top_left() + Offset::y(y_offset);
            let ordinal = uformat!("{}.", index + 1);

            shape::Text::new(baseline + Offset::x(NUMBER_X_OFFSET), &ordinal)
                .with_font(NUMBER_FONT)
                .with_fg(theme::FG)
                .render(target);

            word.map(|w| {
                shape::Text::new(baseline + Offset::x(WORD_X_OFFSET), w)
                    .with_font(WORD_FONT)
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

    fn paint(&mut self) {
        // Showing scrollbar in all cases
        // Individual pages are responsible for not colliding with it
        self.scrollbar.paint();
        if self.is_final_page() {
            self.paint_final_page();
        } else {
            self.paint_words();
        }
    }

    fn render<'s>(&'s self, target: &mut impl Renderer<'s>) {
        // Showing scrollbar in all cases
        // Individual pages are responsible for not colliding with it
        self.scrollbar.render(target);
        if self.is_final_page() {
            self.render_final_page(target);
        } else {
            self.render_words(target);
        }
    }
}

impl<'a> Paginate for ShareWords<'a> {
    fn page_count(&mut self) -> usize {
        // Not defining the logic here, as we do not want it to be `&mut`.
        self.total_page_count()
    }

    fn change_page(&mut self, active_page: usize) {
        self.page_index = active_page;
        self.scrollbar.change_page(active_page);
    }
}

// DEBUG-ONLY SECTION BELOW

#[cfg(feature = "ui_debug")]
impl<'a> crate::trace::Trace for ShareWords<'a> {
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.component("ShareWords");
        let content = if self.is_final_page() {
            self.get_final_text()
        } else {
            let mut content = ShortString::new();
            for i in 0..WORDS_PER_PAGE {
                let index = self.word_index() + i;
                if index >= self.share_words.len() {
                    break;
                }
                self.share_words[index]
                    .map(|word| unwrap!(uwrite!(content, "{}. {}\n", index + 1, word)));
            }
            content
        };
        t.string("screen_content", content.as_str().into());
    }
}
