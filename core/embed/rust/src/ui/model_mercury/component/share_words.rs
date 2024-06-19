use super::{theme, InternallySwipableContent};
use crate::{
    strutil::TString,
    time::Duration,
    translations::TR,
    ui::{
        animation::Animation,
        component::{
            swipe_detect::{SwipeConfig, SwipeSettings},
            Component, Event, EventCtx, Never, SwipeDirection,
        },
        event::SwipeEvent,
        geometry::{Alignment, Alignment2D, Insets, Offset, Rect},
        model_mercury::component::{Frame, FrameMsg, InternallySwipable},
        shape::{self, Renderer},
        util,
    },
};
use heapless::Vec;

const MAX_WORDS: usize = 33; // super-shamir has 33 words, all other have less
const ANIMATION_DURATION_MS: Duration = Duration::from_millis(166);
type IndexVec = Vec<u8, MAX_WORDS>;

/// Component showing mnemonic/share words during backup procedure. Model T3T1
/// contains one word per screen. A user is instructed to swipe up/down to see
/// next/previous word.
/// This is a wrapper around a Frame so that the subtitle and Footer of the
/// Frame can be updated based on the index of the word shown. Actual share
/// words are rendered within `ShareWordsInner` component,
pub struct ShareWords<'a> {
    subtitle: TString<'static>,
    frame: Frame<InternallySwipableContent<ShareWordsInner<'a>>>,
    repeated_indices: Option<IndexVec>,
}

impl<'a> ShareWords<'a> {
    pub fn new(
        title: TString<'static>,
        subtitle: TString<'static>,
        share_words: Vec<TString<'a>, MAX_WORDS>,
        highlight_repeated: bool,
    ) -> Self {
        let repeated_indices = if highlight_repeated {
            Some(Self::find_repeated(share_words.as_slice()))
        } else {
            None
        };
        let n_words = share_words.len();
        Self {
            subtitle,
            frame: Frame::left_aligned(
                title,
                InternallySwipableContent::new(ShareWordsInner::new(share_words)),
            )
            .with_swipe(SwipeDirection::Up, SwipeSettings::default())
            .with_swipe(SwipeDirection::Down, SwipeSettings::default())
            .with_vertical_pages()
            .with_subtitle(subtitle)
            .with_footer_counter(TR::instructions__swipe_up.into(), n_words as u8),
            repeated_indices,
        }
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
}

impl<'a> Component for ShareWords<'a> {
    type Msg = FrameMsg<Never>;

    fn place(&mut self, bounds: Rect) -> Rect {
        self.frame.place(bounds);
        bounds
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        let page_index = self.frame.inner().inner().page_index as u8;
        if let Some(repeated_indices) = &self.repeated_indices {
            if repeated_indices.contains(&page_index) {
                let updated_subtitle = TString::from_translation(TR::reset__the_word_is_repeated);
                self.frame
                    .update_subtitle(ctx, updated_subtitle, Some(theme::TEXT_SUB_GREEN_LIME));
            } else {
                self.frame
                    .update_subtitle(ctx, self.subtitle, Some(theme::TEXT_SUB_GREY));
            }
        }
        self.frame.update_footer_counter(ctx, page_index + 1);
        self.frame.event(ctx, event)
    }

    fn paint(&mut self) {
        // TODO: remove when ui-t3t1 done
    }

    fn render<'s>(&'s self, target: &mut impl Renderer<'s>) {
        self.frame.render(target);
    }

    #[cfg(feature = "ui_bounds")]
    fn bounds(&self, _sink: &mut dyn FnMut(Rect)) {}
}

#[cfg(feature = "micropython")]
impl<'a> crate::ui::flow::Swipable for ShareWords<'a> {
    fn get_swipe_config(&self) -> SwipeConfig {
        self.frame.get_swipe_config()
    }

    fn get_internal_page_count(&self) -> usize {
        self.frame.get_internal_page_count()
    }
}

