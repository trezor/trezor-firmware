use super::theme;
use crate::{
    strutil::TString,
    translations::TR,
    ui::{
        component::{Component, Event, EventCtx, PageMsg, Paginate},
        constant::SPACING,
        geometry::{Alignment, Alignment2D, Insets, Offset, Rect},
        model_mercury::component::{Footer, Swipe, SwipeDirection},
        shape,
        shape::Renderer,
    },
};
use heapless::{String, Vec};

const MAX_WORDS: usize = 33; // super-shamir has 33 words, all other have less

/// Component showing mnemonic/share words during backup procedure. Model T3T1
/// contains one word per screen. A user is instructed to swipe up/down to see
/// next/previous word.
pub struct ShareWords<'a> {
    area: Rect,
    share_words: Vec<TString<'a>, MAX_WORDS>,
    page_index: usize,
    /// Area reserved for a shown word from mnemonic/share
    area_word: Rect,
    /// TODO: review when swipe concept done for T3T1
    swipe: Swipe,
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
            area_word: Rect::zero(),
            swipe: Swipe::new().up().down(),
            footer: Footer::new(TR::instructions__swipe_up),
        }
    }

    fn is_final_page(&self) -> bool {
        self.page_index == self.share_words.len() - 1
    }
}

impl<'a> Component for ShareWords<'a> {
    type Msg = PageMsg<()>;

    fn place(&mut self, bounds: Rect) -> Rect {
        self.area = bounds;
        let used_area = bounds
            .inset(Insets::sides(SPACING))
            .inset(Insets::bottom(SPACING));

        self.area_word = Rect::snap(
            used_area.center(),
            Offset::new(used_area.width(), ShareWords::AREA_WORD_HEIGHT),
            Alignment2D::CENTER,
        );

        self.footer
            .place(used_area.split_bottom(Footer::HEIGHT_SIMPLE).1);

        self.swipe.place(bounds); // Swipe possible on the whole screen area
        self.area
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        ctx.set_page_count(self.share_words.len());
        let swipe = self.swipe.event(ctx, event);
        match swipe {
            Some(SwipeDirection::Up) => {
                if self.is_final_page() {
                    return Some(PageMsg::Confirmed);
                }
                self.change_page(self.page_index + 1);
                ctx.request_paint();
            }
            Some(SwipeDirection::Down) => {
                self.change_page(self.page_index.saturating_sub(1));
                ctx.request_paint();
            }
            _ => (),
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

        // the share word
        let word = self.share_words[self.page_index];
        let word_baseline = self.area_word.center()
            + Offset::y(theme::TEXT_SUPER.text_font.visible_text_height("A") / 2);
        word.map(|w| {
            shape::Text::new(word_baseline, w)
                .with_font(theme::TEXT_SUPER.text_font)
                .with_align(Alignment::Center)
                .render(target);
        });

        // footer with instructions
        self.footer.render(target);
    }

    #[cfg(feature = "ui_bounds")]
    fn bounds(&self, _sink: &mut dyn FnMut(Rect)) {}
}

impl<'a> Paginate for ShareWords<'a> {
    fn page_count(&mut self) -> usize {
        self.share_words.len()
    }

    fn change_page(&mut self, active_page: usize) {
        self.page_index = active_page;
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
