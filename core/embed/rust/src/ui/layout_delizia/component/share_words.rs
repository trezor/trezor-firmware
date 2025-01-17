use crate::{
    strutil::TString,
    translations::TR,
    ui::{
        component::{base::AttachType, text::TextStyle, Component, Event, EventCtx, Never},
        event::SwipeEvent,
        geometry::{Alignment, Alignment2D, Direction, Insets, Offset, Rect},
        shape::{self, Renderer},
    },
};

use heapless::Vec;

use super::{
    super::component::{swipe_content::SwipeAttachAnimation, InternallySwipable},
    theme,
};

const MAX_WORDS: usize = 33; // super-shamir has 33 words, all other have less

type IndexVec = Vec<u8, MAX_WORDS>;

/// Component showing mnemonic/share words during backup procedure. Model T3T1
/// contains one word per screen. A user is instructed to swipe up/down to see
/// next/previous word.
pub struct ShareWords<'a> {
    share_words: Vec<TString<'a>, MAX_WORDS>,
    subtitle: TString<'static>,
    page_index: i16,
    next_index: i16,
    /// Area reserved for a shown word from mnemonic/share
    area_word: Rect,
    progress: i16,
    attach_animation: SwipeAttachAnimation,
    wait_for_attach: bool,
    repeated_indices: IndexVec,
}

impl<'a> ShareWords<'a> {
    const AREA_WORD_HEIGHT: i16 = 91;

    pub fn new(share_words: Vec<TString<'a>, MAX_WORDS>, subtitle: TString<'static>) -> Self {
        let repeated_indices = Self::find_repeated(share_words.as_slice());
        Self {
            share_words,
            subtitle,
            page_index: 0,
            next_index: 0,
            area_word: Rect::zero(),
            progress: 0,
            attach_animation: SwipeAttachAnimation::new(),
            wait_for_attach: false,
            repeated_indices,
        }
    }

    fn is_first_page(&self) -> bool {
        self.page_index == 0
    }

    fn is_final_page(&self) -> bool {
        self.page_index == self.share_words.len() as i16 - 1
    }

    fn find_repeated(share_words: &[TString]) -> IndexVec {
        let mut repeated_indices = IndexVec::new();
        for i in (0..share_words.len()).rev() {
            let word = share_words[i];
            if share_words[..i].contains(&word) {
                unwrap!(repeated_indices.push(i as u8));
            }
        }
        repeated_indices.reverse();
        repeated_indices
    }

    pub fn subtitle(&self) -> (TString<'static>, &'static TextStyle) {
        if self.repeated_indices.contains(&(self.page_index as u8)) {
            return (
                TString::from_translation(TR::reset__the_word_is_repeated),
                &theme::TEXT_SUB_GREEN_LIME,
            );
        }

        (self.subtitle, &theme::TEXT_SUB_GREY)
    }

    fn render_word<'s>(&self, word_index: i16, target: &mut impl Renderer<'s>, area: Rect) {
        // the share word
        if word_index >= self.share_words.len() as _ || word_index < 0 {
            return;
        }
        let word = self.share_words[word_index as usize];
        let word_baseline =
            area.center() + Offset::y(theme::TEXT_SUPER.text_font.visible_text_height("A") / 2);
        word.map(|w| {
            shape::Text::new(word_baseline, w)
                .with_font(theme::TEXT_SUPER.text_font)
                .with_align(Alignment::Center)
                .render(target);
        });
    }

    fn should_animate_progress(&self) -> (Direction, bool) {
        let (dir, should_animate) = if self.page_index < self.next_index {
            (Direction::Up, !self.is_final_page())
        } else {
            (Direction::Down, !self.is_first_page())
        };
        (dir, should_animate)
    }

    fn should_animate_attach(&self, event: Event) -> (Direction, bool) {
        match event {
            Event::Attach(AttachType::Swipe(Direction::Up)) => {
                (Direction::Up, !self.is_first_page())
            }
            Event::Attach(AttachType::Swipe(Direction::Down)) => {
                (Direction::Down, !self.is_final_page())
            }
            _ => (Direction::Up, false),
        }
    }
}

impl<'a> Component for ShareWords<'a> {
    type Msg = Never;

