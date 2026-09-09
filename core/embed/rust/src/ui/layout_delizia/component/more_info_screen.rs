use super::theme::{self, TITLE_HEIGHT};
use super::{Button, ButtonMsg, Header};
use crate::strutil::TString;
use crate::ui::component::swipe_detect::{SwipeConfig, SwipeSettings};
use crate::ui::component::text::paragraphs::{ParagraphSource, Paragraphs};
use crate::ui::component::{Component, Event, EventCtx, FlowMsg, Paginate};
use crate::ui::flow::Swipable;
use crate::ui::geometry::{Direction, Insets, Rect};
use crate::ui::shape::Renderer;
use crate::ui::util::Pager;

/// Full-screen component showing paragraphs of text with a close button in
/// the header. When the text does not fit on a single page, up/down buttons
/// are shown to paginate through it (similar to the paginate-only action bar
/// in Eckhart's `TextScreen`).
pub struct MoreInfoScreen<T>
where
    T: ParagraphSource<'static>,
{
    header: Header,
    paragraphs: Paragraphs<T>,
    button_up: Option<Button>,
    button_down: Option<Button>,
    /// Whether the content needs pagination buttons. Decided on the first
    /// `place()` pass and kept stable afterwards, so that re-placing after a
    /// page change does not move the content around.
    paginated: Option<bool>,
}

impl<T> MoreInfoScreen<T>
where
    T: ParagraphSource<'static>,
{
    pub fn new(title: TString<'static>, paragraphs: Paragraphs<T>) -> Self {
        Self {
            header: Header::left_aligned(title).with_cancel_button(),
            paragraphs,
            button_up: None,
            button_down: None,
            paginated: None,
        }
    }

    fn update_page(&mut self, ctx: &mut EventCtx, page: u16) {
        self.paragraphs.change_page(page);
        // Re-run the place pass so that the pagination buttons are
        // shown/hidden according to the current page.
        ctx.request_place();
    }
}

impl<T> Component for MoreInfoScreen<T>
where
    T: ParagraphSource<'static>,
{
    type Msg = FlowMsg;

    fn place(&mut self, bounds: Rect) -> Rect {
        let header_height = self.header.place(bounds).height().max(TITLE_HEIGHT);
        let rest = bounds.inset(Insets::top(header_height + theme::SPACING));

        let paginated = if let Some(paginated) = self.paginated {
            paginated
        } else {
            // First pass without the buttons to find out whether the content
            // paginates at all.
            self.paragraphs.place(rest);
            let paginated = self.paragraphs.pager().total() > 1;
            self.paginated = Some(paginated);
            paginated
        };

        let content_area = if paginated {
            let (content_area, nav_area) =
                rest.split_bottom(theme::BUTTON_HEIGHT + theme::SPACING);
            let (buttons_area, _) = nav_area.split_top(theme::BUTTON_HEIGHT);

            let pager = self.paragraphs.pager();
            self.button_up = if pager.is_first() {
                None
            } else {
                Some(Button::with_icon(theme::ICON_CHEVRON_UP))
            };
            self.button_down = if pager.is_last() {
                None
            } else {
                Some(Button::with_icon(theme::ICON_CHEVRON_DOWN))
            };
            match (self.button_up.as_mut(), self.button_down.as_mut()) {
                (Some(up), Some(down)) => {
                    let (left, _, right) = buttons_area.split_center(0);
                    up.place(left);
                    down.place(right);
                }
                (Some(up), None) => {
                    up.place(buttons_area);
                }
                (None, Some(down)) => {
                    down.place(buttons_area);
                }
                (None, None) => {}
            }

            content_area
        } else {
            self.button_up = None;
            self.button_down = None;
            rest
        };
        self.paragraphs.place(content_area);

        bounds
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        if let Some(msg @ FlowMsg::Cancelled) = self.header.event(ctx, event) {
            return Some(msg);
        }

        if let Some(up) = self.button_up.as_mut() {
            if let Some(ButtonMsg::Clicked) = up.event(ctx, event) {
                let page = self.paragraphs.pager().prev();
                self.update_page(ctx, page);
                return None;
            }
        }
        if let Some(down) = self.button_down.as_mut() {
            if let Some(ButtonMsg::Clicked) = down.event(ctx, event) {
                let page = self.paragraphs.pager().next();
                self.update_page(ctx, page);
                return None;
            }
        }

        self.paragraphs.event(ctx, event);
        None
    }

    fn render<'s>(&'s self, target: &mut impl Renderer<'s>) {
        self.header.render(target);
        self.paragraphs.render(target);
        self.button_up.render(target);
        self.button_down.render(target);
    }
}

impl<T> Swipable for MoreInfoScreen<T>
where
    T: ParagraphSource<'static>,
{
    fn get_swipe_config(&self) -> SwipeConfig {
        // Swipe up to leave the screen (e.g. when wrapped in `SwipeUpScreen`).
        // Pagination is handled by the buttons, not by swiping.
        SwipeConfig::new().with_swipe(Direction::Up, SwipeSettings::Default)
    }

    fn get_pager(&self) -> Pager {
        self.paragraphs.pager()
    }
}

#[cfg(feature = "ui_debug")]
impl<T> crate::trace::Trace for MoreInfoScreen<T>
where
    T: ParagraphSource<'static>,
{
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.component("MoreInfoScreen");
        t.child("header", &self.header);
        t.child("paragraphs", &self.paragraphs);
    }
}
