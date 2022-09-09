use super::theme;
use crate::ui::{
    component::{Child, Component, Event, EventCtx},
    display::{self, Color, Font},
    geometry::{Insets, Offset, Rect},
};

pub struct Frame<T, U> {
    area: Rect,
    border: Insets,
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
            border: theme::borders_scroll(),
            content: Child::new(content),
        }
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
            Font::BOLD,
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

pub struct NotificationFrame<T, U> {
    area: Rect,
    border: Insets,
    icon: &'static [u8],
    title: U,
    content: Child<T>,
}

impl<T, U> NotificationFrame<T, U>
where
    T: Component,
    U: AsRef<str>,
{
    const HEIGHT: i16 = 42;
    const COLOR: Color = theme::YELLOW;
    const FONT: Font = Font::BOLD;
    const TEXT_OFFSET: Offset = Offset::new(1, -2);
    const ICON_SPACE: i16 = 8;

    pub fn new(icon: &'static [u8], title: U, content: T) -> Self {
        Self {
            icon,
            title,
            area: Rect::zero(),
            border: theme::borders_notification(),
            content: Child::new(content),
        }
    }

    pub fn inner(&self) -> &T {
        self.content.inner()
    }
}

impl<T, U> Component for NotificationFrame<T, U>
where
    T: Component,
    U: AsRef<str>,
{
    type Msg = T::Msg;

    fn place(&mut self, bounds: Rect) -> Rect {
        let (title_area, content_area) = bounds.split_top(Self::HEIGHT);
        let content_area = content_area.inset(self.border);

        self.area = title_area;
        self.content.place(content_area);
        bounds
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        self.content.event(ctx, event)
    }

    fn paint(&mut self) {
        let toif_info = unwrap!(display::toif_info(self.icon), "Invalid TOIF data");
        let icon_width = toif_info.0.y;
        let text_width = Self::FONT.text_width(self.title.as_ref());
        let text_height = Self::FONT.text_height();
        let text_center =
            self.area.center() + Offset::new((icon_width + Self::ICON_SPACE) / 2, text_height / 2);
        let icon_center = self.area.center() - Offset::x((text_width + Self::ICON_SPACE) / 2);

        display::rect_fill_rounded(self.area, Self::COLOR, theme::BG, 2);
        display::text_center(
            text_center + Self::TEXT_OFFSET,
            self.title.as_ref(),
            Self::FONT,
            theme::BG,
            Self::COLOR,
        );
        display::icon(icon_center, self.icon, theme::BG, Self::COLOR);

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
