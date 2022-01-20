use super::theme;
use crate::ui::{
    component::{Child, Component, ComponentExt, Event, EventCtx},
    display,
    geometry::{Offset, Rect},
};

pub struct Frame<T, U> {
    area: Rect,
    title: U,
    content: Child<T>,
}

impl<T: Component, U: AsRef<[u8]>> Frame<T, U> {
    pub fn new(area: Rect, title: U, content: impl FnOnce(Rect) -> T) -> Self {
        let (title_area, content_area) = Self::areas(area);
        Self {
            area: title_area,
            title,
            content: content(content_area).into_child(),
        }
    }

    fn areas(area: Rect) -> (Rect, Rect) {
        const HEADER_SPACE: i32 = 4;
        let header_height = theme::FONT_BOLD.line_height();

        let (header_area, content_area) = area.split_top(header_height);
        let (_space, content_area) = content_area.split_top(HEADER_SPACE);

        (header_area, content_area)
    }
}

impl<T: Component, U: AsRef<[u8]>> Component for Frame<T, U> {
    type Msg = T::Msg;

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        self.content.event(ctx, event)
    }

    fn paint(&mut self) {
        display::text(
            self.area.bottom_left() - Offset::y(2),
            self.title.as_ref(),
            theme::FONT_BOLD,
            theme::FG,
            theme::BG,
        );
        display::dotted_line(self.area.bottom_left(), self.area.width(), theme::FG);
        self.content.paint();
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
