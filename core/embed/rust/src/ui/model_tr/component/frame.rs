use super::{theme, ScrollBar};
use crate::{
    micropython::buffer::StrBuffer,
    ui::{
        component::{Child, Component, Event, EventCtx},
        geometry::{Insets, Rect},
        model_tr::component::{scrollbar::SCROLLBAR_SPACE, title::Title},
    },
};

/// Component for holding another component and displaying a title.
pub struct Frame<T> {
    area: Rect,
    title: Title,
    content: Child<T>,
}

impl<T> Frame<T>
where
    T: Component,
{
    pub fn new(title: StrBuffer, content: T) -> Self {
        Self {
            area: Rect::zero(),
            title: Title::new(title),
            content: Child::new(content),
        }
    }

    pub fn inner(&self) -> &T {
        self.content.inner()
    }

    /// Aligning the title to the center, instead of the left.
    pub fn with_title_centered(mut self) -> Self {
        self.title = self.title.with_title_centered();
        self
    }
}

impl<T> Component for Frame<T>
where
    T: Component,
{
    type Msg = T::Msg;

    fn place(&mut self, bounds: Rect) -> Rect {
        const TITLE_SPACE: i16 = 2;

        let (title_area, content_area) = bounds.split_top(theme::FONT_HEADER.line_height());
        let content_area = content_area.inset(Insets::top(TITLE_SPACE));

        self.area = bounds;
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

pub trait ScrollableContent {
    fn page_count(&self) -> usize;
    fn active_page(&self) -> usize;
}

/// Component for holding another component and displaying a title.
/// Also is allocating space for a scrollbar.
pub struct ScrollableFrame<T> {
    area: Rect,
    title: Title,
    scrollbar: ScrollBar,
    content: Child<T>,
}

impl<T> ScrollableFrame<T>
where
    T: Component + ScrollableContent,
{
    pub fn new(title: StrBuffer, content: T) -> Self {
        Self {
            area: Rect::zero(),
            title: Title::new(title),
            scrollbar: ScrollBar::to_be_filled_later(),
            content: Child::new(content),
        }
    }

    pub fn inner(&self) -> &T {
        self.content.inner()
    }
}

impl<T> Component for ScrollableFrame<T>
where
    T: Component + ScrollableContent,
{
    type Msg = T::Msg;

    fn place(&mut self, bounds: Rect) -> Rect {
        const TITLE_SPACE: i16 = 2;

        let (title_and_scrollbar_area, content_area) =
            bounds.split_top(theme::FONT_HEADER.line_height());
        let content_area = content_area.inset(Insets::top(TITLE_SPACE));

        self.content.place(content_area);

        self.scrollbar
            .set_page_count(self.content.inner().page_count());

        // Title area is different based on scrollbar.

        let (title_area, scrollbar_area) =
            title_and_scrollbar_area.split_right(self.scrollbar.overall_width() + SCROLLBAR_SPACE);

        self.area = title_area;
        self.scrollbar.place(scrollbar_area);
        self.title.place(title_area);
        bounds
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        let msg = self.content.event(ctx, event);
        self.scrollbar
            .set_active_page(self.content.inner().active_page(), ctx);
        self.title.event(ctx, event);
        self.scrollbar.event(ctx, event);
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
impl<T> crate::trace::Trace for Frame<T>
where
    T: crate::trace::Trace,
{
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.open("Frame");
        t.field("title", &self.title);
        t.field("content", &self.content);
        t.close();
    }
}

// DEBUG-ONLY SECTION BELOW

#[cfg(feature = "ui_debug")]
impl<T> crate::trace::Trace for ScrollableFrame<T>
where
    T: crate::trace::Trace,
{
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.open("ScrollableFrame");
        t.field("title", &self.title);
        t.field("scrollbar", &self.title);
        t.field("content", &self.content);
        t.close();
    }
}
