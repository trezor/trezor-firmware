use super::theme::{self, TITLE_HEIGHT};
use super::{ActionBar, ActionBarMsg, Header};
use crate::strutil::TString;
use crate::ui::component::text::paragraphs::{ParagraphSource, Paragraphs};
use crate::ui::component::{Component, Event, EventCtx, FlowMsg, Paginate};
use crate::ui::geometry::{Insets, Rect};
use crate::ui::shape::Renderer;
use crate::ui::util::Pager;

/// Full-screen component showing paragraphs of text with a close button in
/// the header. When the text does not fit on a single page, an action bar
/// with up/down buttons is shown to paginate through it (similar to the
/// paginate-only action bar in Eckhart's `TextScreen`).
pub struct MoreInfoScreen<T>
where
    T: ParagraphSource<'static>,
{
    header: Header,
    paragraphs: Paragraphs<T>,
    action_bar: ActionBar,
    /// Whether the content needs the action bar for pagination. Decided on
    /// the first `place()` pass and kept stable afterwards, so that
    /// re-placing after a page change does not move the content around.
    paginated: Option<bool>,
}

impl<T> MoreInfoScreen<T>
where
    T: ParagraphSource<'static>,
{
    pub fn new(title: TString<'static>, paragraphs: Paragraphs<T>) -> Self {
        Self {
            header: Header::left_aligned(title).with_cancel_button(),
            paragraphs,
            action_bar: ActionBar::new_paginate_only(),
            paginated: None,
        }
    }

    fn update_page(&mut self, ctx: &mut EventCtx, page: u16) {
        self.change_page(page);
        self.action_bar.update(ctx, self.pager());
        ctx.request_paint();
    }
}

impl<T> Component for MoreInfoScreen<T>
where
    T: ParagraphSource<'static>,
{
    type Msg = FlowMsg;

    fn place(&mut self, bounds: Rect) -> Rect {
        let header_height = self.header.place(bounds).height().max(TITLE_HEIGHT);
        let rest = bounds.inset(Insets::top(header_height + theme::SPACING));

        let paginated = if let Some(paginated) = self.paginated {
            paginated
        } else {
            // First pass without the action bar to find out whether the
            // content paginates at all.
            self.paragraphs.place(rest);
            let paginated = self.paragraphs.pager().total() > 1;
            self.paginated = Some(paginated);
            paginated
        };

        let content_area = if paginated {
            let (content_area, bar_area) =
                rest.split_bottom(ActionBar::ACTION_BAR_HEIGHT + theme::SPACING);
            let (bar_area, _) = bar_area.split_top(ActionBar::ACTION_BAR_HEIGHT);
            self.action_bar.place(bar_area);
            content_area
        } else {
            rest
        };
        self.paragraphs.place(content_area);

        bounds
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        // Update page count of the screen
        ctx.set_page_count(self.pager().total());

        if let Some(msg @ FlowMsg::Cancelled) = self.header.event(ctx, event) {
            return Some(msg);
        }

        if self.paginated == Some(true) {
            match self.action_bar.event(ctx, event) {
                Some(ActionBarMsg::Prev) => {
                    let page = self.pager().prev();
                    self.update_page(ctx, page);
                    return None;
                }
                Some(ActionBarMsg::Next) => {
                    let page = self.pager().next();
                    self.update_page(ctx, page);
                    return None;
                }
                None => {}
            }
        }

        self.paragraphs.event(ctx, event);
        None
    }

    fn render<'s>(&'s self, target: &mut impl Renderer<'s>) {
        self.header.render(target);
        self.paragraphs.render(target);
        if self.paginated == Some(true) {
            self.action_bar.render(target);
        }
    }
}

impl<T> Paginate for MoreInfoScreen<T>
where
    T: ParagraphSource<'static>,
{
    fn pager(&self) -> Pager {
        self.paragraphs.pager()
    }

    fn change_page(&mut self, active_page: u16) {
        self.paragraphs.change_page(active_page);
    }
}

#[cfg(feature = "ui_debug")]
impl<T> crate::trace::Trace for MoreInfoScreen<T>
where
    T: ParagraphSource<'static>,
{
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.component("MoreInfoScreen");
        t.child("header", &self.header);
        t.child("paragraphs", &self.paragraphs);
        if self.paginated == Some(true) {
            t.child("action_bar", &self.action_bar);
        }
        t.int("page_count", i64::from(self.pager().total()));
    }
}
