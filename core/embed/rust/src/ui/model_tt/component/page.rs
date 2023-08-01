use crate::ui::{
    component::{
        base::ComponentExt,
        paginated::{AuxPageMsg, PageMsg},
        Component, Event, EventCtx, FixedHeightBar, Pad, Paginate,
    },
    display::{self, toif::Icon, Color},
    geometry::{Grid, Insets, Rect},
    model_tt::component::{Button, ButtonContent, ButtonMsg},
};

use super::{
    hold_to_confirm::{handle_hold_event, CancelHold, CancelHoldMsg},
    theme, CancelConfirmMsg, Loader, ScrollBar, Swipe, SwipeDirection,
};

/// Describes behavior of left button.
enum ButtonPrevCancels {
    /// Button never causes `PageMsg::Aux(AuxPageMsg::GoBack)` to be emitted.
    Never,

    /// Button cancels the layout if pressed on the first page. Otherwise it
    /// goes to previous page.
    FirstPage,

    /// Button cancels the layout on any page, except the last where controls
    /// are displayed.
    AnyPage,
}

impl ButtonPrevCancels {
    fn should_cancel(&self, is_first_page: bool) -> bool {
        match self {
            ButtonPrevCancels::Never => false,
            ButtonPrevCancels::FirstPage => is_first_page,
            ButtonPrevCancels::AnyPage => true,
        }
    }

    fn icon(&self, is_first_page: bool) -> Icon {
        match self {
            ButtonPrevCancels::Never => theme::ICON_UP,
            ButtonPrevCancels::FirstPage if is_first_page => theme::ICON_CANCEL,
            ButtonPrevCancels::FirstPage => theme::ICON_UP,
            ButtonPrevCancels::AnyPage => theme::ICON_BACK,
        }
    }
}

pub struct SwipePage<T, U>
where
    U: Component,
{
    content: T,
    controls: U,
    pad: Pad,
    swipe: Swipe,
    scrollbar: ScrollBar,
    button_prev: Button<&'static str>,
    button_next: Button<&'static str>,
    button_prev_cancels: ButtonPrevCancels,
    is_go_back: Option<fn(&U::Msg) -> bool>,
    swipe_left: bool,
    swipe_right: bool,
    fade: Option<u16>,
}

