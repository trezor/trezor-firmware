use crate::{
    strutil::TString,
    ui::{
        cache::PageCache,
        component::{
            text::{layout::LayoutFit, LineBreaking},
            Component, Event, EventCtx, Never, TextLayout,
        },
        geometry::Rect,
        shape::Renderer,
        util::Pager,
    },
};

use super::{constant::SCREEN, theme, ActionBar, ActionBarMsg, Header, Hint};

pub const CHARS_PER_PAGE: usize = 10;

pub enum LongContentScreenMsg {
    Confirmed,
    Cancelled,
}

pub struct LongContentScreen<'a> {
    header: Header,
    content: LongContent,
    hint: Hint<'a>,
    action_bar: ActionBar,
}

impl<'a> LongContentScreen<'a> {
    pub fn new(title: TString<'static>, text_length: u32) -> Self {
        let content = LongContent::new(text_length);
        let mut action_bar = ActionBar::new_cancel_confirm();
        action_bar.update(content.pager);

        let mut hint = Hint::new_page_counter();
        hint.update(content.pager);

        Self {
            header: Header::new(title),
            content,
            hint,
            action_bar,
        }
    }

    fn switch_next(&mut self, ctx: &mut EventCtx) {
        // The next button shoudn't be available at the last page
        debug_assert!(!self.content.pager.is_last());
        self.content.switch_next(ctx);
        let new_pager = self.content.pager();
        self.hint.update(new_pager);
        self.action_bar.update(new_pager);
    }

    fn switch_prev(&mut self, ctx: &mut EventCtx) {
        // The prev button shoudn't be available at the first page
        debug_assert!(!self.content.pager.is_first());
        self.content.switch_prev(ctx);
        let new_pager = self.content.pager();
        self.hint.update(new_pager);
        self.action_bar.update(new_pager);
    }
}

impl<'a> Component for LongContentScreen<'a> {
    type Msg = LongContentScreenMsg;
    fn place(&mut self, bounds: Rect) -> Rect {
        // assert full screen
        debug_assert_eq!(bounds.height(), SCREEN.height());
        debug_assert_eq!(bounds.width(), SCREEN.width());

        let (header_area, rest) = bounds.split_top(Header::HEADER_HEIGHT);
        let (rest, action_bar_area) = rest.split_bottom(ActionBar::ACTION_BAR_HEIGHT);
        let (content_area, hint_area) = rest.split_bottom(self.hint.height());

        self.header.place(header_area);
        self.content.place(content_area);
        self.hint.place(hint_area);
        self.action_bar.place(action_bar_area);

        bounds
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        self.content.event(ctx, event);

        if let Some(msg) = self.action_bar.event(ctx, event) {
            match msg {
                ActionBarMsg::Confirmed => return Some(LongContentScreenMsg::Confirmed),
                ActionBarMsg::Cancelled => return Some(LongContentScreenMsg::Cancelled),
                ActionBarMsg::Next => {
                    debug_assert!(!self.content.pager.is_last());
                    self.switch_next(ctx);
                    return None;
                }
                ActionBarMsg::Prev => {
                    debug_assert!(!self.content.pager.is_first());
                    self.switch_prev(ctx);
                    return None;
                }
            }
        };

        None
    }

    fn render<'s>(&'s self, target: &mut impl Renderer<'s>) {
        self.header.render(target);
        self.content.render(target);
        self.hint.render(target);
        self.action_bar.render(target);
    }
}

#[cfg(feature = "ui_debug")]
impl<'a> crate::trace::Trace for LongContentScreen<'a> {
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.component("LongContentScreen");
        t.child("Header", &self.header);
        t.child("Content", &self.content);
        t.child("Hint", &self.hint);
        t.child("ActionBar", &self.action_bar);
    }
}

struct LongContent {
    pager: Pager,
    content_length: u32,
    cache: PageCache<CHARS_PER_PAGE, { 4 * CHARS_PER_PAGE }>,
    area: Rect,
}

impl LongContent {
    fn new(content_length: u32) -> Self {
        let total_pages =
            ((content_length as u16) + CHARS_PER_PAGE as u16 - 1) / CHARS_PER_PAGE as u16;
        Self {
            pager: Pager::new(total_pages),
            content_length,
            cache: PageCache::<CHARS_PER_PAGE, { 4 * CHARS_PER_PAGE }>::new(total_pages),
            area: Rect::zero(),
        }
    }

    fn pager(&self) -> Pager {
        self.pager
    }

    fn switch_next(&mut self, ctx: &mut EventCtx) {
        debug_assert!(!self.pager.is_last());
        self.pager.goto_next();
        self.cache.switch_next(ctx);
    }

    fn switch_prev(&mut self, ctx: &mut EventCtx) {
        debug_assert!(!self.pager.is_first());
        self.pager.goto_prev();
        self.cache.switch_prev(ctx);
    }
}

impl Component for LongContent {
    type Msg = Never;

    fn place(&mut self, bounds: Rect) -> Rect {
        self.area = bounds;
        bounds
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        self.cache.event(ctx, event);

        None
    }

    fn render<'s>(&'s self, target: &mut impl Renderer<'s>) {
        let current_page = self.cache.current_page_data();

        current_page.map(|text| {
            let layout = TextLayout::new(
                theme::TEXT_MONO_MEDIUM.with_line_breaking(LineBreaking::BreakWordsNoHyphen),
            )
            .with_bounds(self.area);

            // must fit parameter doesn't have effect here
            debug_assert!(matches!(layout.fit_text(text), LayoutFit::Fitting { .. }));

            layout.render_text(text, target, true)
        });
    }
}

#[cfg(feature = "ui_debug")]
impl crate::trace::Trace for LongContent {
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.component("LongContent");
        t.int("content length", self.content_length as i64);
        t.int("current_page", self.pager.current() as i64);
        t.int("total_pages", self.pager.total() as i64);
    }
}
