use crate::ui::util::Pager;

/// Common message type for pagination components.
#[cfg_attr(feature = "debug", derive(ufmt::derive::uDebug))]
pub enum PageMsg<T> {
    /// Pass-through from paged component.
    Content(T),

    /// Confirmed using page controls.
    Confirmed,

    /// Cancelled using page controls.
    Cancelled,

    /// Info button pressed
    Info,

    /// Page component was configured to react to swipes and user swiped left.
    SwipeLeft,

    /// Page component was configured to react to swipes and user swiped right.
    SwipeRight,
}

/// Paginate trait allowing the user to see the internal pager state.
pub trait PaginateFull {
    /// What is the internal pager state?
    fn pager(&self) -> Pager;
    /// Navigate to the given page.
    fn change_page(&mut self, active_page: u16);

    fn next_page(&mut self) {
        let mut pager = self.pager();
        if pager.goto_next() {
            self.change_page(pager.current());
        }
    }

    fn prev_page(&mut self) {
        let mut pager = self.pager();
        if pager.goto_prev() {
            self.change_page(pager.current());
        }
    }
}

pub trait SinglePage {}

impl<T: SinglePage> PaginateFull for T {
    fn pager(&self) -> Pager {
        Pager::single_page()
    }

    fn change_page(&mut self, active_page: u16) {
        if active_page != 0 {
            unimplemented!()
        }
    }
}
