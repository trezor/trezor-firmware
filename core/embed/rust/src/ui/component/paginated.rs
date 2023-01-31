pub enum AuxPageMsg {
    /// Page component was instantiated with BACK button on every page and it
    /// was pressed.
    GoBack,

    /// Page component was configured to react to swipes and user swiped left.
    SwipeLeft,
}

/// Common message type for pagination components.
pub enum PageMsg<T, U> {
    /// Pass-through from paged component.
    Content(T),

    /// Messages from page controls outside the paged component, like
    /// "OK" and "Cancel" buttons.
    Controls(U),

    /// Auxilliary events used by exotic pages on touchscreens.
    Aux(AuxPageMsg),
}

pub trait Paginate {
    /// How many pages of content are there in total?
    fn page_count(&mut self) -> usize;
    /// Navigate to the given page.
    fn change_page(&mut self, active_page: usize);
}
