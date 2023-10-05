use crate::{
    time::Instant,
    ui::{
        component::{paginated::PageMsg, Component, ComponentExt, Event, EventCtx, Pad, Paginate},
        constant,
        display::{self, Color},
        geometry::{Insets, Rect},
        util::animation_disabled,
    },
};

use super::{
    theme, Button, ButtonContent, ButtonMsg, ButtonStyleSheet, Loader, LoaderMsg, ScrollBar, Swipe,
    SwipeDirection,
};

/// Allows pagination of inner component. Shows scroll bar, confirm & cancel
/// buttons. Optionally handles hold-to-confirm with loader.
pub struct ButtonPage<T, U> {
    /// Inner component.
    content: T,
    /// Cleared when page changes.
    pad: Pad,
    /// Swipe controller.
    swipe: Swipe,
    scrollbar: ScrollBar,
    /// Hold-to-confirm mode whenever this is `Some(loader)`.
    loader: Option<Loader>,
    button_cancel: Option<Button<U>>,
    button_confirm: Button<U>,
    button_prev: Button<&'static str>,
    button_next: Button<&'static str>,
    /// Show cancel button instead of back button.
    cancel_from_any_page: bool,
    /// Whether to pass-through left swipe to parent component.
    swipe_left: bool,
    /// Whether to pass-through right swipe to parent component.
    swipe_right: bool,
    /// Fade to given backlight level on next paint().
    fade: Option<u16>,
}