    fn place(&mut self, bounds: Rect) -> Rect {
        let used_area = bounds
            .inset(Insets::sides(theme::SPACING))
            .inset(Insets::bottom(theme::SPACING));

        self.area_word = Rect::snap(
            used_area.center(),
            Offset::new(used_area.width(), ShareWords::AREA_WORD_HEIGHT),
            Alignment2D::CENTER,
        );

        bounds
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        ctx.set_page_count(self.share_words.len());

        let (_, should_animate) = self.should_animate_attach(event);

        self.attach_animation.lazy_start(ctx, event, should_animate);

        match event {
            Event::Attach(_) => {
                self.progress = 0;

                if !should_animate {
                    self.wait_for_attach = false;
                }
            }
            Event::Swipe(SwipeEvent::End(dir)) => match dir {
                Direction::Up if !self.is_final_page() => {
                    self.progress = 0;
                    self.page_index = (self.page_index + 1).min(self.share_words.len() as i16 - 1);
                    self.wait_for_attach = true;
                    ctx.request_paint();
                }
                Direction::Down if !self.is_first_page() => {
                    self.progress = 0;
                    self.page_index = self.page_index.saturating_sub(1);
                    self.wait_for_attach = true;
                    ctx.request_paint();
                }
                _ => {}
            },
            Event::Swipe(SwipeEvent::Move(dir, progress)) => {
                match dir {
                    Direction::Up => {
                        self.next_index = self.page_index + 1;
                        self.progress = progress;
                    }
                    Direction::Down => {
                        self.next_index = self.page_index - 1;
                        self.progress = progress;
                    }
                    _ => {}
                }
                ctx.request_paint();
            }
            _ => {}
        }

        None
    }

    fn render<'s>(&'s self, target: &mut impl Renderer<'s>) {
        // corner highlights
        let (_, top_right_shape, bot_left_shape, bot_right_shape) =
            shape::CornerHighlight::from_rect(self.area_word, theme::GREY_DARK, theme::BG);
        top_right_shape.render(target);
        bot_left_shape.render(target);
        bot_right_shape.render(target);

        // the ordinal number of the current word
        let ordinal_val = self.page_index as u8 + 1;
        let ordinal_pos = self.area_word.top_left()
            + Offset::y(
                theme::TEXT_SUB_GREY_LIGHT
                    .text_font
                    .visible_text_height("1"),
            );
        let ordinal = uformat!("{}.", ordinal_val);
        shape::Text::new(ordinal_pos, &ordinal)
            .with_font(theme::TEXT_SUB_GREY_LIGHT.text_font)
            .with_fg(theme::GREY)
            .render(target);

        let (dir, should_animate_progress) = self.should_animate_progress();

        if self.progress > 0 && should_animate_progress {
            target.in_clip(self.area_word, &|target| {
                let bounds = target.viewport().clip;
                let full_offset = dir.as_offset(bounds.size());
                let current_offset = full_offset * (self.progress as f32 / 1000.0);

                target.with_origin(current_offset, &|target| {
                    self.render_word(self.page_index, target, target.viewport().clip)
                });
            });
        } else if (self.attach_animation.is_active() || self.wait_for_attach) && self.progress == 0
        {
            let t = self.attach_animation.eval();

            let offset = self
                .attach_animation
                .get_offset(t, ShareWords::AREA_WORD_HEIGHT);

            target.in_clip(self.area_word, &|target| {
                target.with_origin(offset, &|target| {
                    self.render_word(self.page_index, target, target.viewport().clip)
                });
            });
        } else {
            self.render_word(self.page_index, target, self.area_word);
        }
    }
}

impl InternallySwipable for ShareWords<'_> {
    fn current_page(&self) -> usize {
        self.page_index as usize
    }

    fn num_pages(&self) -> usize {
        self.share_words.len()
    }
}

#[cfg(feature = "ui_debug")]
impl<'a> crate::trace::Trace for ShareWords<'a> {
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.component("ShareWordsInner");
        let word = &self.share_words[self.page_index as usize];
        let content = word.map(|w| uformat!("{}. {}\n", self.page_index + 1, w));
        t.string("screen_content", content.as_str().into());
        t.int("page_count", self.share_words.len() as i64)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_find_repeated_indices() {
        let words0 = [];
        let words1 = [
            TString::from_str("aaa"),
            TString::from_str("bbb"),
            TString::from_str("ccc"),
        ];
        let words2 = [
            TString::from_str("aaa"),
            TString::from_str("aaa"),
            TString::from_str("bbb"),
        ];
        let words3 = [
            TString::from_str("aaa"),
            TString::from_str("aaa"),
            TString::from_str("bbb"),
            TString::from_str("bbb"),
            TString::from_str("aaa"),
        ];
        let words4 = [
            TString::from_str("aaa"),
            TString::from_str("aaa"),
            TString::from_str("aaa"),
            TString::from_str("aaa"),
            TString::from_str("aaa"),
        ];

        assert_eq!(ShareWords::find_repeated(&words0), IndexVec::new());
        assert_eq!(ShareWords::find_repeated(&words1), IndexVec::new());
        assert_eq!(
            ShareWords::find_repeated(&words2),
            IndexVec::from_slice(&[1]).unwrap()
        );
        assert_eq!(
            ShareWords::find_repeated(&words3),
            IndexVec::from_slice(&[1, 3, 4]).unwrap()
        );
        assert_eq!(
            ShareWords::find_repeated(&words4),
            IndexVec::from_slice(&[1, 2, 3, 4]).unwrap()
        );
    }
}
