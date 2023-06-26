use crate::{
    strutil::StringType,
    ui::{
        component::{
            text::util::text_multiline, Child, Component, Event, EventCtx, Never, Paginate,
        },
        display::Font,
        geometry::{Alignment, Offset, Rect},
    },
};

use heapless::{String, Vec};

use super::{common::display_left, scrollbar::SCROLLBAR_SPACE, theme, ScrollBar};

const WORDS_PER_PAGE: usize = 3;
const EXTRA_LINE_HEIGHT: i16 = 2;
const NUMBER_X_OFFSET: i16 = 0;
const WORD_X_OFFSET: i16 = 25;
const NUMBER_FONT: Font = Font::DEMIBOLD;
const WORD_FONT: Font = Font::BIG;
const INFO_TOP_OFFSET: i16 = 20;
const MAX_WORDS: usize = 33; // super-shamir has 33 words, all other have less

/// Showing the given share words.
pub struct ShareWords<T>
where
    T: StringType,
{
    area: Rect,
    scrollbar: Child<ScrollBar>,
    share_words: Vec<T, MAX_WORDS>,
    page_index: usize,
}

impl<T> ShareWords<T>
where
    T: StringType + Clone,
{
    pub fn new(share_words: Vec<T, MAX_WORDS>) -> Self {
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

    fn get_final_text(&self) -> String<50> {
        build_string!(
            50,
            "I wrote down all ",
            inttostr!(self.share_words.len() as u8),
            " words in order."
        )
    }

    /// Display the final page with user confirmation.
    fn paint_final_page(&mut self) {
        text_multiline(
            self.area.split_top(INFO_TOP_OFFSET).1,
            &self.get_final_text(),
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
            let word = &self.share_words[index];
            let baseline = self.area.top_left() + Offset::y(y_offset);
            let ordinal = build_string!(5, inttostr!(index as u8 + 1), ".");
            display_left(baseline + Offset::x(NUMBER_X_OFFSET), &ordinal, NUMBER_FONT);
            display_left(baseline + Offset::x(WORD_X_OFFSET), &word, WORD_FONT);
        }
    }
}

impl<T> Component for ShareWords<T>
where
    T: StringType + Clone,
{
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
}

impl<T> Paginate for ShareWords<T>
where
    T: StringType + Clone,
{
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
impl<T> crate::trace::Trace for ShareWords<T>
where
    T: StringType + Clone,
{
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.component("ShareWords");
        let content = if self.is_final_page() {
            self.get_final_text()
        } else {
            let mut content = String::<50>::new();
            for i in 0..WORDS_PER_PAGE {
                let index = self.word_index() + i;
                if index >= self.share_words.len() {
                    break;
                }
                let word = &self.share_words[index];
                let current_line =
                    build_string!(50, inttostr!(index as u8 + 1), ". ", word.as_ref(), "\n");
                unwrap!(content.push_str(&current_line));
            }
            content
        };
        t.string("screen_content", &content);
    }
}
