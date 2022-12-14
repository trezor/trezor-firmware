use super::theme;
use crate::ui::{
    component::{label::Label, text::TextStyle, Child, Component, Event, EventCtx},
    display::{self, Color, Font},
    geometry::{Alignment, Insets, Offset, Rect},
    util::icon_text_center,
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
}

impl<T, U> Component for Frame<T, U>
where
    T: Component,
    U: AsRef<str>,
{
    type Msg = T::Msg;

    fn place(&mut self, bounds: Rect) -> Rect {
        const TITLE_SPACE: i16 = theme::BUTTON_SPACING;

        let (title_area, content_area) = bounds
            .inset(self.border)
            .split_top(Font::BOLD.text_height());
        let title_area = title_area.inset(Insets::sides(theme::CONTENT_BORDER));
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
    icon: &'static [u8],
    title: U,
    content: Child<T>,
}

impl<T, U> NotificationFrame<T, U>
where
    T: Component,
    U: AsRef<str>,
{
    const HEIGHT: i16 = 32;
    const COLOR: Color = theme::YELLOW;
    const TEXT_OFFSET: Offset = Offset::new(1, -2);
    const ICON_SPACE: i16 = 8;
    const BORDER: i16 = 8;

    pub fn new(icon: &'static [u8], title: U, content: T) -> Self {
        Self {
            icon,
            title,
            area: Rect::zero(),
            content: Child::new(content),
        }
    }

    pub fn inner(&self) -> &T {
        self.content.inner()
    }

    pub fn paint_notification(area: Rect, icon: &'static [u8], title: &str, color: Color) {
        let (area, _) = area
            .inset(Insets::uniform(Self::BORDER))
            .split_top(Self::HEIGHT);
        let style = TextStyle {
            background_color: color,
            ..theme::TEXT_BOLD
        };
        display::rect_fill_rounded(area, color, theme::BG, 2);
        icon_text_center(
            area.center(),
            icon,
            Self::ICON_SPACE,
            title,
            style,
            Self::TEXT_OFFSET,
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
        Self::paint_notification(self.area, self.icon, self.title.as_ref(), Self::COLOR);
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
