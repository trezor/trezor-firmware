use super::{theme, ScrollBar};
use crate::{
    micropython::buffer::StrBuffer,
    ui::{
        component::{Child, Component, Event, EventCtx},
        geometry::{Insets, Rect},
        model_tr::component::title::Title,
    },
};

/// Component for holding another component and displaying a title.
/// Also is allocating space for a scrollbar.
pub struct Frame<T> {
    area: Rect,
    title: Title,
    account_for_scrollbar: bool,
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
            account_for_scrollbar: true,
            content: Child::new(content),
        }
    }

    pub fn inner(&self) -> &T {
        self.content.inner()
    }

    /// Aligning the title to the center, instead of the left.
    /// Also disabling scrollbar, as they are not compatible.
    pub fn with_title_centered(mut self) -> Self {
        self.title = self.title.with_title_centered();
        self.account_for_scrollbar = false;
        self
    }

    /// Allocating space for scrollbar in the top right. True by default.
    pub fn with_scrollbar(mut self, account_for_scrollbar: bool) -> Self {
        self.account_for_scrollbar = account_for_scrollbar;
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
