use crate::{
    strutil::StringType,
    ui::{
        component::{Child, Component, ComponentExt, Event, EventCtx, Paginate},
        geometry::{Insets, Rect},
    },
};

use super::{super::constant, scrollbar::SCROLLBAR_SPACE, theme, title::Title, ScrollBar};

/// Component for holding another component and displaying a title.
pub struct Frame<T, U>
where
    T: Component,
    U: StringType,
{
    title: Title<U>,
    content: Child<T>,
}

impl<T, U> Frame<T, U>
where
    T: Component,
    U: StringType + Clone,
{
    pub fn new(title: U, content: T) -> Self {
        Self {
            title: Title::new(title),
            content: Child::new(content),
        }
    }

    /// Aligning the title to the center, instead of the left.
    pub fn with_title_centered(mut self) -> Self {
        self.title = self.title.with_centered();
        self
    }

    pub fn inner(&self) -> &T {
        self.content.inner()
    }

    pub fn update_title(&mut self, ctx: &mut EventCtx, new_title: U) {
        self.title.set_text(ctx, new_title);
    }

    pub fn update_content<F, R>(&mut self, ctx: &mut EventCtx, update_fn: F) -> R
    where
        F: Fn(&mut T) -> R,
    {
        self.content.mutate(ctx, |ctx, c| {
            let res = update_fn(c);
            c.request_complete_repaint(ctx);
            res
        })
    }
}

impl<T, U> Component for Frame<T, U>
where
    T: Component,
    U: StringType + Clone,
{
    type Msg = T::Msg;

    fn place(&mut self, bounds: Rect) -> Rect {
        const TITLE_SPACE: i16 = 2;

        let (title_area, content_area) = bounds.split_top(theme::FONT_HEADER.line_height());
        let content_area = content_area.inset(Insets::top(TITLE_SPACE));

        self.title.place(title_area);
        self.content.place(content_area);
        bounds
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        self.title.event(ctx, event);
        self.content.event(ctx, event)
    }

    fn paint(&mut self) {
        self.title.paint();
        self.content.paint();
    }
}

impl<T, U> Paginate for Frame<T, U>
where
    T: Component + Paginate,
    U: StringType + Clone,
{
    fn page_count(&mut self) -> usize {
        self.content.page_count()
    }

    fn change_page(&mut self, active_page: usize) {
        self.content.change_page(active_page);
    }
}

pub trait ScrollableContent {
    fn page_count(&self) -> usize;
    fn active_page(&self) -> usize;
}

/// Component for holding another component and displaying a title.
/// Also is allocating space for a scrollbar.
pub struct ScrollableFrame<T, U>
where
    T: Component + ScrollableContent,
    U: StringType + Clone,
{
    title: Option<Child<Title<U>>>,
    scrollbar: ScrollBar,
    content: Child<T>,
}

impl<T, U> ScrollableFrame<T, U>
where
    T: Component + ScrollableContent,
    U: StringType + Clone,
{
    pub fn new(content: T) -> Self {
        Self {
            title: None,
            scrollbar: ScrollBar::to_be_filled_later(),
            content: Child::new(content),
        }
    }

    pub fn inner(&self) -> &T {
        self.content.inner()
    }

    pub fn with_title(mut self, title: U) -> Self {
        self.title = Some(Child::new(Title::new(title)));
        self
    }
}

impl<T, U> Component for ScrollableFrame<T, U>
where
    T: Component + ScrollableContent,
    U: StringType + Clone,
{
    type Msg = T::Msg;

    fn place(&mut self, bounds: Rect) -> Rect {
        // Depending whether there is a title or not
        let (content_area, scrollbar_area, title_area) = if self.title.is_none() {
            // When the content fits on one page, no need for allocating place for scrollbar
            self.content.place(bounds);
            let page_count = self.content.inner().page_count();
            self.scrollbar.set_page_count(page_count);
            if page_count == 1 {
                (bounds, Rect::zero(), Rect::zero())
            } else {
                let (scrollbar_area, content_area) =
                    bounds.split_top(ScrollBar::MAX_DOT_SIZE + constant::LINE_SPACE);
                (content_area, scrollbar_area, Rect::zero())
            }
        } else {
            let (title_and_scrollbar_area, content_area) =
                bounds.split_top(theme::FONT_HEADER.line_height());

            // When there is only one page, do not allocate anything for scrollbar,
            // which would reduce the space for title
            self.content.place(content_area);
            let page_count = self.content.inner().page_count();
            self.scrollbar.set_page_count(page_count);
            let (title_area, scrollbar_area) = if page_count == 1 {
                (title_and_scrollbar_area, Rect::zero())
            } else {
                title_and_scrollbar_area
                    .split_right(self.scrollbar.overall_width() + SCROLLBAR_SPACE)
            };

            (content_area, scrollbar_area, title_area)
        };

        self.content.place(content_area);
        self.scrollbar.place(scrollbar_area);
        self.title.place(title_area);
        bounds
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        let msg = self.content.event(ctx, event);
        let content_active_page = self.content.inner().active_page();
        if self.scrollbar.active_page != content_active_page {
            self.scrollbar.change_page(content_active_page);
            self.scrollbar.request_complete_repaint(ctx);
        }
        self.title.event(ctx, event);
        msg
    }

    fn paint(&mut self) {
        self.title.paint();
        self.scrollbar.paint();
        self.content.paint();
    }
}

// DEBUG-ONLY SECTION BELOW

#[cfg(feature = "ui_debug")]
impl<T, U> crate::trace::Trace for Frame<T, U>
where
    T: crate::trace::Trace + Component,
    U: StringType + Clone,
{
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.component("Frame");
        t.child("title", &self.title);
        t.child("content", &self.content);
    }
}

#[cfg(feature = "ui_debug")]
impl<T, U> crate::trace::Trace for ScrollableFrame<T, U>
where
    T: crate::trace::Trace + Component + ScrollableContent,
    U: StringType + Clone,
{
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.component("ScrollableFrame");
        if let Some(title) = &self.title {
            t.child("title", title);
        }
        t.child("scrollbar", &self.scrollbar);
        t.child("content", &self.content);
    }
}
