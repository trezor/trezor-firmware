use crate::ui::{
    component::{base::ComponentExt, Component, Event, EventCtx, Pad, PageMsg, Paginate},
    display::{self, Color},
    geometry::{Axis, Insets, Rect},
    shape::Renderer,
};

use super::{theme, ScrollBar, Swipe, SwipeDirection};
use core::cell::Cell;

const SCROLLBAR_HEIGHT: i16 = 18;
const SCROLLBAR_BORDER: i16 = 4;

pub struct SimplePage<T> {
    content: T,
    pad: Pad,
    swipe: Swipe,
    scrollbar: ScrollBar,
    axis: Axis,
    swipe_right_to_go_back: bool,
    fade: Cell<Option<u8>>,
}

impl<T> SimplePage<T>
where
    T: Paginate,
    T: Component,
{
    pub fn new(content: T, axis: Axis, background: Color) -> Self {
        Self {
            content,
            swipe: Swipe::new(),
            pad: Pad::with_background(background),
            scrollbar: ScrollBar::new(axis),
            axis,
            swipe_right_to_go_back: false,
            fade: Cell::new(None),
        }
    }

    pub fn horizontal(content: T, background: Color) -> Self {
        Self::new(content, Axis::Horizontal, background)
    }

    pub fn vertical(content: T, background: Color) -> Self {
        Self::new(content, Axis::Vertical, background)
    }

    pub fn with_swipe_right_to_go_back(mut self) -> Self {
        self.swipe_right_to_go_back = true;
        self
    }

    pub fn inner(&self) -> &T {
        &self.content
    }

    fn setup_swipe(&mut self) {
        if self.is_horizontal() {
            self.swipe.allow_left = self.scrollbar.has_next_page();
            self.swipe.allow_right =
                self.scrollbar.has_previous_page() || self.swipe_right_to_go_back;
        } else {
            self.swipe.allow_up = self.scrollbar.has_next_page();
            self.swipe.allow_down = self.scrollbar.has_previous_page();
            self.swipe.allow_right = self.swipe_right_to_go_back;
        }
    }

    fn change_page(&mut self, ctx: &mut EventCtx, step: isize) {
        // Advance scrollbar.
        self.scrollbar.go_to_relative(step);
        // Adjust the swipe parameters according to the scrollbar.
        self.setup_swipe();

        // Change the page in the content, make sure it gets completely repainted and
        // clear the background under it.
        self.content.change_page(self.scrollbar.active_page);
        self.content.request_complete_repaint(ctx);
        self.pad.clear();

        // Swipe has dimmed the screen, so fade back to normal backlight after the next
        // paint.
        self.fade
            .set(Some(theme::backlight::get_backlight_normal()));
    }

    fn is_horizontal(&self) -> bool {
        matches!(self.axis, Axis::Horizontal)
    }
}

impl<T> Component for SimplePage<T>
where
    T: Paginate,
    T: Component,
{
    type Msg = PageMsg<T::Msg>;

    fn place(&mut self, bounds: Rect) -> Rect {
        self.swipe.place(bounds);

        let (content, scrollbar) = if self.is_horizontal() {
            bounds.split_bottom(SCROLLBAR_HEIGHT + SCROLLBAR_BORDER)
        } else {
            bounds.split_right(SCROLLBAR_HEIGHT + SCROLLBAR_BORDER)
        };

        self.content.place(bounds);
        if self.content.page_count() > 1 {
            self.pad.place(content);
            self.content.place(content);
        } else {
            self.pad.place(bounds);
        }

        if self.is_horizontal() {
            self.scrollbar
                .place(scrollbar.inset(Insets::bottom(SCROLLBAR_BORDER)));
        } else {
            self.scrollbar
                .place(scrollbar.inset(Insets::right(SCROLLBAR_BORDER)));
        }

        self.scrollbar
            .set_count_and_active_page(self.content.page_count(), 0);
        self.setup_swipe();

        bounds
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        ctx.set_page_count(self.scrollbar.page_count);
        if let Some(swipe) = self.swipe.event(ctx, event) {
            match (swipe, self.axis) {
                (SwipeDirection::Left, Axis::Horizontal) | (SwipeDirection::Up, Axis::Vertical) => {
                    self.change_page(ctx, 1);
                    return None;
                }
                (SwipeDirection::Right, _)
                    if self.swipe_right_to_go_back && self.scrollbar.active_page == 0 =>
                {
                    return Some(PageMsg::Cancelled);
                }
                (SwipeDirection::Right, Axis::Horizontal)
                | (SwipeDirection::Down, Axis::Vertical) => {
                    self.change_page(ctx, -1);
                    return None;
                }
                _ => {
                    // Ignore other directions.
                }
            }
        }
        self.content.event(ctx, event).map(PageMsg::Content)
    }

    fn paint(&mut self) {
        self.pad.paint();
        self.content.paint();
        if self.scrollbar.has_pages() {
            self.scrollbar.paint();
        }
        if let Some(val) = self.fade.take() {
            // Note that this is blocking and takes some time.
            display::fade_backlight(val);
        }
    }

    fn render<'s>(&'s self, target: &mut impl Renderer<'s>) {
        self.pad.render(target);
        self.content.render(target);
        if self.scrollbar.has_pages() {
            self.scrollbar.render(target);
        }
        if let Some(val) = self.fade.take() {
            // Note that this is blocking and takes some time.
            display::fade_backlight(val);
        }
    }
}

#[cfg(feature = "ui_debug")]
impl<T> crate::trace::Trace for SimplePage<T>
where
    T: crate::trace::Trace,
{
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.component("SimplePage");
        t.int("active_page", self.scrollbar.active_page as i64);
        t.int("page_count", self.scrollbar.page_count as i64);
        t.child("content", &self.content);
    }
}
