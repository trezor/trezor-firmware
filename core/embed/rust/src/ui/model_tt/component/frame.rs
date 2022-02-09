use super::theme;
use crate::ui::{
    component::{Child, Component, Event, EventCtx},
    display,
    geometry::{Insets, Rect},
};

pub struct Frame<T, U> {
    area: Rect,
    title: U,
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
            content: Child::new(content),
        }
    }

    pub fn inner(&self) -> &T {
        &self.content.inner()
    }
}

impl<T, U> Component for Frame<T, U>
where
    T: Component,
    U: AsRef<str>,
{
    type Msg = T::Msg;

    fn place(&mut self, bounds: Rect) -> Rect {
        // Same as PageLayout::BUTTON_SPACE.
        const TITLE_SPACE: i32 = 6;

        let (title_area, content_area) = bounds
            .inset(theme::borders_scroll())
            .split_top(theme::FONT_BOLD.text_height());
        let title_area = title_area.inset(Insets::left(theme::CONTENT_BORDER));
        let content_area = content_area.inset(Insets::top(TITLE_SPACE));

        self.area = title_area;
        self.content.place(content_area);
        bounds
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        self.content.event(ctx, event)
    }

    fn paint(&mut self) {
        display::text(
            self.area.bottom_left(),
            self.title.as_ref(),
            theme::FONT_BOLD,
            theme::GREY_LIGHT,
            theme::BG,
        );
        self.content.paint();
    }

    fn bounds(&self, sink: &mut dyn FnMut(Rect)) {
        sink(self.area);
        self.content.bounds(sink);
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
