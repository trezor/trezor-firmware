use super::{common, theme, ScrollBar};
use crate::ui::{
    component::{Child, Component, Event, EventCtx},
    geometry::{Insets, Rect},
};

/// Component for holding another component and displaying a title.
/// Also is allocating space for a scrollbar.
pub struct Frame<T, U> {
    area: Rect,
    title: U,
    title_centered: bool,
    account_for_scrollbar: bool,
    content: Child<T>,
}

impl<T, U> Frame<T, U>
where
    T: Component,
    U: AsRef<str>,
{
    pub fn new(title: U, content: T) -> Self {
        Self {
            title,
            area: Rect::zero(),
            title_centered: false,
            account_for_scrollbar: true,
            content: Child::new(content),
        }
    }

    pub fn inner(&self) -> &T {
        self.content.inner()
    }

    /// Aligning the title to the center, instead of the left.
    /// Also disabling scrollbar in the positive case, as they are not
    /// compatible.
    pub fn with_title_center(mut self, title_centered: bool) -> Self {
        self.title_centered = title_centered;
        if title_centered {
            self.account_for_scrollbar = false;
        }
        self
    }

    /// Allocating space for scrollbar in the top right. True by default.
    pub fn with_scrollbar(mut self, account_for_scrollbar: bool) -> Self {
        self.account_for_scrollbar = account_for_scrollbar;
        self
    }
}

impl<T, U> Component for Frame<T, U>
where
    T: Component,
    U: AsRef<str>,
{
    type Msg = T::Msg;

    fn place(&mut self, bounds: Rect) -> Rect {
        const TITLE_SPACE: i16 = 2;

        let (title_and_scrollbar_area, content_area) =
            bounds.split_top(theme::FONT_HEADER.line_height());
        let content_area = content_area.inset(Insets::top(TITLE_SPACE));

        // Title area is different based on scrollbar.
        let title_area = if self.account_for_scrollbar {
            let (title_area, scrollbar_area) =
                title_and_scrollbar_area.split_right(ScrollBar::MAX_WIDTH);
            // Sending the scrollbar area to the child component.
            self.content.set_scrollbar_area(scrollbar_area);
            title_area
        } else {
            title_and_scrollbar_area
        };

        self.area = title_area;
        self.content.place(content_area);
        bounds
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        self.content.event(ctx, event)
    }

    fn paint(&mut self) {
        if self.title_centered {
            common::paint_header_centered(&self.title, self.area);
        } else {
            common::paint_header_left(&self.title, self.area);
        }
        self.content.paint();
    }
}

#[cfg(feature = "ui_debug")]
impl<T, U> crate::trace::Trace for Frame<T, U>
where
    T: crate::trace::Trace,
    U: crate::trace::Trace + AsRef<str>,
{
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.open("Frame");
        t.title(self.title.as_ref());
        t.field("content", &self.content);
        t.close();
    }
}
