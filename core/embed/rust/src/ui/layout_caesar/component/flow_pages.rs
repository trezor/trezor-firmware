use crate::{
    strutil::TString,
    ui::{
        component::{base::Component, FormattedText, Paginate},
        geometry::Rect,
        shape::Renderer,
        util::Pager,
    },
};

use super::{ButtonActions, ButtonDetails, ButtonLayout};

// So that there is only one implementation, and not multiple generic ones
// as would be via `const N: usize` generics.
const MAX_OPS_PER_PAGE: usize = 15;

/// Holding specific workflows that are created in `layout.rs`.
/// Is returning a `Page` (page/screen) on demand
/// based on the current page in `Flow`.
/// Before, when `layout.rs` was defining a `heapless::Vec` of `Page`s,
/// it was a very stack-expensive operation and StackOverflow was encountered.
/// With this "lazy-loading" approach (creating each page on demand) we can
/// have theoretically unlimited number of pages without triggering SO.
/// (Currently only the current page is stored on stack - in
/// `Flow::current_page`.)
pub struct FlowPages<F>
where
    F: Fn(usize) -> Page,
{
    /// Function/closure that will return appropriate page on demand.
    get_page: F,
    /// Number of pages in the flow.
    page_count: usize,
}

impl<F> FlowPages<F>
where
    F: Fn(usize) -> Page,
{
    pub fn new(get_page: F, page_count: usize) -> Self {
        Self {
            get_page,
            page_count,
        }
    }

    /// Returns a page on demand on a specified index.
    pub fn get(&self, page_index: usize) -> Page {
        (self.get_page)(page_index)
    }

    /// Total amount of pages.
    pub fn count(&self) -> usize {
        self.page_count
    }

    /// How many scrollable pages are there in the flow
    /// (each page can have arbitrary number of "sub-pages").
    pub fn scrollbar_page_count(&self, bounds: Rect) -> u16 {
        self.scrollbar_page_index(bounds, self.page_count)
    }

    /// Active scrollbar position connected with the beginning of a specific
    /// page index.
    pub fn scrollbar_page_index(&self, bounds: Rect, page_index: usize) -> u16 {
        let mut page_count = 0;
        for i in 0..page_index {
            let mut current_page = self.get(i);
            current_page.place(bounds);
            page_count += current_page.pager().total();
        }
        page_count
    }
}

#[derive(Clone)]
pub struct Page {
    formatted: FormattedText,
    btn_layout: ButtonLayout,
    btn_actions: ButtonActions,
    title: Option<TString<'static>>,
    /// Replaces `title` once the page is scrolled past its first sub-page.
    title_scrolled: Option<TString<'static>>,
    slim_arrows: bool,
    nav: bool,
    /// On an action-bar page, a successful "Shift + right" scroll-back leaves
    /// this page for the next one instead of moving to the previous sub-page.
    /// The tutorial uses it so that performing the gesture is what advances the
    /// walkthrough (figma 456:2899).
    advance_on_shift_back: bool,
    /// Offer "Shift" even with no previous sub-page to scroll to, taking the
    /// user back a whole page instead. Without this the icon on a single-page
    /// screen would advertise a gesture that does nothing.
    shift_to_prev_page: bool,
}

// For `layout.rs`
impl Page {
    pub fn new(
        btn_layout: ButtonLayout,
        btn_actions: ButtonActions,
        formatted: FormattedText,
    ) -> Self {
        Self {
            formatted,
            btn_layout,
            btn_actions,
            title: None,
            title_scrolled: None,
            slim_arrows: false,
            nav: false,
            advance_on_shift_back: false,
            shift_to_prev_page: false,
        }
    }
}

// For `flow.rs`
impl Page {
    /// A different title for once the page has been scrolled past its first
    /// sub-page, e.g. "SCROLL UP" instead of "SCREEN SCROLL".
    pub fn with_scrolled_title(mut self, title: TString<'static>) -> Self {
        self.title_scrolled = Some(title);
        self
    }

    /// Adding title.
    pub fn with_title(mut self, title: TString<'static>) -> Self {
        self.title = Some(title);
        self
    }

    /// Using slim arrows instead of wide buttons.
    pub fn with_slim_arrows(mut self) -> Self {
        self.slim_arrows = true;
        self
    }