impl<T, U> SwipePage<T, U>
where
    T: Paginate,
    T: Component,
    U: Component,
{
    pub fn new(content: T, controls: U, background: Color) -> Self {
        Self {
            content,
            controls,
            scrollbar: ScrollBar::vertical(),
            swipe: Swipe::new(),
            pad: Pad::with_background(background),
            button_prev: Button::with_icon(theme::ICON_UP).initially_enabled(false),
            button_next: Button::with_icon(theme::ICON_DOWN),
            button_prev_cancels: ButtonPrevCancels::Never,
            is_go_back: None,
            swipe_left: false,
            swipe_right: false,
            fade: None,
        }
    }

    pub fn with_back_button(mut self) -> Self {
        self.button_prev_cancels = ButtonPrevCancels::AnyPage;
        self.button_prev = Button::with_icon(theme::ICON_BACK).initially_enabled(true);
        self
    }

    pub fn with_cancel_on_first_page(mut self) -> Self {
        self.button_prev_cancels = ButtonPrevCancels::FirstPage;
        self.button_prev = Button::with_icon(theme::ICON_CANCEL).initially_enabled(true);
        self
    }

    /// If `controls` message matches the function then we will go page back
    /// instead of propagating the message to parent component.
    pub fn with_go_back(mut self, is_go_back: fn(&U::Msg) -> bool) -> Self {
        self.is_go_back = Some(is_go_back);
        self
    }

    pub fn with_swipe_left(mut self) -> Self {
        self.swipe_left = true;
        self
    }

    pub fn with_swipe_right(mut self) -> Self {
        self.swipe_right = true;
        self
    }

    fn setup_swipe(&mut self) {
        self.swipe.allow_up = self.scrollbar.has_next_page();
        self.swipe.allow_down = self.scrollbar.has_previous_page();
        self.swipe.allow_left = self.swipe_left;
        self.swipe.allow_right = self.swipe_right;
    }

    fn on_page_change(&mut self, ctx: &mut EventCtx) {
        // Adjust the swipe parameters according to the scrollbar.
        self.setup_swipe();

        // Enable/disable prev/next buttons.
        self.button_prev.set_content(
            ctx,
            ButtonContent::Icon(
                self.button_prev_cancels
                    .icon(self.scrollbar.active_page == 0),
            ),
        );
        self.button_prev.enable_if(
            ctx,
            self.scrollbar.has_previous_page()
                || matches!(
                    self.button_prev_cancels,
                    ButtonPrevCancels::FirstPage | ButtonPrevCancels::AnyPage
                ),
        );
        self.button_next
            .enable_if(ctx, self.scrollbar.has_next_page());

        // Change the page in the content, make sure it gets completely repainted and
        // clear the background under it.
        self.content.change_page(self.scrollbar.active_page);
        self.content.request_complete_repaint(ctx);
        self.pad.clear();

        // Swipe has dimmed the screen, so fade back to normal backlight after the next
        // paint.
        self.fade = Some(theme::BACKLIGHT_NORMAL);
    }

    /// Like `place()` but returns area for loader (content + scrollbar) to be
    /// used in SwipeHoldPage.
    fn place_get_content_area(&mut self, bounds: Rect) -> Rect {
        let mut layout = PageLayout::new(bounds);
        self.pad.place(bounds);
        self.swipe.place(bounds);
        self.button_prev.place(layout.button_prev);
        self.button_next.place(layout.button_next);

        let buttons_area = self.controls.place(layout.controls);
        layout.set_buttons_height(buttons_area.height());
        self.scrollbar.place(layout.scrollbar);

        // Layout the content. Try to fit it on a single page first, and reduce the area
        // to make space for a scrollbar if it doesn't fit.
        self.content.place(layout.content_single_page);
        let page_count = {
            let count = self.content.page_count();
            if count > 1 {
                self.content.place(layout.content);
                self.content.page_count() // Make sure to re-count it with the
                                          // new size.
            } else {
                count // Content fits on a single page.
            }
        };

        // Now that we finally have the page count, we can setup the scrollbar and the
        // swiper.
        self.scrollbar.set_count_and_active_page(page_count, 0);
        self.setup_swipe();

        layout.content_single_page.union(layout.scrollbar)
    }
}

