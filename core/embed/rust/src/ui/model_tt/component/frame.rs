use super::theme;
use crate::ui::{
    component::{Child, Component, ComponentExt, Event, EventCtx},
    display,
    geometry::Rect,
};

pub struct Frame<T, U> {
    area: Rect,
    title: U,
    content: Child<T>,
}

impl<T, U> Frame<T, U>
where
    T: Component,
    U: AsRef<[u8]>,
{
    pub fn new(area: Rect, title: U, content: impl FnOnce(Rect) -> T) -> Self {
        let (title_area, content_area) = Self::areas(area);
        Self {
            area: title_area,
            title,
            content: content(content_area).into_child(),
        }
    }

    fn areas(area: Rect) -> (Rect, Rect) {
        const HEADER_SPACE: i32 = 14;
        let header_height = theme::FONT_BOLD.line_height() - theme::CONTENT_BORDER;

        let (header_area, content_area) = area.split_top(header_height);
        let (_space, header_area) = header_area.split_left(theme::CONTENT_BORDER);
        let (_space, content_area) = content_area.split_top(HEADER_SPACE);

        (header_area, content_area)
    }
}

impl<T, U> Component for Frame<T, U>
where
    T: Component,
    U: AsRef<[u8]>,
{
    type Msg = T::Msg;

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
    U: crate::trace::Trace + AsRef<[u8]>,
{
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.open("Frame");
        t.field("title", &self.title);
        t.field("content", &self.content);
        t.close();
    }
}
