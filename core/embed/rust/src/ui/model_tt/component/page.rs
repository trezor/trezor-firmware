use crate::ui::{
    component::{
        base::ComponentExt, paginated::PageMsg, Component, Event, EventCtx, Pad, Paginate,
    },
    display::{self, Color},
    geometry::{Offset, Rect},
};

use super::{theme, Button, ScrollBar, Swipe, SwipeDirection};

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
    U: Component,
{
    pub fn new(content: T, buttons: U, background: Color) -> Self {
        Self {
            content,
            buttons,
            scrollbar: ScrollBar::vertical(),
            swipe: Swipe::new(),
            pad: Pad::with_background(background),
            fade: None,
        }
    }

    fn setup_swipe(&mut self) {
        self.swipe.allow_up = self.scrollbar.has_next_page();
        self.swipe.allow_down = self.scrollbar.has_previous_page();
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

    fn paint_hint(&mut self) {
        display::text_center(
            self.pad.area.bottom_center() - Offset::y(3),
            "SWIPE TO CONTINUE",
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
    U: Component,
{
    type Msg = PageMsg<T::Msg, U::Msg>;

    fn place(&mut self, bounds: Rect) -> Rect {
        let layout = PageLayout::new(bounds);
        self.pad.place(bounds);
        self.swipe.place(bounds);
        self.buttons.place(layout.buttons);
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

        bounds
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
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
        sink(self.pad.area);
        self.scrollbar.bounds(sink);
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
        t.field("buttons", &self.buttons);
        t.close();
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

#[cfg(test)]
mod tests {
    use crate::{
        trace::Trace,
        ui::{
            component::{text::paragraphs::Paragraphs, Empty},
            geometry::Point,
            model_tt::{constant, event::TouchEvent, theme},
        },
    };

    use super::*;

    const SCREEN: Rect = constant::screen().inset(theme::borders());

    fn trace(val: &impl Trace) -> String {
        let mut t = Vec::new();
        val.trace(&mut t);
        String::from_utf8(t).unwrap()
    }

    fn swipe(component: &mut impl Component, points: &[(i32, i32)]) {
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
        let mut page = SwipePage::new(Paragraphs::<&str>::new(), Empty, theme::BG);
        page.place(SCREEN);

        let expected =
            "<SwipePage active_page:0 page_count:1 content:<Paragraphs > buttons:<Empty > >";

        assert_eq!(trace(&page), expected);
        swipe_up(&mut page);
        assert_eq!(trace(&page), expected);
        swipe_down(&mut page);
        assert_eq!(trace(&page), expected);
    }

    #[test]
    fn paragraphs_single() {
        let mut page = SwipePage::new(
            Paragraphs::new()
                .add::<theme::TTDefaultText>(
                    theme::FONT_NORMAL,
                    "This is the first paragraph and it should fit on the screen entirely.",
                )
                .add::<theme::TTDefaultText>(
                    theme::FONT_BOLD,
                    "Second, bold, paragraph should also fit on the screen whole I think.",
                ),
            Empty,
            theme::BG,
        );
        page.place(SCREEN);

        let expected = "<SwipePage active_page:0 page_count:1 content:<Paragraphs This is the first paragraph\nand it should fit on the\nscreen entirely.\nSecond, bold, paragraph\nshould also fit on the\nscreen whole I think.\n> buttons:<Empty > >";

        assert_eq!(trace(&page), expected);
        swipe_up(&mut page);
        assert_eq!(trace(&page), expected);
        swipe_down(&mut page);
        assert_eq!(trace(&page), expected);
    }

    #[test]
    fn paragraphs_one_long() {
        let mut page = SwipePage::new(
            Paragraphs::new()
                .add::<theme::TTDefaultText>(
                    theme::FONT_BOLD,
                    "This is somewhat long paragraph that goes on and on and on and on and on and will definitely not fit on just a single screen. You have to swipe a bit to see all the text it contains I guess. There's just so much letters in it.",
                ),
            Empty,
            theme::BG,
        );
        page.place(SCREEN);

        let expected1 = "<SwipePage active_page:0 page_count:2 content:<Paragraphs This is somewhat long\nparagraph that goes on\nand on and on and on\nand on and will definitely\nnot fit on just a single\nscreen. You have to\nswipe a bit to see all the\ntext it contains I guess....\n> buttons:<Empty > >";
        let expected2 = "<SwipePage active_page:1 page_count:2 content:<Paragraphs There's just so much\nletters in it.\n> buttons:<Empty > >";

        assert_eq!(trace(&page), expected1);
        swipe_down(&mut page);
        assert_eq!(trace(&page), expected1);
        swipe_up(&mut page);
        assert_eq!(trace(&page), expected2);
        swipe_up(&mut page);
        assert_eq!(trace(&page), expected2);
        swipe_down(&mut page);
        assert_eq!(trace(&page), expected1);
    }

    #[test]
    fn paragraphs_three_long() {
        let mut page = SwipePage::new(
            Paragraphs::new()
                .add::<theme::TTDefaultText>(
                    theme::FONT_BOLD,
                    "This paragraph is using a bold font. It doesn't need to be all that long.",
                )
                .add::<theme::TTDefaultText>(
                    theme::FONT_MONO,
                    "And this one is using MONO. Monospace is nice for numbers, they have the same width and can be scanned quickly. Even if they span several pages or something.",
                )
                .add::<theme::TTDefaultText>(
                    theme::FONT_BOLD,
                    "Let's add another one for a good measure. This one should overflow all the way to the third page with a bit of luck.",
                ),
            Empty,
            theme::BG,
        );
        page.place(SCREEN);

        let expected1 = "<SwipePage active_page:0 page_count:3 content:<Paragraphs This paragraph is using a\nbold font. It doesn't\nneed to be all that long.\nAnd this one is\nusing MONO.\nMonospace is\nnice for...\n> buttons:<Empty > >";
        let expected2 = "<SwipePage active_page:1 page_count:3 content:<Paragraphs numbers, they\nhave the same\nwidth and can be\nscanned quickly.\nEven if they\nspan several\npages or...\n> buttons:<Empty > >";
        let expected3 = "<SwipePage active_page:2 page_count:3 content:<Paragraphs something.\nLet's add another one\nfor a good measure. This\none should overflow all\nthe way to the third\npage with a bit of luck.\n> buttons:<Empty > >";

        assert_eq!(trace(&page), expected1);
        swipe_down(&mut page);
        assert_eq!(trace(&page), expected1);
        swipe_up(&mut page);
        assert_eq!(trace(&page), expected2);
        swipe_up(&mut page);
        assert_eq!(trace(&page), expected3);
        swipe_up(&mut page);
        assert_eq!(trace(&page), expected3);
        swipe_down(&mut page);
        assert_eq!(trace(&page), expected2);
        swipe_down(&mut page);
        assert_eq!(trace(&page), expected1);
        swipe_down(&mut page);
        assert_eq!(trace(&page), expected1);
    }
}
