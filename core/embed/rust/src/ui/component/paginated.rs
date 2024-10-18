/// Common message type for pagination components.
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

pub trait Paginate {
    /// How many pages of content are there in total?
    fn page_count(&mut self) -> usize;
    /// Navigate to the given page.
    fn change_page(&mut self, active_page: usize);
}
