use crate::ui::{
    component::{
        paginated::{Page, PageMsg},
        Component, Event, EventCtx, Never,
    },
    display,
    geometry::{Offset, Point, Rect},
};

use super::{theme, Swipe, SwipeDirection};

pub struct SwipePage<T> {
    swipe: Swipe,
    scrollbar: ScrollBar,
    page: T,
    fade: Option<i32>,
}

impl<T> SwipePage<T> {
    fn setup_swipe(scrollbar: &ScrollBar, swipe: &mut Swipe) {
        swipe.allow_up = scrollbar.has_next_page();
        swipe.allow_down = scrollbar.has_previous_page();
    }
}

impl<T> Page for SwipePage<T> {
    type Content = T;

    fn new(area: Rect, page: T, page_count: usize, active_page: usize) -> Self {
        let scrollbar = ScrollBar::vertical_right(area, page_count, active_page);
        let mut swipe = Swipe::new(area);
        Self::setup_swipe(&scrollbar, &mut swipe);
        Self {
            swipe,
            scrollbar,
            page,
            fade: None,
        }
    }

    fn inner_mut(&mut self) -> &mut T {
        &mut self.page
    }

    fn page_count(&self) -> usize {
        self.scrollbar.page_count
    }

    fn active_page(&self) -> usize {
        self.scrollbar.active_page
    }

    fn fade_after_next_paint(&mut self) {
        self.fade = Some(theme::BACKLIGHT_NORMAL);
    }

    fn content_area(area: Rect) -> Rect {
        area
    }
}

impl<T: Component> Component for SwipePage<T> {
    type Msg = PageMsg<T::Msg, Never>;

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        if let Some(swipe) = self.swipe.event(ctx, event) {
            match swipe {
                SwipeDirection::Up => {
                    // Scroll down, if possible.
                    self.scrollbar.go_to_next_page();
                    Self::setup_swipe(&self.scrollbar, &mut self.swipe);
                    return Some(PageMsg::ChangePage(self.active_page()));
                }
                SwipeDirection::Down => {
                    // Scroll up, if possible.
                    self.scrollbar.go_to_previous_page();
                    Self::setup_swipe(&self.scrollbar, &mut self.swipe);
                    return Some(PageMsg::ChangePage(self.active_page()));
                }
                _ => {
                    // Ignore other directions.
                }
            }
        }
        if let Some(msg) = self.page.event(ctx, event) {
            return Some(PageMsg::Content(msg));
        }
        None
    }

    fn paint(&mut self) {
        self.page.paint();
        self.scrollbar.paint();
        if let Some(val) = self.fade.take() {
            display::fade_backlight(val);
        }
    }
}

#[cfg(feature = "ui_debug")]
impl<T> crate::trace::Trace for SwipePage<T>
where
    T: crate::trace::Trace,
{
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.open("SwipePage");
        t.field("active_page", &self.active_page());
        t.field("page_count", &self.page_count());
        t.field("content", &self.page);
        t.close();
    }
}

pub struct ScrollBar {
    area: Rect,
    page_count: usize,
    active_page: usize,
}

impl ScrollBar {
    pub const DOT_SIZE: Offset = Offset::new(8, 8);
    pub const DOT_INTERVAL: i32 = 14;

    pub fn vertical_right(area: Rect, page_count: usize, active_page: usize) -> Self {
        Self {
            area: area.cut_from_right(Self::DOT_SIZE.x),
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
            self.area.center().x,
            self.area.center().y - (count / 2) * interval,
        );
        for i in 0..self.page_count {
            display::rounded_rect(
                Rect::from_center_and_size(dot, Self::DOT_SIZE),
                if i == self.active_page {
                    theme::FG
                } else {
                    theme::GREY_LIGHT
                },
                theme::BG,
                theme::RADIUS,
            );
            dot.y += interval;
        }
    }
}
