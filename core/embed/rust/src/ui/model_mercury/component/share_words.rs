use super::theme;
use crate::{
    strutil::TString,
    time::{Duration, Instant},
    translations::TR,
    ui::{
        animation::Animation,
        component::{Component, Event, EventCtx, Never, SwipeDirection},
        flow::{Swipable, SwipableResult},
        geometry::{Alignment, Alignment2D, Insets, Offset, Rect},
        model_mercury::component::Footer,
        shape,
        shape::Renderer,
        util,
    },
};
use heapless::{String, Vec};

const MAX_WORDS: usize = 33; // super-shamir has 33 words, all other have less
const ANIMATION_DURATION_MS: Duration = Duration::from_millis(166);

/// Component showing mnemonic/share words during backup procedure. Model T3T1
/// contains one word per screen. A user is instructed to swipe up/down to see
/// next/previous word.
pub struct ShareWords<'a> {
    area: Rect,
    share_words: Vec<TString<'a>, MAX_WORDS>,
    page_index: usize,
    prev_index: usize,
    /// Area reserved for a shown word from mnemonic/share
    area_word: Rect,
    /// `Some` when transition animation is in progress
    animation: Option<Animation<f32>>,
    /// Footer component for instructions and word counting
    footer: Footer<'static>,
}

impl<'a> ShareWords<'a> {
    const AREA_WORD_HEIGHT: i16 = 91;

    pub fn new(share_words: Vec<TString<'a>, MAX_WORDS>) -> Self {
        Self {
            area: Rect::zero(),
            share_words,
            page_index: 0,
            prev_index: 0,
            area_word: Rect::zero(),
            animation: None,
            footer: Footer::new(TR::instructions__swipe_up),
        }
    }

    fn is_first_page(&self) -> bool {
        self.page_index == 0
    }

    fn is_final_page(&self) -> bool {
        self.page_index == self.share_words.len() - 1
    }

    fn render_word<'s>(&'s self, word_index: usize, target: &mut impl Renderer<'s>) {
        // the share word
        let word = self.share_words[word_index];
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

    fn event(&mut self, ctx: &mut EventCtx, _event: Event) -> Option<Self::Msg> {
        // ctx.set_page_count(self.share_words.len());
        if let Some(a) = &self.animation {
            if a.finished(Instant::now()) {
                self.animation = None;
            } else {
                ctx.request_anim_frame();
            }
            ctx.request_paint();
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
        let ordinal = build_string!(3, inttostr!(ordinal_val), ".");
        shape::Text::new(ordinal_pos, &ordinal)
            .with_font(theme::TEXT_SUB_GREY_LIGHT.text_font)
            .with_fg(theme::GREY)
            .render(target);

        if let Some(animation) = &self.animation {
            target.in_clip(self.area_word, &|target| {
                util::render_slide(
                    |target| self.render_word(self.prev_index, target),
                    |target| self.render_word(self.page_index, target),
                    animation.value(Instant::now()),
                    if self.prev_index < self.page_index {
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

impl<'a> Swipable<Never> for ShareWords<'a> {
    fn swipe_start(
        &mut self,
        ctx: &mut EventCtx,
        direction: SwipeDirection,
    ) -> SwipableResult<Never> {
        match direction {
            SwipeDirection::Up if !self.is_final_page() => {
                self.prev_index = self.page_index;
                self.page_index = (self.page_index + 1).min(self.share_words.len() - 1);
            }
            SwipeDirection::Down if !self.is_first_page() => {
                self.prev_index = self.page_index;
                self.page_index = self.page_index.saturating_sub(1);
            }
            _ => return SwipableResult::Ignored,
        };
        if util::animation_disabled() {
            ctx.request_paint();
            return SwipableResult::Animating;
        }
        self.animation = Some(Animation::new(
            0.0f32,
            1.0f32,
            ANIMATION_DURATION_MS,
            Instant::now(),
        ));
        ctx.request_anim_frame();
        ctx.request_paint();
        SwipableResult::Animating
    }

    fn swipe_finished(&self) -> bool {
        self.animation.is_none()
    }
}

#[cfg(feature = "ui_debug")]
impl<'a> crate::trace::Trace for ShareWords<'a> {
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.component("ShareWords");
        let word = &self.share_words[self.page_index];
        let content =
            word.map(|w| build_string!(50, inttostr!(self.page_index as u8 + 1), ". ", w, "\n"));
        t.string("screen_content", content.as_str().into());
    }
}
