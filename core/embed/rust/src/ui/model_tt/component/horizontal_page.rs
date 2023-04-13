use crate::ui::{
    component::{
        base::ComponentExt, AuxPageMsg, Component, Event, EventCtx, Never, Pad, PageMsg, Paginate,
    },
    display::{self, Color},
    geometry::{Insets, Rect},
};

use super::{theme, ScrollBar, Swipe, SwipeDirection};

const SCROLLBAR_HEIGHT: i16 = 18;
const SCROLLBAR_BORDER: i16 = 4;

pub struct HorizontalPage<T> {
    content: T,
    pad: Pad,
    swipe: Swipe,
    scrollbar: ScrollBar,
    swipe_right_to_go_back: bool,
    fade: Option<u16>,
}

impl<T> HorizontalPage<T>
where
    T: Paginate,
    T: Component,
{
    pub fn new(content: T, background: Color) -> Self {
        Self {
            content,
            swipe: Swipe::new(),
            pad: Pad::with_background(background),
            scrollbar: ScrollBar::horizontal(),
            swipe_right_to_go_back: false,
            fade: None,
        }
    }

    pub fn with_swipe_right_to_go_back(mut self) -> Self {
        self.swipe_right_to_go_back = true;
        self
    }

    pub fn inner(&self) -> &T {
        &self.content
    }

    fn setup_swipe(&mut self) {
        self.swipe.allow_left = self.scrollbar.has_next_page();
        self.swipe.allow_right = self.scrollbar.has_previous_page() || self.swipe_right_to_go_back;
    }

    fn on_page_change(&mut self, ctx: &mut EventCtx) {
        // Adjust the swipe parameters according to the scrollbar.
        self.setup_swipe();

        // Change the page in the content, make sure it gets completely repainted and
        // clear the background under it.
        self.content.change_page(self.scrollbar.active_page);
        self.content.request_complete_repaint(ctx);
        self.pad.clear();

        // Swipe has dimmed the screen, so fade back to normal backlight after the next
        // paint.
        self.fade = Some(theme::BACKLIGHT_NORMAL);
    }
}

impl<T> Component for HorizontalPage<T>
where
    T: Paginate,
    T: Component,
{
    type Msg = PageMsg<T::Msg, Never>;

    fn place(&mut self, bounds: Rect) -> Rect {
        self.swipe.place(bounds);

        let (content, scrollbar) = bounds.split_bottom(SCROLLBAR_HEIGHT + SCROLLBAR_BORDER);
        self.pad.place(content);
        self.content.place(content);
        self.scrollbar
            .place(scrollbar.inset(Insets::bottom(SCROLLBAR_BORDER)));

        self.scrollbar
            .set_count_and_active_page(self.content.page_count(), 0);
        self.setup_swipe();

        bounds
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        ctx.set_page_count(self.scrollbar.page_count);
        if let Some(swipe) = self.swipe.event(ctx, event) {
            match swipe {
                SwipeDirection::Left => {
                    self.scrollbar.go_to_next_page();
                    self.on_page_change(ctx);
                    return None;
                }
                SwipeDirection::Right => {
                    if self.swipe_right_to_go_back && self.scrollbar.active_page == 0 {
                        return Some(PageMsg::Aux(AuxPageMsg::GoBack));
                    }
                    self.scrollbar.go_to_previous_page();
                    self.on_page_change(ctx);
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
        self.scrollbar.paint();
        if let Some(val) = self.fade.take() {
            // Note that this is blocking and takes some time.
            display::fade_backlight(val);
        }
    }

    #[cfg(feature = "ui_bounds")]
    fn bounds(&self, sink: &mut dyn FnMut(Rect)) {
        sink(self.pad.area);
        self.scrollbar.bounds(sink);
        self.content.bounds(sink);
    }
}

#[cfg(feature = "ui_debug")]
impl<T> crate::trace::Trace for HorizontalPage<T>
where
    T: crate::trace::Trace,
{
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.component("HorizontalPage");
        t.int("active_page", self.scrollbar.active_page as i64);
        t.int("page_count", self.scrollbar.page_count as i64);
        t.child("content", &self.content);
    }
}
