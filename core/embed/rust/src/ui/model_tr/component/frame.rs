use super::{common, theme};
use crate::ui::{
    component::{Child, Component, Event, EventCtx},
    geometry::{Insets, Rect},
};

/// Component for holding another component and displaying
/// a title and optionally a subtitle describing that child component.
pub struct Frame<T, U> {
    area: Rect,
    title: U,
    subtitle: Option<U>,
    content: Child<T>,
}

impl<T, U> Frame<T, U>
where
    T: Component,
    U: AsRef<str>,
{
    pub fn new(title: U, subtitle: Option<U>, content: T) -> Self {
        Self {
            title,
            subtitle,
            area: Rect::zero(),
            content: Child::new(content),
        }
    }

    pub fn inner(&self) -> &T {
        self.content.inner()
    }
}

impl<T, U> Component for Frame<T, U>
where
    T: Component,
    U: AsRef<str>,
{
    type Msg = T::Msg;

    fn place(&mut self, bounds: Rect) -> Rect {
        // Depending on whether there is subtitle or not
        let title_space = if self.subtitle.is_some() { 12 } else { 4 };

        let (title_area, content_area) = bounds.split_top(theme::FONT_HEADER.line_height());
        let content_area = content_area.inset(Insets::top(title_space));

        self.area = title_area;
        self.content.place(content_area);
        bounds
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        self.content.event(ctx, event)
    }

    fn paint(&mut self) {
        common::paint_header(self.area.top_left(), &self.title, &self.subtitle);
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
        t.field("title", &self.title);
        t.field("content", &self.content);
        t.close();
    }
}
