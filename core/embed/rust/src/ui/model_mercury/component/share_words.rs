use super::theme;
use crate::{
    strutil::TString,
    time::Duration,
    translations::TR,
    ui::{
        animation::Animation,
        component::{Component, Event, EventCtx, Never, SwipeDirection},
        event::SwipeEvent,
        geometry::{Alignment, Alignment2D, Insets, Offset, Rect},
        model_mercury::component::Footer,
        shape::{self, Renderer},
        util,
    },
};
use heapless::Vec;

const MAX_WORDS: usize = 33; // super-shamir has 33 words, all other have less
const ANIMATION_DURATION_MS: Duration = Duration::from_millis(166);

/// Component showing mnemonic/share words during backup procedure. Model T3T1
/// contains one word per screen. A user is instructed to swipe up/down to see
/// next/previous word.
pub struct ShareWords<'a> {
    area: Rect,
    share_words: Vec<TString<'a>, MAX_WORDS>,
    page_index: i16,
    next_index: i16,
    /// Area reserved for a shown word from mnemonic/share
    area_word: Rect,
    /// `Some` when transition animation is in progress
    animation: Option<Animation<f32>>,
    /// Footer component for instructions and word counting
    footer: Footer<'static>,
    progress: i16,
}

impl<'a> ShareWords<'a> {
    const AREA_WORD_HEIGHT: i16 = 91;

    pub fn new(share_words: Vec<TString<'a>, MAX_WORDS>) -> Self {
        Self {
            area: Rect::zero(),
            share_words,
            page_index: 0,
            next_index: 0,
            area_word: Rect::zero(),
            animation: None,
            footer: Footer::new(TR::instructions__swipe_up),
            progress: 0,
        }
    }

    fn is_first_page(&self) -> bool {
        self.page_index == 0
    }

    fn is_final_page(&self) -> bool {
        self.page_index == self.share_words.len() as i16 - 1
    }

    fn render_word<'s>(&self, word_index: i16, target: &mut impl Renderer<'s>) {
        // the share word
        if word_index >= self.share_words.len() as _ || word_index < 0 {
            return;
        }
        let word = self.share_words[word_index as usize];
        let word_baseline = target.viewport().clip.center()
            + Offset::y(theme::TEXT_SUPER.text_font.visible_text_height("A") / 2);
        word.map(|w| {
            shape::Text::new(word_baseline, w)
                .with_font(theme::TEXT_SUPER.text_font)
                .with_align(Alignment::Center)
                .render(target);
        });
    }
}

impl<'a> Component for ShareWords<'a> {
    type Msg = Never;

    fn place(&mut self, bounds: Rect) -> Rect {
        self.area = bounds;
        let used_area = bounds
            .inset(Insets::sides(theme::SPACING))
            .inset(Insets::bottom(theme::SPACING));

        self.area_word = Rect::snap(
            used_area.center(),
            Offset::new(used_area.width(), ShareWords::AREA_WORD_HEIGHT),
            Alignment2D::CENTER,
        );

        self.footer
            .place(used_area.split_bottom(Footer::HEIGHT_SIMPLE).1);

        self.area
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

        if self.progress > 0 {
            target.in_clip(self.area_word, &|target| {
                let progress = pareen::constant(0.0).seq_ease_out(
                    0.0,
                    easer::functions::Cubic,
                    1.0,
                    pareen::constant(1.0),
                );

                util::render_slide(
                    |target| self.render_word(self.page_index, target),
                    |target| self.render_word(self.next_index, target),
                    progress.eval(self.progress as f32 / 1000.0),
                    if self.page_index < self.next_index {
                        SwipeDirection::Up
                    } else {
                        SwipeDirection::Down
                    },
                    target,
                )
            });
        } else {
            target.in_clip(self.area_word, &|target| {
                self.render_word(self.page_index, target);
            })
        };

        // footer with instructions
        self.footer.render(target);
    }

    #[cfg(feature = "ui_bounds")]
    fn bounds(&self, _sink: &mut dyn FnMut(Rect)) {}
}

#[cfg(feature = "ui_debug")]
impl<'a> crate::trace::Trace for ShareWords<'a> {
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.component("ShareWords");
        let word = &self.share_words[self.page_index as usize];
        let content = word.map(|w| uformat!("{}. {}\n", self.page_index + 1, w));
        t.string("screen_content", content.as_str().into());
        t.int("page_count", self.share_words.len() as i64)
    }
}