impl<T, U> ButtonPage<T, U>
where
    T: Paginate,
    T: Component,
    U: AsRef<str> + From<&'static str>,
{
    pub fn new(content: T, background: Color) -> Self {
        Self {
            content,
            pad: Pad::with_background(background),
            swipe: Swipe::new(),
            scrollbar: ScrollBar::vertical(),
            loader: None,
            button_cancel: Some(Button::with_icon(theme::ICON_CANCEL)),
            button_confirm: Button::with_icon(theme::ICON_CONFIRM).styled(theme::button_confirm()),
            button_prev: Button::with_icon(theme::ICON_UP).initially_enabled(false),
            button_next: Button::with_icon(theme::ICON_DOWN),
            cancel_from_any_page: false,
            swipe_left: false,
            swipe_right: false,
            fade: None,
        }
    }

    pub fn without_cancel(mut self) -> Self {
        self.button_cancel = None;
        self
    }

    pub fn with_cancel_confirm(mut self, left: Option<U>, right: Option<U>) -> Self {
        let cancel = match left {
            Some(verb) => match verb.as_ref() {
                "^" => Button::with_icon(theme::ICON_UP),
                "<" => Button::with_icon(theme::ICON_BACK),
                _ => Button::with_text(verb),
            },
            _ => Button::with_icon(theme::ICON_CANCEL),
        };
        let confirm = match right {
            Some(verb) => Button::with_text(verb).styled(theme::button_confirm()),
            _ => Button::with_icon(theme::ICON_CONFIRM).styled(theme::button_confirm()),
        };
        self.button_cancel = Some(cancel);
        self.button_confirm = confirm;
        self
    }

    pub fn with_hold(mut self) -> Self {
        self.button_confirm =
            Button::with_text("HOLD TO CONFIRM".into()).styled(theme::button_confirm());
        self.loader = Some(Loader::new());
        self
    }

    pub fn with_back_button(mut self) -> Self {
        self.cancel_from_any_page = true;
        self.button_prev = Button::with_icon(theme::ICON_BACK).initially_enabled(false);
        self.button_cancel = Some(Button::with_icon(theme::ICON_BACK));
        self
    }

    pub fn with_cancel_arrow(mut self) -> Self {
        self.button_cancel = Some(Button::with_icon(theme::ICON_UP));
        self
    }

    pub fn with_confirm_style(mut self, style: ButtonStyleSheet) -> Self {
        self.button_confirm = self.button_confirm.styled(style);
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

    fn change_page(&mut self, ctx: &mut EventCtx, step: isize) {
        // Advance scrollbar.
        self.scrollbar.go_to_relative(step);

        // Adjust the swipe parameters according to the scrollbar.
        self.setup_swipe();

        // Enable/disable prev button.
        self.button_prev
            .enable_if(ctx, self.scrollbar.has_previous_page());

        // Change the page in the content, make sure it gets completely repainted and
        // clear the background under it.
        self.content.change_page(self.scrollbar.active_page);
        self.content.request_complete_repaint(ctx);
        self.pad.clear();

        // Swipe has dimmed the screen, so fade back to normal backlight after the next
        // paint.
        self.fade = Some(theme::BACKLIGHT_NORMAL);
    }

    fn is_cancel_visible(&self) -> bool {
        self.cancel_from_any_page || !self.scrollbar.has_previous_page()
    }

    /// Area for drawing loader (and black rectangle behind it). Can be outside
    /// bounds as we repaint entire UI tree after hiding the loader.
    const fn loader_area() -> Rect {
        constant::screen()
            .inset(theme::borders())
            .inset(Insets::bottom(theme::BUTTON_HEIGHT + theme::BUTTON_SPACING))
    }

    fn handle_swipe(
        &mut self,
        ctx: &mut EventCtx,
        event: Event,
    ) -> HandleResult<<Self as Component>::Msg> {
        if let Some(swipe) = self.swipe.event(ctx, event) {
            match swipe {
                SwipeDirection::Up => {
                    // Scroll down, if possible.
                    return HandleResult::NextPage;
                }
                SwipeDirection::Down => {
                    // Scroll up, if possible.
                    return HandleResult::PrevPage;
                }
                SwipeDirection::Left if self.swipe_left => {
                    return HandleResult::Return(PageMsg::SwipeLeft);
                }
                SwipeDirection::Right if self.swipe_right => {
                    return HandleResult::Return(PageMsg::SwipeRight);
                }
                _ => {
                    // Ignore other directions.
                }
            }
        }

        HandleResult::Continue
    }

    fn handle_button(
        &mut self,
        ctx: &mut EventCtx,
        event: Event,
    ) -> HandleResult<(Option<<Self as Component>::Msg>, Option<ButtonMsg>)> {
        if self.scrollbar.has_next_page() {
            if let Some(ButtonMsg::Clicked) = self.button_next.event(ctx, event) {
                return HandleResult::NextPage;
            }
        } else {
            let result = self.button_confirm.event(ctx, event);
            match result {
                Some(ButtonMsg::Clicked) => {
                    return HandleResult::Return((Some(PageMsg::Confirmed), result))
                }
                Some(_) => return HandleResult::Return((None, result)),
                None => {}
            }
        }
        if self.is_cancel_visible() {
            if let Some(ButtonMsg::Clicked) = self.button_cancel.event(ctx, event) {
                return HandleResult::Return((Some(PageMsg::Cancelled), None));
            }
        } else if let Some(ButtonMsg::Clicked) = self.button_prev.event(ctx, event) {
            return HandleResult::PrevPage;
        }

        HandleResult::Continue
    }

    fn handle_hold(
        &mut self,
        ctx: &mut EventCtx,
        event: Event,
        button_msg: &Option<ButtonMsg>,
    ) -> HandleResult<<Self as Component>::Msg> {
        let Some(loader) = &mut self.loader else {
            return HandleResult::Continue;
        };
        let now = Instant::now();

        if let Some(LoaderMsg::ShrunkCompletely) = loader.event(ctx, event) {
            // Switch it to the initial state, so we stop painting it.
            loader.reset();
            // Re-draw the whole content tree.
            self.content.request_complete_repaint(ctx);
            // Loader overpainted our bounds, repaint entire screen from scratch.
            ctx.request_repaint_root()
            // This can be a result of an animation frame event, we should take
            // care to not short-circuit here and deliver the event to the
            // content as well.
        }
        match button_msg {
            Some(ButtonMsg::Pressed) => {
                loader.start_growing(ctx, now);
                loader.pad.clear(); // Clear the remnants of the content.
            }
            Some(ButtonMsg::Released) => {
                loader.start_shrinking(ctx, now);
            }
            Some(ButtonMsg::Clicked) => {
                if loader.is_completely_grown(now) || animation_disabled() {
                    return HandleResult::Return(PageMsg::Confirmed);
                } else {
                    loader.start_shrinking(ctx, now);
                }
            }
            _ => {}
        }

        HandleResult::Continue
    }
}

enum HandleResult<T> {
    Return(T),
    PrevPage,
    NextPage,
    Continue,
}

impl<T, U> Component for ButtonPage<T, U>
where
    T: Paginate,
    T: Component,
    U: AsRef<str> + From<&'static str>,
{
    type Msg = PageMsg<T::Msg>;

    fn place(&mut self, bounds: Rect) -> Rect {
        let small_left_button = match (&self.button_cancel, &self.button_confirm) {
            (None, _) => true,
            (Some(cancel), confirm) => match (cancel.content(), confirm.content()) {
                (ButtonContent::Text(t), _) => t.as_ref().len() <= 4,
                (ButtonContent::Icon(_), ButtonContent::Icon(_)) => false,
                _ => true,
            },
        };
        let layout = PageLayout::new(bounds, small_left_button);
        self.pad.place(bounds);
        self.swipe.place(bounds);
        self.button_cancel.place(layout.button_left);
        self.button_confirm.place(layout.button_right);
        self.button_prev.place(layout.button_left);
        self.button_next.place(layout.button_right);
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

        if page_count == 1 && self.button_cancel.is_none() {
            self.button_confirm.place(layout.button_both);
        }

        // Now that we finally have the page count, we can setup the scrollbar and the
        // swiper.
        self.scrollbar.set_count_and_active_page(page_count, 0);
        self.setup_swipe();

        self.loader.place(Self::loader_area());
        bounds
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        ctx.set_page_count(self.scrollbar.page_count);

        match self.handle_swipe(ctx, event) {
            HandleResult::Return(r) => return Some(r),
            HandleResult::PrevPage => {
                self.change_page(ctx, -1);
                return None;
            }
            HandleResult::NextPage => {
                self.change_page(ctx, 1);
                return None;
            }
            HandleResult::Continue => {}
        }

        if let Some(msg) = self.content.event(ctx, event) {
            return Some(PageMsg::Content(msg));
        }

        let mut confirm_button_msg = None;
        let mut button_result = None;

        match self.handle_button(ctx, event) {
            HandleResult::Return((Some(r), None)) => return Some(r),
            HandleResult::Return((r, m)) => {
                button_result = r;
                confirm_button_msg = m;
            }
            HandleResult::PrevPage => {
                self.change_page(ctx, -1);
                return None;
            }
            HandleResult::NextPage => {
                self.change_page(ctx, 1);
                return None;
            }
            HandleResult::Continue => {}
        }

        if self.loader.is_some() {
            return match self.handle_hold(ctx, event, &confirm_button_msg) {
                HandleResult::Return(r) => Some(r),
                HandleResult::Continue => None,
                _ => unreachable!(),
            };
        }
        button_result
    }

    fn paint(&mut self) {
        self.pad.paint();
        match &self.loader {
            Some(l) if l.is_animating() => self.loader.paint(),
            _ => {
                self.content.paint();
                if self.scrollbar.has_pages() {
                    self.scrollbar.paint();
                }
            }
        }
        if self.button_cancel.is_some() && self.is_cancel_visible() {
            self.button_cancel.paint();
        } else {
            self.button_prev.paint();
        }
        if self.scrollbar.has_next_page() {
            self.button_next.paint();
        } else {
            self.button_confirm.paint();
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
        self.button_cancel.bounds(sink);
        self.button_confirm.bounds(sink);
        self.button_prev.bounds(sink);
        self.button_next.bounds(sink);
    }
}

#[cfg(feature = "ui_debug")]
impl<T, U> crate::trace::Trace for ButtonPage<T, U>
where
    T: crate::trace::Trace,
{
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.component("ButtonPage");
        t.int("active_page", self.scrollbar.active_page as i64);
        t.int("page_count", self.scrollbar.page_count as i64);
        t.bool("hold", self.loader.is_some());
        t.child("content", &self.content);
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
    pub button_left: Rect,
    pub button_right: Rect,
    pub button_both: Rect,
}

impl PageLayout {
    const SCROLLBAR_WIDTH: i16 = 8;
    const SCROLLBAR_SPACE: i16 = 5;

    pub fn new(area: Rect, small_left_button: bool) -> Self {
        let (area, button_both) = area.split_bottom(theme::BUTTON_HEIGHT);
        let area = area.inset(Insets::bottom(theme::BUTTON_SPACING));
        let (_space, content) = area.split_left(theme::CONTENT_BORDER);
        let (content_single_page, _space) = content.split_right(theme::CONTENT_BORDER);
        let (content, scrollbar) =
            content.split_right(Self::SCROLLBAR_SPACE + Self::SCROLLBAR_WIDTH);
        let (_space, scrollbar) = scrollbar.split_left(Self::SCROLLBAR_SPACE);

        let width = if small_left_button {
            theme::BUTTON_WIDTH
        } else {
            (button_both.width() - theme::BUTTON_SPACING) / 2
        };
        let (button_left, button_right) = button_both.split_left(width);
        let button_right = button_right.inset(Insets::left(theme::BUTTON_SPACING));

        Self {
            content_single_page,
            content,
            scrollbar,
            button_left,
            button_right,
            button_both,
        }
    }
}

#[cfg(test)]
mod tests {
    use serde_json;

    use crate::{
        strutil::SkipPrefix,
        trace::tests::trace,
        ui::{
            component::text::paragraphs::{Paragraph, Paragraphs},
            event::TouchEvent,
            geometry::Point,
            model_tt::{constant, theme},
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
        let mut page = ButtonPage::<_, &'static str>::new(
            Paragraphs::<[Paragraph<&'static str>; 0]>::new([]),
            theme::BG,
        );
        page.place(SCREEN);

        let expected = serde_json::json!({
            "component": "ButtonPage",
            "active_page": 0,
            "page_count": 1,
            "content": {
                "component": "Paragraphs",
                "paragraphs": [],
            },
            "hold": false,
        });

        assert_eq!(trace(&page), expected);
        swipe_up(&mut page);
        assert_eq!(trace(&page), expected);
        swipe_down(&mut page);
        assert_eq!(trace(&page), expected);
    }

    #[test]
    fn paragraphs_single() {
        let mut page = ButtonPage::<_, &'static str>::new(
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
            theme::BG,
        );
        page.place(SCREEN);

        let expected = serde_json::json!({
            "component": "ButtonPage",
            "active_page": 0,
            "page_count": 1,
            "content": {
                "component": "Paragraphs",
                "paragraphs": [
                    ["This is the first", "\n", "paragraph and it should", "\n", "fit on the screen", "\n", "entirely."],
                    ["Second, bold, paragraph", "\n", "should also fit on the", "\n", "screen whole I think."],
                ],
            },
            "hold": false,
        });

        assert_eq!(trace(&page), expected);
        swipe_up(&mut page);
        assert_eq!(trace(&page), expected);
        swipe_down(&mut page);
        assert_eq!(trace(&page), expected);
    }

    #[test]
    fn paragraphs_one_long() {
        let mut page = ButtonPage::<_, &'static str>::new(
            Paragraphs::new(
                Paragraph::new(
                    &theme::TEXT_BOLD,
                    "This is somewhat long paragraph that goes on and on and on and on and on and will definitely not fit on just a single screen. You have to swipe a bit to see all the text it contains I guess. There's just so much letters in it.",
                )
            ),
            theme::BG,
        );
        page.place(SCREEN);

        let first_page = serde_json::json!({
            "component": "ButtonPage",
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
            "hold": false,
        });
        let second_page = serde_json::json!({
            "component": "ButtonPage",
            "active_page": 1,
            "page_count": 2,
            "content": {
                "component": "Paragraphs",
                "paragraphs": [
                    ["There's just so much", "\n", "letters in it."],
                ],
            },
            "hold": false,
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
        let mut page = ButtonPage::<_, &'static str>::new(
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
            theme::BG,
        );
        page.place(SCREEN);

        let first_page = serde_json::json!({
            "component": "ButtonPage",
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
            "hold": false,
        });
        let second_page = serde_json::json!({
            "component": "ButtonPage",
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
            "hold": false,
        });
        let third_page = serde_json::json!({
            "component": "ButtonPage",
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
            "hold": false,
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
        let mut page = ButtonPage::<_, &'static str>::new(
            Paragraphs::new([
                Paragraph::new(&theme::TEXT_NORMAL, "Short one.").break_after(),
                Paragraph::new(&theme::TEXT_NORMAL, "Short two.").break_after(),
                Paragraph::new(&theme::TEXT_NORMAL, "Short three.").break_after(),
            ]),
            theme::BG,
        );
        page.place(SCREEN);

        let first_page = serde_json::json!({
            "component": "ButtonPage",
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
            "hold": false,
        });
        let second_page = serde_json::json!({
            "component": "ButtonPage",
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
            "hold": false,
        });
        let third_page = serde_json::json!({
            "component": "ButtonPage",
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
            "hold": false,
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
