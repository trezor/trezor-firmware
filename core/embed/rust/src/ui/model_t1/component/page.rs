use crate::ui::{
    component::{Component, ComponentExt, Event, EventCtx, Never, Pad, PageMsg, Paginate},
    display::{self, Color},
    geometry::{Insets, Offset, Point, Rect},
};

use super::{theme, Button, ButtonMsg, ButtonPos};

pub struct ButtonPage<T> {
    content: T,
    scrollbar: ScrollBar,
    pad: Pad,
    prev: Button<&'static str>,
    next: Button<&'static str>,
    cancel: Button<&'static str>,
    confirm: Button<&'static str>,
}

impl<T> ButtonPage<T>
where
    T: Paginate,
    T: Component,
{
    pub fn new(area: Rect, content: impl FnOnce(Rect) -> T, background: Color) -> Self {
        let (content_area, scrollbar_area, button_area) = Self::areas(area);
        let mut content = content(content_area);
        let pad = Pad::with_background(area, background);

        // Always start at the first page.
        let scrollbar = ScrollBar::vertical_right(scrollbar_area, content.page_count(), 0);

        // Create the button controls.
        let prev = Button::with_text(button_area, ButtonPos::Left, "BACK", theme::button_cancel());
        let next = Button::with_text(
            button_area,
            ButtonPos::Right,
            "NEXT",
            theme::button_default(),
        );
        let cancel = Button::with_text(
            button_area,
            ButtonPos::Left,
            "CANCEL",
            theme::button_cancel(),
        );
        let confirm = Button::with_text(
            button_area,
            ButtonPos::Right,
            "CONFIRM",
            theme::button_default(),
        );

        Self {
            content,
            scrollbar,
            pad,
            prev,
            next,
            cancel,
            confirm,
        }
    }

    fn areas(area: Rect) -> (Rect, Rect, Rect) {
        let button_height = theme::FONT_BOLD.line_height() + 2;
        let (content_area, button_area) = area.split_bottom(button_height);
        let (content_area, scrollbar_area) = content_area.split_right(ScrollBar::WIDTH);
        let (content_area, _) = content_area.split_bottom(1);
        (content_area, scrollbar_area, button_area)
    }

    fn change_page(&mut self, ctx: &mut EventCtx, page: usize) {
        // Change the page in the content, clear the background under it and make sure
        // it gets completely repainted.
        self.content.change_page(page);
        self.content.request_complete_repaint(ctx);
        self.pad.clear();
    }
}

impl<T> Component for ButtonPage<T>
where
    T: Component,
    T: Paginate,
{
    type Msg = PageMsg<T::Msg, bool>;

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        if self.scrollbar.has_previous_page() {
            if let Some(ButtonMsg::Clicked) = self.prev.event(ctx, event) {
                // Scroll up.
                self.scrollbar.go_to_previous_page();
                self.change_page(ctx, self.scrollbar.active_page);
                return None;
            }
        } else if let Some(ButtonMsg::Clicked) = self.cancel.event(ctx, event) {
            return Some(PageMsg::Controls(false));
        }

        if self.scrollbar.has_next_page() {
            if let Some(ButtonMsg::Clicked) = self.next.event(ctx, event) {
                // Scroll down.
                self.scrollbar.go_to_next_page();
                self.change_page(ctx, self.scrollbar.active_page);
                return None;
            }
        } else if let Some(ButtonMsg::Clicked) = self.confirm.event(ctx, event) {
            return Some(PageMsg::Controls(true));
        }

        if let Some(msg) = self.content.event(ctx, event) {
            return Some(PageMsg::Content(msg));
        }
        None
    }

    fn paint(&mut self) {
        self.pad.paint();
        self.content.paint();
        self.scrollbar.paint();
        if self.scrollbar.has_previous_page() {
            self.prev.paint();
        } else {
            self.cancel.paint();
        }
        if self.scrollbar.has_next_page() {
            self.next.paint();
        } else {
            self.confirm.paint();
        }
    }
}

#[cfg(feature = "ui_debug")]
impl<T> crate::trace::Trace for ButtonPage<T>
where
    T: crate::trace::Trace,
{
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.open("ButtonPage");
        t.field("active_page", &self.scrollbar.active_page);
        t.field("page_count", &self.scrollbar.page_count);
        t.field("content", &self.content);
        t.close();
    }
}

pub struct ScrollBar {
    area: Rect,
    page_count: usize,
    active_page: usize,
}

impl ScrollBar {
    pub const WIDTH: i32 = 8;
    pub const DOT_SIZE: Offset = Offset::new(4, 4);
    pub const DOT_INTERVAL: i32 = 6;

    pub fn vertical_right(area: Rect, page_count: usize, active_page: usize) -> Self {
        Self {
            area,
            page_count,
            active_page,
        }
    }

    pub fn has_next_page(&self) -> bool {
        self.active_page < self.page_count - 1
    }

    pub fn has_previous_page(&self) -> bool {
        self.active_page > 0
    }

    pub fn go_to_next_page(&mut self) {
        self.active_page = self.active_page.saturating_add(1).min(self.page_count - 1);
    }

    pub fn go_to_previous_page(&mut self) {
        self.active_page = self.active_page.saturating_sub(1);
    }

    fn paint_dot(&self, active: bool, top_left: Point) {
        let sides = [
            Rect::from_top_left_and_size(top_left + Offset::x(1), Offset::new(2, 1)),
            Rect::from_top_left_and_size(top_left + Offset::y(1), Offset::new(1, 2)),
            Rect::from_top_left_and_size(
                top_left + Offset::new(1, Self::DOT_SIZE.y - 1),
                Offset::new(2, 1),
            ),
            Rect::from_top_left_and_size(
                top_left + Offset::new(Self::DOT_SIZE.x - 1, 1),
                Offset::new(1, 2),
            ),
        ];
        for side in sides {
            display::rect_fill(side, theme::FG)
        }
        if active {
            display::rect_fill(
                Rect::from_top_left_and_size(top_left, Self::DOT_SIZE).inset(Insets::uniform(1)),
                theme::FG,
            )
        }
    }
}

impl Component for ScrollBar {
    type Msg = Never;

    fn event(&mut self, _ctx: &mut EventCtx, _event: Event) -> Option<Self::Msg> {
        None
    }

    fn paint(&mut self) {
        let count = self.page_count as i32;
        let interval = {
            let available_height = self.area.height();
            let naive_height = count * Self::DOT_INTERVAL;
            if naive_height > available_height {
                available_height / count
            } else {
                Self::DOT_INTERVAL
            }
        };
        let mut dot = Point::new(
            self.area.center().x - Self::DOT_SIZE.x / 2,
            self.area.center().y - (count / 2) * interval,
        );
        for i in 0..self.page_count {
            self.paint_dot(i == self.active_page, dot);
            dot.y += interval
        }
    }
}
