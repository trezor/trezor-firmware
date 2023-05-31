use super::theme;
use crate::ui::{
    component::{
        base::ComponentExt, label::Label, text::TextStyle, Child, Component, Event, EventCtx,
    },
    display::{self, Color, Font, Icon},
    geometry::{Alignment, Insets, Offset, Rect},
    model_tt::component::{Button, ButtonMsg, CancelInfoConfirmMsg},
};

pub struct Frame<T, U> {
    border: Insets,
    title: Child<Label<U>>,
    subtitle: Option<Child<Label<U>>>,
    button: Option<Child<Button<&'static str>>>,
    button_msg: CancelInfoConfirmMsg,
    content: Child<T>,
}

pub enum FrameMsg<T> {
    Content(T),
    Button(CancelInfoConfirmMsg),
}

impl<T, U> Frame<T, U>
where
    T: Component,
    U: AsRef<str>,
{
    pub fn new(style: TextStyle, alignment: Alignment, title: U, content: T) -> Self {
        Self {
            title: Child::new(Label::new(title, alignment, style)),
            subtitle: None,
            border: theme::borders(),
            button: None,
            button_msg: CancelInfoConfirmMsg::Cancelled,
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

    pub fn with_subtitle(mut self, style: TextStyle, subtitle: U) -> Self {
        self.subtitle = Some(Child::new(Label::new(
            subtitle,
            self.title.inner().alignment(),
            style,
        )));
        self
    }

    fn with_button(mut self, icon: Icon, msg: CancelInfoConfirmMsg) -> Self {
        let touch_area = Insets {
            left: self.border.left * 4,
            bottom: self.border.bottom * 4,
            ..self.border
        };
        self.button = Some(Child::new(
            Button::with_icon(icon)
                .with_expanded_touch_area(touch_area)
                .styled(theme::button_moreinfo()),
        ));
        self.button_msg = msg;
        self
    }

    pub fn with_cancel_button(self) -> Self {
        self.with_button(theme::ICON_CORNER_CANCEL, CancelInfoConfirmMsg::Cancelled)
    }

    pub fn with_info_button(self) -> Self {
        self.with_button(theme::ICON_CORNER_INFO, CancelInfoConfirmMsg::Info)
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

    pub fn update_content<F, R>(&mut self, ctx: &mut EventCtx, update_fn: F) -> R
    where
        F: Fn(&mut T) -> R,
    {
        self.content.mutate(ctx, |ctx, c| {
            let res = update_fn(c);
            c.request_complete_repaint(ctx);
            res
        })
    }
}

impl<T, U> Component for Frame<T, U>
where
    T: Component,
    U: AsRef<str>,
{
    type Msg = FrameMsg<T::Msg>;

    fn place(&mut self, bounds: Rect) -> Rect {
        const TITLE_SPACE: i16 = theme::BUTTON_SPACING;

        let bounds = bounds.inset(self.border);
        if let Some(b) = &mut self.button {
            let button_side = theme::CORNER_BUTTON_SIDE;
            let (header_area, button_area) = bounds.split_right(button_side);
            let (button_area, _) = button_area.split_top(button_side);
            b.place(button_area);
            let title_area = self.title.place(header_area);
            let remaining = header_area.inset(Insets::top(title_area.height()));
            let subtitle_area = self.subtitle.place(remaining);

            let title_height = title_area.height() + subtitle_area.height();
            let header_height = title_height.max(button_side);
            if title_height < button_side {
                self.title
                    .place(title_area.translate(Offset::y((button_side - title_height) / 2)));
                self.subtitle
                    .place(subtitle_area.translate(Offset::y((button_side - title_height) / 2)));
            }
            let content_area = bounds.inset(Insets::top(header_height + TITLE_SPACE));
            self.content.place(content_area);
        } else {
            let title_area = self.title.place(bounds);
            let remaining = bounds.inset(Insets::top(title_area.height()));
            let subtitle_area = self.subtitle.place(remaining);
            let remaining = remaining.inset(Insets::top(subtitle_area.height()));
            let content_area = remaining.inset(Insets::top(TITLE_SPACE));
            self.content.place(content_area);
        }
        bounds
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        self.title.event(ctx, event);
        self.subtitle.event(ctx, event);
        if let Some(ButtonMsg::Clicked) = self.button.event(ctx, event) {
            return Some(FrameMsg::Button(self.button_msg));
        }
        self.content.event(ctx, event).map(FrameMsg::Content)
    }

    fn paint(&mut self) {
        self.title.paint();
        self.subtitle.paint();
        self.button.paint();
        self.content.paint();
    }

    #[cfg(feature = "ui_bounds")]
    fn bounds(&self, sink: &mut dyn FnMut(Rect)) {
        self.title.bounds(sink);
        self.subtitle.bounds(sink);
        self.button.bounds(sink);
        self.content.bounds(sink);
    }
}

#[cfg(feature = "ui_debug")]
impl<T, U> crate::trace::Trace for Frame<T, U>
where
    T: crate::trace::Trace,
    U: AsRef<str>,
{
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.component("Frame");
        t.child("title", &self.title);
        t.child("content", &self.content);
        if let Some(subtitle) = &self.subtitle {
            t.child("subtitle", subtitle);
        }
        if let Some(button) = &self.button {
            t.child("button", button);
        }
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
            font,
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

    #[cfg(feature = "ui_bounds")]
    fn bounds(&self, sink: &mut dyn FnMut(Rect)) {
        sink(self.area);
        self.content.bounds(sink);
    }
}

#[cfg(feature = "ui_debug")]
impl<T, U> crate::trace::Trace for NotificationFrame<T, U>
where
    T: crate::trace::Trace,
    U: AsRef<str>,
{
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.component("NotificationFrame");
        t.string("title", self.title.as_ref());
        t.child("content", &self.content);
    }
}
