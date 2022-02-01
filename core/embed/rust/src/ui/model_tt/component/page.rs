use crate::ui::{
    component::{
        base::ComponentExt, paginated::PageMsg, Component, Event, EventCtx, Never, Pad, Paginate,
    },
    display::{self, Color},
    geometry::{Dimensions, LinearLayout, Offset, Rect},
};

use super::{theme, Button, Swipe, SwipeDirection};

pub struct SwipePage<T, U> {
    content: T,
    buttons: U,
    pad: Pad,
    swipe: Swipe,
    scrollbar: ScrollBar,
    fade: Option<i32>,
}

impl<T, U> SwipePage<T, U>
where
    T: Paginate,
    T: Component,
    T: Dimensions,
    U: Component,
{
    pub fn new(
        area: Rect,
        background: Color,
        content: impl FnOnce(Rect) -> T,
        controls: impl FnOnce(Rect) -> U,
    ) -> Self {
        let layout = PageLayout::new(area);
        let mut content = Self::make_content(&layout, content);

        // Always start at the first page.
        let scrollbar = ScrollBar::vertical_right(layout.scrollbar, content.page_count(), 0);

        let swipe = Self::make_swipe(area, &scrollbar);
        let pad = Pad::with_background(area, background);
        Self {
            content,
            buttons: controls(layout.buttons),
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

    fn make_content(layout: &PageLayout, content: impl FnOnce(Rect) -> T) -> T {
        // Check if content fits on single page.
        let mut content = content(layout.content_single_page);
        if content.page_count() > 1 {
            // Reduce area to make space for scrollbar if it doesn't fit.
            content.set_area(layout.content);
        }
        content.change_page(0);
        content
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

    fn paint_hint(&mut self) {
        display::text_center(
            self.pad.area.bottom_center() - Offset::y(3),
            b"SWIPE TO CONTINUE",
            theme::FONT_BOLD, // FIXME: Figma has this as 14px but bold is 16px
            theme::GREY_LIGHT,
            theme::BG,
        );
    }
}

impl<T, U> Component for SwipePage<T, U>
where
    T: Paginate,
    T: Component,
    T: Dimensions,
    U: Component,
{
    type Msg = PageMsg<T::Msg, U::Msg>;

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
        if !self.scrollbar.has_next_page() {
            if let Some(msg) = self.buttons.event(ctx, event) {
                return Some(PageMsg::Controls(msg));
            }
        }
        None
    }

    fn paint(&mut self) {
        self.pad.paint();
        self.content.paint();
        if self.scrollbar.has_pages() {
            self.scrollbar.paint();
        }
        if self.scrollbar.has_next_page() {
            self.paint_hint();
        } else {
            self.buttons.paint();
        }
        if let Some(val) = self.fade.take() {
            // Note that this is blocking and takes some time.
            display::fade_backlight(val);
        }
    }

    fn bounds(&self, sink: &mut dyn FnMut(Rect)) {
        sink(self.scrollbar.area);
        sink(self.pad.area);
        self.content.bounds(sink);
        if !self.scrollbar.has_next_page() {
            self.buttons.bounds(sink);
        }
    }
}

#[cfg(feature = "ui_debug")]
impl<T, U> crate::trace::Trace for SwipePage<T, U>
where
    T: crate::trace::Trace,
    U: crate::trace::Trace,
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
    const DOT_SIZE: i32 = 6;
    /// Edge to edge.
    const DOT_INTERVAL: i32 = 6;
    /// Edge of last dot to center of arrow icon.
    const ARROW_SPACE: i32 = 26;

    const ICON_ACTIVE: &'static [u8] = include_res!("model_tt/res/scroll-active.toif");
    const ICON_INACTIVE: &'static [u8] = include_res!("model_tt/res/scroll-inactive.toif");
    const ICON_UP: &'static [u8] = include_res!("model_tt/res/scroll-up.toif");
    const ICON_DOWN: &'static [u8] = include_res!("model_tt/res/scroll-down.toif");

    pub fn vertical_right(area: Rect, page_count: usize, active_page: usize) -> Self {
        Self {
            area,
            page_count,
            active_page,
        }
    }

    pub fn has_pages(&self) -> bool {
        self.page_count > 1
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
        let layout = LinearLayout::vertical()
            .align_at_center()
            .with_spacing(Self::DOT_INTERVAL);

        let mut i = 0;
        let mut top = None;
        let mut display_icon = |top_left| {
            let icon = if i == self.active_page {
                Self::ICON_ACTIVE
            } else {
                Self::ICON_INACTIVE
            };
            display::icon_top_left(top_left, icon, theme::FG, theme::BG);
            i += 1;
            top.get_or_insert(top_left.x);
        };

        layout.arrange_uniform(
            self.area,
            self.page_count,
            Offset::new(Self::DOT_SIZE, Self::DOT_SIZE),
            &mut display_icon,
        );

        let arrow_distance = self.area.center().x - top.unwrap_or(0) + Self::ARROW_SPACE;
        if self.has_previous_page() {
            display::icon(
                self.area.center() - Offset::y(arrow_distance),
                Self::ICON_UP,
                theme::FG,
                theme::BG,
            );
        }
        if self.has_next_page() {
            display::icon(
                self.area.center() + Offset::y(arrow_distance),
                Self::ICON_DOWN,
                theme::FG,
                theme::BG,
            );
        }
    }
}

pub struct PageLayout {
    pub content_single_page: Rect,
    pub content: Rect,
    pub scrollbar: Rect,
    pub buttons: Rect,
}

impl PageLayout {
    const BUTTON_SPACE: i32 = 6;
    const SCROLLBAR_WIDTH: i32 = 10;
    const SCROLLBAR_SPACE: i32 = 10;

    pub fn new(area: Rect) -> Self {
        let (content, buttons) = area.split_bottom(Button::<&str>::HEIGHT);
        let (content, _space) = content.split_bottom(Self::BUTTON_SPACE);
        let (buttons, _space) = buttons.split_right(theme::CONTENT_BORDER);
        let (_space, content) = content.split_left(theme::CONTENT_BORDER);
        let (content_single_page, _space) = content.split_right(theme::CONTENT_BORDER);
        let (content, scrollbar) =
            content.split_right(Self::SCROLLBAR_SPACE + Self::SCROLLBAR_WIDTH);
        let (_space, scrollbar) = scrollbar.split_left(Self::SCROLLBAR_SPACE);

        Self {
            content_single_page,
            content,
            scrollbar,
            buttons,
        }
    }
}