    /// Mark this page as using the action-bar navigation (menu + "Shift").
    /// The button layout and events for such a page are handled by `Flow`
    /// (it owns the shift state), not by `btn_layout()` here.
    pub fn with_nav(mut self) -> Self {
        self.nav = true;
        self
    }

    /// Whether this page uses the action-bar navigation.
    pub fn is_nav(&self) -> bool {
        self.nav
    }

    /// Leave this page for the next one when "Shift + right" scrolls back,
    /// instead of moving to the previous sub-page. Makes performing the gesture
    /// the way out of the page.
    pub fn with_advance_on_shift_back(mut self) -> Self {
        self.advance_on_shift_back = true;
        self
    }

    /// See `with_advance_on_shift_back`.
    pub fn advances_on_shift_back(&self) -> bool {
        self.advance_on_shift_back
    }

    /// Offer "Shift" here even though there is no previous sub-page: the
    /// gesture goes back a whole page instead.
    pub fn with_shift_to_prev_page(mut self) -> Self {
        self.shift_to_prev_page = true;
        self
    }

    /// See `with_shift_to_prev_page`.
    pub fn shifts_to_prev_page(&self) -> bool {
        self.shift_to_prev_page
    }

    /// Underline the body text, as transient emphasis while a key is held.
    pub fn set_underline(&mut self, underline: bool) {
        self.formatted.set_underline(underline);
    }

    /// The raw, un-paginated button layout as configured in `layout.rs`. Used
    /// by `Flow` to pick the boundary buttons (first / last sub-page) of an
    /// action-bar page.
    pub fn raw_btn_layout(&self) -> ButtonLayout {
        self.btn_layout.clone()
    }

    pub fn render<'s>(&'s self, target: &mut impl Renderer<'s>) {
        self.formatted.render(target);
    }

    pub fn place(&mut self, bounds: Rect) -> Rect {
        self.formatted.place(bounds);
        bounds
    }

    pub fn btn_layout(&self) -> ButtonLayout {
        // When we are in pagination inside this flow,
        // show the up and down arrows on appropriate sides.
        let current = self.btn_layout.clone();

        // On the last page showing only the narrow arrow, so the right
        // button with possibly long text has enough space.
        let btn_left = if self.pager().has_prev() && !self.pager().has_next() {
            if self.slim_arrows {
                Some(ButtonDetails::left_arrow_icon())
            } else {
                Some(ButtonDetails::up_arrow_icon())
            }
        } else if self.pager().has_prev() {
            if self.slim_arrows {
                Some(ButtonDetails::left_arrow_icon())
            } else {
                Some(ButtonDetails::up_arrow_icon_wide())
            }
        } else {
            current.btn_left
        };

        // Middle button should be shown only on the last page, not to collide
        // with the possible fat right button.
        let (btn_middle, btn_right) = if self.pager().has_next() {
            if self.slim_arrows {
                (None, Some(ButtonDetails::right_arrow_icon()))
            } else {
                (None, Some(ButtonDetails::down_arrow_icon_wide()))
            }
        } else {
            (current.btn_middle, current.btn_right)
        };

        ButtonLayout::new(btn_left, btn_middle, btn_right)
    }

    pub fn btn_actions(&self) -> ButtonActions {
        self.btn_actions
    }

    pub fn title(&self) -> Option<TString<'static>> {
        // Once scrolled, a page may name what the screen now does.
        if self.pager().current() > 0 && self.title_scrolled.is_some() {
            return self.title_scrolled;
        }
        self.title
    }
}

// Pagination
impl Paginate for Page {
    fn pager(&self) -> Pager {
        self.formatted.pager()
    }

    fn change_page(&mut self, to_page: u16) {
        self.formatted.change_page(to_page)
    }
}

// DEBUG-ONLY SECTION BELOW
#[cfg(feature = "ui_debug")]
impl crate::trace::Trace for Page {
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        use crate::ui::component::text::layout::LayoutFit;
        use core::cell::Cell;
        let fit: Cell<Option<LayoutFit>> = Cell::new(None);
        t.component("Page");
        if let Some(title) = &self.title {
            // Not calling it "title" as that is already traced by FlowPage
            t.string("page_title", *title);
        }
        t.int("active_page", self.pager().current() as i64);
        t.int("page_count", self.pager().total() as i64);
        t.in_list("text", &|l| {
            let result = self.formatted.trace_lines_as_list(l);
            fit.set(Some(result));
        });
    }
}
