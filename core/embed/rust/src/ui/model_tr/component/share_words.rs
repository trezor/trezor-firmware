use crate::{
    micropython::buffer::StrBuffer,
    ui::{
        component::{Component, Event, EventCtx, Never, Paginate},
        display::Font,
        geometry::{Offset, Rect},
    },
};

use heapless::{String, Vec};

use super::common::display_inverse;

const WORDS_PER_PAGE: usize = 3;
const EXTRA_LINE_HEIGHT: i16 = 3;
const NUMBER_X_OFFSET: i16 = 5;
const NUMBER_WORD_OFFSET: i16 = 20;
const NUMBER_FONT: Font = Font::DEMIBOLD;
const WORD_FONT: Font = Font::NORMAL;

/// Showing the given share words.
///
/// Displays them in inverse colors - black text on white background.
/// It is that because of the OLED side attack - lot of white noise makes
/// the attack much harder.
pub struct ShareWords<const N: usize> {
    area: Rect,
    share_words: Vec<StrBuffer, N>,
    word_index: usize,
}

impl<const N: usize> ShareWords<N> {
    pub fn new(share_words: Vec<StrBuffer, N>) -> Self {
        Self {
            area: Rect::zero(),
            share_words,
            word_index: 0,
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
        let mut y_offset = 0;
        // Showing the word index and the words itself
        for i in 0..WORDS_PER_PAGE {
            y_offset += NUMBER_FONT.line_height() + EXTRA_LINE_HEIGHT;
            let index = self.word_index + i;
            let word = self.share_words[index].clone();
            let baseline = self.area.top_left() + Offset::new(NUMBER_X_OFFSET, y_offset);
            display_inverse(baseline, &inttostr!(index as u8 + 1), NUMBER_FONT);
            display_inverse(baseline + Offset::x(NUMBER_WORD_OFFSET), &word, WORD_FONT);
        }
    }
}

impl<const N: usize> Paginate for ShareWords<N> {
    fn page_count(&mut self) -> usize {
        if self.share_words.len() % WORDS_PER_PAGE == 0 {
            self.share_words.len() / WORDS_PER_PAGE
        } else {
            self.share_words.len() / WORDS_PER_PAGE + 1
        }
    }

    fn change_page(&mut self, active_page: usize) {
        self.word_index = active_page * WORDS_PER_PAGE;
    }
}

#[cfg(feature = "ui_debug")]
impl<const N: usize> crate::trace::Trace for ShareWords<N> {
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.open("ShareWords");
        t.content_flag();
        for i in 0..WORDS_PER_PAGE {
            let index = self.word_index + i;
            let word = self.share_words[index].clone();
            let content = build_string!(20, inttostr!(index as u8 + 1), " ", &word, "\n");
            t.string(&content);
        }
        t.content_flag();
        t.close();
    }
}
