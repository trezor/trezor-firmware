use super::theme;
use crate::ui::{
    component::{
        base::ComponentExt, label::Label, text::TextStyle, Child, Component, Event, EventCtx,
    },
    display::{self, Color, Font},
    geometry::{Alignment, Insets, Offset, Rect},
};

pub struct Frame<T, U> {
    border: Insets,
    title: Child<Label<U>>,
    content: Child<T>,
}

impl<T, U> Frame<T, U>
where
    T: Component,
    U: AsRef<str>,
{
    pub fn new(style: TextStyle, alignment: Alignment, title: U, content: T) -> Self {
        Self {
            title: Child::new(Label::new(title, alignment, style)),
            border: theme::borders_scroll(),
            content: Child::new(content),
        }
    }

    pub fn left_aligned(style: TextStyle, title: U, content: T) -> Self {
        Self::new(style, Alignment::Start, title, content)
    }

    pub fn right_aligned(style: TextStyle, title: U, content: T) -> Self {
        Self::new(style, Alignment::End, title, content)
    }

    pub fn centered(style: TextStyle, title: U, content: T) -> Self {
        Self::new(style, Alignment::Center, title, content)
    }

    pub fn with_border(mut self, border: Insets) -> Self {
        self.border = border;
        self
    }

    pub fn inner(&self) -> &T {
        self.content.inner()
    }

    pub fn update_title(&mut self, ctx: &mut EventCtx, new_title: U) {
        self.title.mutate(ctx, |ctx, t| {
            t.set_text(new_title);
            t.request_complete_repaint(ctx)
        })
    }

    pub fn update_content<F>(&mut self, ctx: &mut EventCtx, update_fn: F)
    where
        F: Fn(&mut T),
    {
        self.content.mutate(ctx, |ctx, c| {
            update_fn(c);
            c.request_complete_repaint(ctx)
        })
    }
}

impl<T, U> Component for Frame<T, U>
where
    T: Component,
    U: AsRef<str>,
{
    type Msg = T::Msg;

    fn place(&mut self, bounds: Rect) -> Rect {
        const TITLE_SPACE: i16 = theme::BUTTON_SPACING;

        let bounds = bounds.inset(self.border);
        let title_area = bounds.inset(Insets::sides(theme::CONTENT_BORDER));
        let title_area = self.title.place(title_area);
        let content_area = bounds.inset(Insets::top(title_area.height() + TITLE_SPACE));
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

    fn bounds(&self, sink: &mut dyn FnMut(Rect)) {
        self.title.bounds(sink);
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

pub struct NotificationFrame<T, U> {
    area: Rect,
    title: U,
    content: Child<T>,
}

impl<T, U> NotificationFrame<T, U>
where
    T: Component,
    U: AsRef<str>,
{
    const HEIGHT: i16 = 36;
    const COLOR: Color = theme::YELLOW;
    const BORDER: i16 = 6;

    pub fn new(title: U, content: T) -> Self {
        Self {
            title,
            area: Rect::zero(),
            content: Child::new(content),
        }
    }

    pub fn inner(&self) -> &T {
        self.content.inner()
    }

    pub fn paint_notification(area: Rect, title: &str, color: Color) {
        let (area, _) = area
            .inset(Insets::uniform(Self::BORDER))
            .split_top(Self::HEIGHT);
        let font = Font::BOLD;
        display::rect_fill_rounded(area, color, theme::BG, 2);
        display::text_center(
            area.center() + Offset::y((font.text_max_height() - font.text_baseline()) / 2),
            title,
            Font::BOLD,
            theme::FG,
            color,
        );
    }
}

impl<T, U> Component for NotificationFrame<T, U>
where
    T: Component,
    U: AsRef<str>,
{
    type Msg = T::Msg;

    fn place(&mut self, bounds: Rect) -> Rect {
        let content_area = bounds.inset(theme::borders_notification());
        self.area = bounds;
        self.content.place(content_area);
        bounds
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        self.content.event(ctx, event)
    }

    fn paint(&mut self) {
        Self::paint_notification(self.area, self.title.as_ref(), Self::COLOR);
        self.content.paint();
    }

    fn bounds(&self, sink: &mut dyn FnMut(Rect)) {
        sink(self.area);
        self.content.bounds(sink);
    }
}

#[cfg(feature = "ui_debug")]
impl<T, U> crate::trace::Trace for NotificationFrame<T, U>
where
    T: crate::trace::Trace,
    U: crate::trace::Trace + AsRef<str>,
{
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.open("NotificationFrame");
        t.field("title", &self.title);
        t.field("content", &self.content);
        t.close();
    }
}