#[cfg(feature = "ui_debug")]
impl<'a> crate::trace::Trace for ShareWords<'a> {
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.component("ShareWords");
        t.child("inner", &self.frame);
    }
}

struct ShareWordsInner<'a> {
    share_words: Vec<TString<'a>, MAX_WORDS>,
    page_index: i16,
    next_index: i16,
    /// Area reserved for a shown word from mnemonic/share
    area_word: Rect,
    /// `Some` when transition animation is in progress
    animation: Option<Animation<f32>>,
    progress: i16,
}

impl<'a> ShareWordsInner<'a> {
    const AREA_WORD_HEIGHT: i16 = 91;

    fn new(share_words: Vec<TString<'a>, MAX_WORDS>) -> Self {
        Self {
            share_words,
            page_index: 0,
            next_index: 0,
            area_word: Rect::zero(),
            animation: None,
            progress: 0,
        }
    }

    fn is_first_page(&self) -> bool {
        self.page_index == 0
    }

    fn is_final_page(&self) -> bool {
        self.page_index == self.share_words.len() as i16 - 1
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
}

impl<'a> Component for ShareWordsInner<'a> {
    type Msg = Never;

    fn place(&mut self, bounds: Rect) -> Rect {
        let used_area = bounds
            .inset(Insets::sides(theme::SPACING))
            .inset(Insets::bottom(theme::SPACING));

        self.area_word = Rect::snap(
            used_area.center(),
            Offset::new(used_area.width(), ShareWordsInner::AREA_WORD_HEIGHT),
            Alignment2D::CENTER,
        );

        bounds
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        ctx.set_page_count(self.share_words.len());

        match event {
            Event::Attach(_) => {
                self.progress = 0;
            }
            Event::Swipe(SwipeEvent::End(dir)) => match dir {
                SwipeDirection::Up if !self.is_final_page() => {
                    self.progress = 0;
                    self.page_index = (self.page_index + 1).min(self.share_words.len() as i16 - 1);
                    ctx.request_paint();
                }
                SwipeDirection::Down if !self.is_first_page() => {
                    self.progress = 0;
                    self.page_index = self.page_index.saturating_sub(1);
                    ctx.request_paint();
                }
                _ => {}
            },
            Event::Swipe(SwipeEvent::Move(dir, progress)) => {
                match dir {
                    SwipeDirection::Up => {
                        self.next_index = self.page_index + 1;
                        self.progress = progress;
                    }
                    SwipeDirection::Down => {
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

    fn paint(&mut self) {
        // TODO: remove when ui-t3t1 done
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

        let (dir, should_animate) = if self.page_index < self.next_index {
            (
                SwipeDirection::Up,
                self.page_index < self.share_words.len() as i16 - 1,
            )
        } else {
            (SwipeDirection::Down, self.page_index > 0)
        };

        if self.progress > 0 && should_animate {
            target.in_clip(self.area_word, &|target| {
                let progress = pareen::constant(0.0).seq_ease_out(
                    0.0,
                    easer::functions::Cubic,
                    1.0,
                    pareen::constant(1.0),
                );

                util::render_slide(
                    |target| self.render_word(self.page_index, target, target.viewport().clip),
                    |target| self.render_word(self.next_index, target, target.viewport().clip),
                    progress.eval(self.progress as f32 / 1000.0),
                    dir,
                    target,
                )
            });
        } else {
            self.render_word(self.page_index, target, self.area_word);
        };
    }

    #[cfg(feature = "ui_bounds")]
    fn bounds(&self, _sink: &mut dyn FnMut(Rect)) {}
}

impl InternallySwipable for ShareWordsInner<'_> {
    fn current_page(&self) -> usize {
        self.page_index as usize
    }

    fn num_pages(&self) -> usize {
        self.share_words.len()
    }
}

#[cfg(feature = "ui_debug")]
impl<'a> crate::trace::Trace for ShareWordsInner<'a> {
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