impl<T, U> Component for SwipePage<T, U>
where
    T: Paginate,
    T: Component,
    U: Component,
{
    type Msg = PageMsg<T::Msg, U::Msg>;

    fn place(&mut self, bounds: Rect) -> Rect {
        self.place_get_content_area(bounds);
        bounds
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        ctx.set_page_count(self.scrollbar.page_count);
        if let Some(swipe) = self.swipe.event(ctx, event) {
            match swipe {
                SwipeDirection::Up => {
                    // Scroll down, if possible.
                    self.scrollbar.go_to_next_page();
                    self.on_page_change(ctx);
                    return None;
                }
                SwipeDirection::Down => {
                    // Scroll up, if possible.
                    self.scrollbar.go_to_previous_page();
                    self.on_page_change(ctx);
                    return None;
                }
                SwipeDirection::Left if self.swipe_left => {
                    return Some(PageMsg::Aux(AuxPageMsg::SwipeLeft));
                }
                SwipeDirection::Right if self.swipe_right => {
                    return Some(PageMsg::Aux(AuxPageMsg::SwipeRight));
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
            if let Some(msg) = self.controls.event(ctx, event) {
                // Handle the case when one of the controls buttons is configured to go back a
                // page.
                if let Some(f) = self.is_go_back {
                    if f(&msg) {
                        self.scrollbar.go_to_previous_page();
                        self.on_page_change(ctx);
                        return None;
                    }
                }
                return Some(PageMsg::Controls(msg));
            }
        } else {
            if let Some(ButtonMsg::Clicked) = self.button_prev.event(ctx, event) {
                if self
                    .button_prev_cancels
                    .should_cancel(self.scrollbar.active_page == 0)
                {
                    return Some(PageMsg::Aux(AuxPageMsg::GoBack));
                }
                self.scrollbar.go_to_previous_page();
                self.on_page_change(ctx);
                return None;
            }
            if let Some(ButtonMsg::Clicked) = self.button_next.event(ctx, event) {
                self.scrollbar.go_to_next_page();
                self.on_page_change(ctx);
                return None;
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
            self.button_prev.paint();
            self.button_next.paint();
        } else {
            self.controls.paint();
        }
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
        if !self.scrollbar.has_next_page() {
            self.controls.bounds(sink);
        } else {
            self.button_prev.bounds(sink);
            self.button_next.bounds(sink);
        }
    }
}

#[cfg(feature = "ui_debug")]
impl<T, U> crate::trace::Trace for SwipePage<T, U>
where
    T: crate::trace::Trace,
    U: crate::trace::Trace + Component,
{
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.component("SwipePage");
        t.int("active_page", self.scrollbar.active_page as i64);
        t.int("page_count", self.scrollbar.page_count as i64);
        t.child("content", &self.content);
        t.child("controls", &self.controls);
    }
}

pub struct PageLayout {
    /// Content when it fits on single page (no scrollbar).
    pub content_single_page: Rect,
    /// Content when multiple pages.
    pub content: Rect,
    /// Scroll bar when multiple pages.
    pub scrollbar: Rect,
    /// Controls displayed on last page.
    pub controls: Rect,
    pub button_prev: Rect,
    pub button_next: Rect,
}

impl PageLayout {
    const SCROLLBAR_WIDTH: i16 = 8;
    const SCROLLBAR_SPACE: i16 = 5;

    pub fn new(area: Rect) -> Self {
        let (controls, _space) = area.split_right(theme::CONTENT_BORDER);
        let (_space, content) = area.split_left(theme::CONTENT_BORDER);
        let (content_single_page, _space) = content.split_right(theme::CONTENT_BORDER);
        let (content, scrollbar) =
            content.split_right(Self::SCROLLBAR_SPACE + Self::SCROLLBAR_WIDTH);
        let (_space, scrollbar) = scrollbar.split_left(Self::SCROLLBAR_SPACE);

        let (_, one_row_buttons) = area.split_bottom(theme::BUTTON_HEIGHT);
        let grid = Grid::new(one_row_buttons, 1, 2).with_spacing(theme::BUTTON_SPACING);
        let button_prev = grid.row_col(0, 0);
        let button_next = grid.row_col(0, 1);

        Self {
            content_single_page,
            content,
            scrollbar,
            controls,
            button_prev,
            button_next,
        }
    }

    pub fn set_buttons_height(&mut self, height: i16) {
        let buttons_inset = Insets::bottom(height + theme::BUTTON_SPACING);
        self.content_single_page = self.content_single_page.inset(buttons_inset);
        self.content = self.content.inset(buttons_inset);
        self.scrollbar = self.scrollbar.inset(buttons_inset);
    }
}

pub struct SwipeHoldPage<T> {
    inner: SwipePage<T, FixedHeightBar<CancelHold>>,
    loader: Loader,
    pad: Pad,
}

impl<T> SwipeHoldPage<T>
where
    T: Paginate,
    T: Component,
{
    pub fn new(content: T, background: Color) -> Self {
        let buttons = CancelHold::new(theme::button_confirm());
        Self {
            inner: SwipePage::new(content, buttons, background).with_cancel_on_first_page(),
            loader: Loader::new(),
            pad: Pad::with_background(background),
        }
    }

    pub fn with_danger(content: T, background: Color) -> Self {
        let buttons = CancelHold::new(theme::button_danger());
        Self {
            inner: SwipePage::new(content, buttons, background).with_cancel_on_first_page(),
            loader: Loader::new(),
            pad: Pad::with_background(background),
        }
    }

    pub fn without_cancel(content: T, background: Color) -> Self {
        let buttons = CancelHold::without_cancel();
        Self {
            inner: SwipePage::new(content, buttons, background),
            loader: Loader::new(),
            pad: Pad::with_background(background),
        }
    }

    pub fn with_cancel_arrow(content: T, background: Color) -> Self {
        let buttons = CancelHold::with_cancel_arrow();
        Self {
            inner: SwipePage::new(content, buttons, background),
            loader: Loader::new(),
            pad: Pad::with_background(background),
        }
    }

    pub fn with_swipe_left(mut self) -> Self {
        self.inner = self.inner.with_swipe_left();
        self
    }
}

impl<T> Component for SwipeHoldPage<T>
where
    T: Paginate,
    T: Component,
{
    type Msg = PageMsg<T::Msg, CancelConfirmMsg>;

    fn place(&mut self, bounds: Rect) -> Rect {
        let content_area = self.inner.place_get_content_area(bounds);
        self.loader.place(content_area);
        self.pad.place(content_area);
        bounds
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        let msg = self.inner.event(ctx, event);
        let button_msg = match msg {
            Some(PageMsg::Content(c)) => return Some(PageMsg::Content(c)),
            Some(PageMsg::Controls(CancelHoldMsg::Cancelled)) => {
                return Some(PageMsg::Controls(CancelConfirmMsg::Cancelled))
            }
            Some(PageMsg::Controls(CancelHoldMsg::HoldButton(b))) => Some(b),
            Some(PageMsg::Aux(a)) => return Some(PageMsg::Aux(a)),
            _ => None,
        };
        if handle_hold_event(
            ctx,
            event,
            button_msg,
            &mut self.loader,
            &mut self.pad,
            &mut self.inner.content,
        ) {
            return Some(PageMsg::Controls(CancelConfirmMsg::Confirmed));
        }
        if self.inner.pad.will_paint().is_some() {
            self.inner.controls.request_complete_repaint(ctx);
        }
        None
    }

    fn paint(&mut self) {
        self.pad.paint();
        self.inner.pad.paint();
        if self.loader.is_animating() {
            self.loader.paint()
        } else {
            self.inner.content.paint();
            if self.inner.scrollbar.has_pages() {
                self.inner.scrollbar.paint();
            }
        }
        if self.inner.scrollbar.has_next_page() {
            self.inner.button_prev.paint();
            self.inner.button_next.paint();
        } else {
            self.inner.controls.paint();
        }
        if let Some(val) = self.inner.fade.take() {
            // Note that this is blocking and takes some time.
            display::fade_backlight(val);
        }
    }

    #[cfg(feature = "ui_bounds")]
    fn bounds(&self, sink: &mut dyn FnMut(Rect)) {
        self.loader.bounds(sink);
        self.inner.bounds(sink);
    }
}

#[cfg(feature = "ui_debug")]
impl<T> crate::trace::Trace for SwipeHoldPage<T>
where
    T: crate::trace::Trace,
{
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        self.inner.trace(t)
    }
}

#[cfg(test)]
mod tests {
    use serde_json;

    use crate::{
        strutil::SkipPrefix,
        trace::tests::trace,
        ui::{
            component::{
                text::paragraphs::{Paragraph, Paragraphs},
                Empty,
            },
            event::TouchEvent,
            geometry::Point,
            model_tt::{component::Button, constant, theme},
        },
    };

    use super::*;

    const SCREEN: Rect = constant::screen().inset(theme::borders());

    impl SkipPrefix for &str {
        fn skip_prefix(&self, chars: usize) -> Self {
            &self[chars..]
        }
    }

    fn swipe(component: &mut impl Component, points: &[(i16, i16)]) {
        let last = points.len().saturating_sub(1);
        let mut first = true;
        let mut ctx = EventCtx::new();
        for (i, &(x, y)) in points.iter().enumerate() {
            let p = Point::new(x, y);
            let ev = if first {
                TouchEvent::TouchStart(p)
            } else if i == last {
                TouchEvent::TouchEnd(p)
            } else {
                TouchEvent::TouchMove(p)
            };
            component.event(&mut ctx, Event::Touch(ev));
            ctx.clear();
            first = false;
        }
    }

    fn swipe_up(component: &mut impl Component) {
        swipe(component, &[(20, 100), (20, 60), (20, 20)])
    }

    fn swipe_down(component: &mut impl Component) {
        swipe(component, &[(20, 20), (20, 60), (20, 100)])
    }

    #[test]
    fn paragraphs_empty() {
        let mut page = SwipePage::new(
            Paragraphs::<[Paragraph<&'static str>; 0]>::new([]),
            Empty,
            theme::BG,
        );
        page.place(SCREEN);

        let expected = serde_json::json!({
            "component": "SwipePage",
            "active_page": 0,
            "page_count": 1,
            "content": {
                "component": "Paragraphs",
                "paragraphs": [],
            },
            "controls": {
                "component": "Empty",
            },
        });

        assert_eq!(trace(&page), expected);
        swipe_up(&mut page);
        assert_eq!(trace(&page), expected);
        swipe_down(&mut page);
        assert_eq!(trace(&page), expected);
    }

    #[test]
    fn paragraphs_single() {
        let mut page = SwipePage::new(
            Paragraphs::new([
                Paragraph::new(
                    &theme::TEXT_NORMAL,
                    "This is the first paragraph and it should fit on the screen entirely.",
                ),
                Paragraph::new(
                    &theme::TEXT_BOLD,
                    "Second, bold, paragraph should also fit on the screen whole I think.",
                ),
            ]),
            Empty,
            theme::BG,
        );
        page.place(SCREEN);

        let expected = serde_json::json!({
            "component": "SwipePage",
            "active_page": 0,
            "page_count": 1,
            "content": {
                "component": "Paragraphs",
                "paragraphs": [
                    ["This is the first", "\n", "paragraph and it should", "\n", "fit on the screen", "\n", "entirely."],
                    ["Second, bold, paragraph", "\n", "should also fit on the", "\n", "screen whole I think."],
                ],
            },
            "controls": {
                "component": "Empty",
            },
        });

        assert_eq!(trace(&page), expected);
        swipe_up(&mut page);
        assert_eq!(trace(&page), expected);
        swipe_down(&mut page);
        assert_eq!(trace(&page), expected);
    }

    #[test]
    fn paragraphs_one_long() {
        let mut page = SwipePage::new(
            Paragraphs::new(
                Paragraph::new(
                    &theme::TEXT_BOLD,
                    "This is somewhat long paragraph that goes on and on and on and on and on and will definitely not fit on just a single screen. You have to swipe a bit to see all the text it contains I guess. There's just so much letters in it.",
                )
            ),
            theme::button_bar(Button::with_text("NO")),
            theme::BG,
        );
        page.place(SCREEN);

        let first_page = serde_json::json!({
            "component": "SwipePage",
            "active_page": 0,
            "page_count": 2,
            "content": {
                "component": "Paragraphs",
                "paragraphs": [
                    [
                        "This is somewhat long", "\n",
                        "paragraph that goes on", "\n",
                        "and on and on and on and", "\n",
                        "on and will definitely not", "\n",
                        "fit on just a single", "\n",
                        "screen. You have to", "\n",
                        "swipe a bit to see all the", "\n",
                        "text it contains I guess.", "...",
                    ],
                ],
            },
            "controls": {
                "component": "FixedHeightBar",
                "inner": {
                    "component": "Button",
                    "text": "NO",
                },
            },
        });
        let second_page = serde_json::json!({
            "component": "SwipePage",
            "active_page": 1,
            "page_count": 2,
            "content": {
                "component": "Paragraphs",
                "paragraphs": [
                    ["There's just so much", "\n", "letters in it."],
                ],
            },
            "controls": {
                "component": "FixedHeightBar",
                "inner": {
                    "component": "Button",
                    "text": "NO",
                },
            },
        });

        assert_eq!(trace(&page), first_page);
        swipe_down(&mut page);
        assert_eq!(trace(&page), first_page);
        swipe_up(&mut page);
        assert_eq!(trace(&page), second_page);
        swipe_up(&mut page);
        assert_eq!(trace(&page), second_page);
        swipe_down(&mut page);
        assert_eq!(trace(&page), first_page);
    }

    #[test]
    fn paragraphs_three_long() {
        let mut page = SwipePage::new(
            Paragraphs::new([
                Paragraph::new(
                    &theme::TEXT_BOLD,
                    "This paragraph is using a bold font. It doesn't need to be all that long.",
                ),
                Paragraph::new(
                    &theme::TEXT_MONO,
                    "And this one is using MONO. Monospace is nice for numbers, they have the same width and can be scanned quickly. Even if they span several pages or something.",
                ),
                Paragraph::new(
                    &theme::TEXT_BOLD,
                    "Let's add another one for a good measure. This one should overflow all the way to the third page with a bit of luck.",
                ),
            ]),
            theme::button_bar(Button::with_text("IDK")),
            theme::BG,
        );
        page.place(SCREEN);

        let first_page = serde_json::json!({
            "component": "SwipePage",
            "active_page": 0,
            "page_count": 3,
            "content": {
                "component": "Paragraphs",
                "paragraphs": [
                    [
                        "This paragraph is using a", "\n",
                        "bold font. It doesn't need", "\n",
                        "to be all that long.",
                    ],
                    [
                        "And this one is u", "\n",
                        "sing MONO. Monosp", "\n",
                        "ace is nice for n", "\n",
                        "umbers, they", "...",
                    ],
                ],
            },
            "controls": {
                "component": "FixedHeightBar",
                "inner": {
                    "component": "Button",
                    "text": "IDK",
                },
            },
        });
        let second_page = serde_json::json!({
            "component": "SwipePage",
            "active_page": 1,
            "page_count": 3,
            "content": {
                "component": "Paragraphs",
                "paragraphs": [
                    [
                        "...", "have the same", "\n",
                        "width and can be", "\n",
                        "scanned quickly.", "\n",
                        "Even if they span", "\n",
                        "several pages or", "\n",
                        "something.",
                    ],
                    [
                        "Let's add another one", "...",
                    ],
                ],
            },
            "controls": {
                "component": "FixedHeightBar",
                "inner": {
                    "component": "Button",
                    "text": "IDK",
                },
            },
        });
        let third_page = serde_json::json!({
            "component": "SwipePage",
            "active_page": 2,
            "page_count": 3,
            "content": {
                "component": "Paragraphs",
                "paragraphs": [
                    [
                        "for a good measure. This", "\n",
                        "one should overflow all", "\n",
                        "the way to the third page", "\n",
                        "with a bit of luck.",
                    ],
                ],
            },
            "controls": {
                "component": "FixedHeightBar",
                "inner": {
                    "component": "Button",
                    "text": "IDK",
                },
            },
        });

        assert_eq!(trace(&page), first_page);
        swipe_down(&mut page);
        assert_eq!(trace(&page), first_page);
        swipe_up(&mut page);
        assert_eq!(trace(&page), second_page);
        swipe_up(&mut page);
        assert_eq!(trace(&page), third_page);
        swipe_up(&mut page);
        assert_eq!(trace(&page), third_page);
        swipe_down(&mut page);
        assert_eq!(trace(&page), second_page);
        swipe_down(&mut page);
        assert_eq!(trace(&page), first_page);
        swipe_down(&mut page);
        assert_eq!(trace(&page), first_page);
    }

    #[test]
    fn paragraphs_hard_break() {
        let mut page = SwipePage::new(
            Paragraphs::new([
                Paragraph::new(&theme::TEXT_NORMAL, "Short one.").break_after(),
                Paragraph::new(&theme::TEXT_NORMAL, "Short two.").break_after(),
                Paragraph::new(&theme::TEXT_NORMAL, "Short three.").break_after(),
            ]),
            theme::button_bar(Empty),
            theme::BG,
        );
        page.place(SCREEN);

        let first_page = serde_json::json!({
            "component": "SwipePage",
            "active_page": 0,
            "page_count": 3,
            "content": {
                "component": "Paragraphs",
                "paragraphs": [
                    [
                        "Short one.",
                    ],
                ],
            },
            "controls": {
                "component": "FixedHeightBar",
                "inner": {
                    "component": "Empty",
                },
            },
        });
        let second_page = serde_json::json!({
            "component": "SwipePage",
            "active_page": 1,
            "page_count": 3,
            "content": {
                "component": "Paragraphs",
                "paragraphs": [
                    [
                        "Short two.",
                    ],
                ],
            },
            "controls": {
                "component": "FixedHeightBar",
                "inner": {
                    "component": "Empty",
                },
            },
        });
        let third_page = serde_json::json!({
            "component": "SwipePage",
            "active_page": 2,
            "page_count": 3,
            "content": {
                "component": "Paragraphs",
                "paragraphs": [
                    [
                        "Short three.",
                    ],
                ],
            },
            "controls": {
                "component": "FixedHeightBar",
                "inner": {
                    "component": "Empty",
                },
            },
        });

        assert_eq!(trace(&page), first_page);
        swipe_up(&mut page);
        assert_eq!(trace(&page), second_page);
        swipe_up(&mut page);
        assert_eq!(trace(&page), third_page);
        swipe_up(&mut page);
        assert_eq!(trace(&page), third_page);
    }
}
