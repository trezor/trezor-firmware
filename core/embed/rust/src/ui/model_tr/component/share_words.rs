use crate::{
    micropython::buffer::StrBuffer,
    ui::{
        component::{Component, Event, EventCtx, Never, Paginate},
        display::{text_multiline, Font},
        geometry::{Offset, Rect},
        model_tr::theme,
    },
};

use heapless::{String, Vec};

use super::common::display;

const WORDS_PER_PAGE: usize = 3;
const EXTRA_LINE_HEIGHT: i16 = 2;
const NUMBER_X_OFFSET: i16 = 5;
const NUMBER_WORD_OFFSET: i16 = 20;
const NUMBER_FONT: Font = Font::DEMIBOLD;
const WORD_FONT: Font = Font::NORMAL;

/// Showing the given share words.
pub struct ShareWords<const N: usize> {
    area: Rect,
    share_words: Vec<StrBuffer, N>,
    page_index: usize,
}

impl<const N: usize> ShareWords<N> {
    pub fn new(share_words: Vec<StrBuffer, N>) -> Self {
        Self {
            area: Rect::zero(),
            share_words,
            page_index: 0,
        }
    }

    fn word_index(&self) -> usize {
        (self.page_index - 1) * WORDS_PER_PAGE
    }

    fn is_entry_page(&self) -> bool {
        self.page_index == 0
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
        // One page before the words, one after it
        1 + word_screens + 1
    }

    /// Display the first page with user information.
    fn render_entry_page(&self) {
        // TODO: will it be always 12, or do we need to check the length?
        // It would need creating a String out of it, which is not ideal.
        let free_area = text_multiline(
            self.area,
            "Write all 12\nwords in order on\nrecovery seed card.",
            Font::BOLD,
            theme::FG,
            theme::BG,
        );
        if let Some(free_area) = free_area {
            // Creating a small vertical distance
            text_multiline(
                free_area.split_top(3).1,
                "Do NOT make\ndigital copies!",
                Font::MONO,
                theme::FG,
                theme::BG,
            );
        }
    }

    /// Display the final page with user confirmation.
    fn render_final_page(&self) {
        // Moving vertically down to avoid collision with the scrollbar
        // and to look better.
        text_multiline(
            self.area.split_top(12).1,
            "I wrote down all\n12 words in order.",
            Font::MONO,
            theme::FG,
            theme::BG,
        );
    }

    /// Display current set of recovery words.
    fn render_words(&self) {
        let mut y_offset = 0;
        // Showing the word index and the words itself
        for i in 0..WORDS_PER_PAGE {
            y_offset += NUMBER_FONT.line_height() + EXTRA_LINE_HEIGHT;
            let index = self.word_index() + i;
            let word = self.share_words[index].clone();
            let baseline = self.area.top_left() + Offset::new(NUMBER_X_OFFSET, y_offset);
            display(baseline, &inttostr!(index as u8 + 1), NUMBER_FONT);
            display(baseline + Offset::x(NUMBER_WORD_OFFSET), &word, WORD_FONT);
        }
    }
}

impl<const N: usize> Component for ShareWords<N> {
    type Msg = Never;

    fn place(&mut self, bounds: Rect) -> Rect {
        self.area = bounds;
        self.area
    }

    fn event(&mut self, _ctx: &mut EventCtx, _event: Event) -> Option<Self::Msg> {
        None
    }

    fn paint(&mut self) {
        if self.is_entry_page() {
            self.render_entry_page();
        } else if self.is_final_page() {
            self.render_final_page();
        } else {
            self.render_words();
        }
    }
}

impl<const N: usize> Paginate for ShareWords<N> {
    fn page_count(&mut self) -> usize {
        // Not defining the logic here, as we do not want it to be `&mut`.
        self.total_page_count()
    }

    fn change_page(&mut self, active_page: usize) {
        self.page_index = active_page;
    }
}

#[cfg(feature = "ui_debug")]
impl<const N: usize> crate::trace::Trace for ShareWords<N> {
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.open("ShareWords");
        t.content_flag();
        if self.is_entry_page() {
            t.string("entry page");
        } else if self.is_final_page() {
            t.string("final page");
        } else {
            for i in 0..WORDS_PER_PAGE {
                let index = self.word_index() + i;
                let word = self.share_words[index].clone();
                let content = build_string!(20, inttostr!(index as u8 + 1), " ", &word, "\n");
                t.string(&content);
            }
        }
        t.content_flag();
        t.close();
    }
}
