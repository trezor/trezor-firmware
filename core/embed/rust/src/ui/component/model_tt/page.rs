use crate::ui::{
    component::{Component, Event, EventCtx, Never},
    display,
    geometry::{Offset, Point, Rect},
};

use super::{theme, Swipe, SwipeDirection};

pub enum PageMsg<T> {
    Content(T),
    ChangePage(usize),
}

pub struct Page<T> {
    swipe: Swipe,
    scrollbar: ScrollBar,
    page: T,
}

impl<T> Page<T> {
    pub fn new(area: Rect, page: T, page_count: usize, active_page: usize) -> Self {
        let scrollbar = ScrollBar::vertical_right(area, page_count, active_page);
        let mut swipe = Swipe::new(area);
        swipe.allow_up = scrollbar.has_next_page();
        swipe.allow_down = scrollbar.has_previous_page();
        Self {
            swipe,
            scrollbar,
            page,
        }
    }
}

impl<T: Component> Component for Page<T> {
    type Msg = PageMsg<T::Msg>;

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        if let Some(swipe) = self.swipe.event(ctx, event) {
            match swipe {
                SwipeDirection::Up => {
                    // Scroll down, if possible.
                    return Some(PageMsg::ChangePage(self.scrollbar.next_page()));
                }
                SwipeDirection::Down => {
                    // Scroll up, if possible.
                    return Some(PageMsg::ChangePage(self.scrollbar.previous_page()));
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

    pub fn next_page(&self) -> usize {
        self.active_page.saturating_add(1).min(self.page_count - 1)
    }

    pub fn previous_page(&self) -> usize {
        self.active_page.saturating_sub(1)
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
