use crate::{
    micropython::buffer::StrBuffer,
    ui::{
        component::{Component, Event, EventCtx, Never, Paginate},
        display::{text_multiline, Font},
        geometry::{Offset, Rect},
        model_tr::theme,
    },
};

use crate::ui::{
    component::Child,
    model_tr::component::{scrollbar::SCROLLBAR_SPACE, title::Title, ScrollBar},
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
    title: Child<Title>,
    scrollbar: Child<ScrollBar>,
    share_words: Vec<StrBuffer, N>,
    page_index: usize,
}

impl<const N: usize> ShareWords<N> {
    pub fn new(title: StrBuffer, share_words: Vec<StrBuffer, N>) -> Self {
        let mut instance = Self {
            area: Rect::zero(),
            title: Child::new(Title::new(title)),
            scrollbar: Child::new(ScrollBar::to_be_filled_later()),
            share_words,
            page_index: 0,
        };
        let page_count = instance.total_page_count();
        instance.scrollbar.inner_mut().set_page_count(page_count);
        instance
    }

    fn word_index(&self) -> usize {
        (self.page_index - 2) * WORDS_PER_PAGE
    }

    fn is_entry_page(&self) -> bool {
        self.page_index == 0
    }

    fn is_second_page(&self) -> bool {
        self.page_index == 1
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
        // Two pages before the words, one after it
        2 + word_screens + 1
    }

    fn get_first_text(&self) -> String<50> {
        build_string!(
            50,
            "Write all ",
            inttostr!(self.share_words.len() as u8),
            "\nwords in order on\nrecovery seed card."
        )
    }

    /// Display the first page with user information.
    fn paint_entry_page(&mut self) {
        text_multiline(
            self.area.split_top(15).1,
            &self.get_first_text(),
            Font::BOLD,
            theme::FG,
            theme::BG,
        );
    }

    fn get_second_text(&self) -> String<50> {
        build_string!(50, "Do NOT make\ndigital copies!")
    }

    /// Display the second page with user information.
    fn paint_second_page(&mut self) {
        text_multiline(
            self.area.split_top(15).1,
            &self.get_second_text(),
            Font::MONO,
            theme::FG,
            theme::BG,
        );
    }

    fn get_final_text(&self) -> String<50> {
        build_string!(
            50,
            "I wrote down all\n",
            inttostr!(self.share_words.len() as u8),
            " words in order."
        )
    }

    /// Display the final page with user confirmation.
    fn paint_final_page(&mut self) {
        text_multiline(
            self.area.split_top(12).1,
            &self.get_final_text(),
            Font::MONO,
            theme::FG,
            theme::BG,
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
            let word = self.share_words[index];
            let baseline = self.area.top_left() + Offset::new(NUMBER_X_OFFSET, y_offset);
            display(baseline, &inttostr!(index as u8 + 1), NUMBER_FONT);
            display(baseline + Offset::x(NUMBER_WORD_OFFSET), &word, WORD_FONT);
        }
    }
}

impl<const N: usize> Component for ShareWords<N> {
    type Msg = Never;

    fn place(&mut self, bounds: Rect) -> Rect {
        let (title_area, _) = bounds.split_top(theme::FONT_HEADER.line_height());

        let (title_area, scrollbar_area) =
            title_area.split_right(self.scrollbar.inner().overall_width() + SCROLLBAR_SPACE);

        self.title.place(title_area);
        self.scrollbar.place(scrollbar_area);

        self.area = bounds;
        self.area
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        self.title.event(ctx, event);
        self.scrollbar.event(ctx, event);
        None
    }

    fn paint(&mut self) {
        // Showing scrollbar in all cases
        // Individual pages are responsible for not colliding with it
        self.scrollbar.paint();
        if self.is_entry_page() {
            self.title.paint();
            self.paint_entry_page();
        } else if self.is_second_page() {
            self.paint_second_page();
        } else if self.is_final_page() {
            self.paint_final_page();
        } else {
            self.paint_words();
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
        self.scrollbar.inner_mut().set_active_page(active_page);
    }
}

// DEBUG-ONLY SECTION BELOW

#[cfg(feature = "ui_debug")]
impl<const N: usize> crate::trace::Trace for ShareWords<N> {
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.open("ShareWords");
        t.content_flag();
        if self.is_entry_page() {
            let content = build_string!(
                70,
                self.title.inner().get_text(),
                "\n",
                &self.get_first_text()
            );
            t.string(&content);
        } else if self.is_second_page() {
            t.string(&self.get_second_text());
        } else if self.is_final_page() {
            t.string(&self.get_final_text());
        } else {
            for i in 0..WORDS_PER_PAGE {
                let index = self.word_index() + i;
                if index >= self.share_words.len() {
                    break;
                }
                let word = self.share_words[index];
                let content = build_string!(20, inttostr!(index as u8 + 1), " ", &word, "\n");
                t.string(&content);
            }
        }
        t.content_flag();
        t.close();
    }
}
