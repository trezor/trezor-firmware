use crate::ui::{
    component::{Component, ComponentExt, Event, EventCtx, Never, Pad, PageMsg, Paginate},
    display::{self, Color},
    geometry::{Offset, Point, Rect},
};

use super::{theme, Swipe, SwipeDirection};

pub struct SwipePage<T> {
    content: T,
    pad: Pad,
    swipe: Swipe,
    scrollbar: ScrollBar,
    fade: Option<i32>,
}

impl<T> SwipePage<T>
where
    T: Paginate,
    T: Component,
{
    pub fn new(area: Rect, content: impl FnOnce(Rect) -> T, background: Color) -> Self {
        // Content occupies the whole area.
        let mut content = content(area);

        // Always start at the first page.
        let scrollbar = ScrollBar::vertical_right(area, content.page_count(), 0);

        let swipe = Self::make_swipe(area, &scrollbar);
        let pad = Pad::with_background(area, background);
        Self {
            content,
            scrollbar,
            swipe,
            pad,
            fade: None,
        }
    }

    fn make_swipe(area: Rect, scrollbar: &ScrollBar) -> Swipe {
        let mut swipe = Swipe::new(area);
        swipe.allow_up = scrollbar.has_next_page();
        swipe.allow_down = scrollbar.has_previous_page();
        swipe
    }

    fn change_page(&mut self, ctx: &mut EventCtx, page: usize) {
        // Adjust the swipe parameters.
        self.swipe = Self::make_swipe(self.swipe.area, &self.scrollbar);

        // Change the page in the content, make sure it gets completely repainted and
        // clear the background under it.
        self.content.change_page(page);
        self.content.request_complete_repaint(ctx);
        self.pad.clear();

        // Swipe has dimmed the screen, so fade back to normal backlight after the next
        // paint.
        self.fade = Some(theme::BACKLIGHT_NORMAL);
    }
}

impl<T> Component for SwipePage<T>
where
    T: Paginate,
    T: Component,
{
    type Msg = PageMsg<T::Msg, Never>;

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        if let Some(swipe) = self.swipe.event(ctx, event) {
            match swipe {
                SwipeDirection::Up => {
                    // Scroll down, if possible.
                    self.scrollbar.go_to_next_page();
                    self.change_page(ctx, self.scrollbar.active_page);
                    return None;
                }
                SwipeDirection::Down => {
                    // Scroll up, if possible.
                    self.scrollbar.go_to_previous_page();
                    self.change_page(ctx, self.scrollbar.active_page);
                    return None;
                }
                _ => {
                    // Ignore other directions.
                }
            }
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
        if let Some(val) = self.fade.take() {
            // Note that this is blocking and takes some time.
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
    const DOT_INTERVAL: i32 = 12;
    const ARROW_SPACE: i32 = 23;

    const ICON_ACTIVE: &'static [u8] = include_res!("model_tt/res/scroll-active.toif");
    const ICON_INACTIVE: &'static [u8] = include_res!("model_tt/res/scroll-inactive.toif");
    const ICON_UP: &'static [u8] = include_res!("model_tt/res/scroll-up.toif");
    const ICON_DOWN: &'static [u8] = include_res!("model_tt/res/scroll-down.toif");

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
        self.go_to(self.active_page.saturating_add(1).min(self.page_count - 1));
    }

    pub fn go_to_previous_page(&mut self) {
        self.go_to(self.active_page.saturating_sub(1));
    }

    pub fn go_to(&mut self, active_page: usize) {
        self.active_page = active_page;
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
        if self.has_previous_page() {
            display::icon(
                dot - Offset::new(0, Self::ARROW_SPACE),
                Self::ICON_UP,
                theme::FG,
                theme::BG,
            );
        }
        for i in 0..self.page_count {
            let icon = if i == self.active_page {
                Self::ICON_ACTIVE
            } else {
                Self::ICON_INACTIVE
            };
            display::icon(dot, icon, theme::FG, theme::BG);
            dot.y += interval;
        }
        if self.has_next_page() {
            display::icon(
                dot + Offset::new(0, Self::ARROW_SPACE - interval),
                Self::ICON_DOWN,
                theme::FG,
                theme::BG,
            );
        }
    }
}
