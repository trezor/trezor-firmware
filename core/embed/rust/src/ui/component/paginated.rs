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
pub trait Paginate {
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

impl<T: SinglePage> Paginate for T {
    fn pager(&self) -> Pager {
        Pager::single_page()
    }

    fn change_page(&mut self, active_page: u16) {
        if active_page != 0 {
            unimplemented!()
        }
    }
}

/// Wrapper for paginate-able content that is displayed on a screen which does
/// NOT paginate. Re-checks after every `place()` (in `ui_debug` builds) that
/// the content fits on a single page, failing loudly otherwise. This detects
/// e.g. overlong translations that would otherwise be silently clipped.
pub struct CheckSinglePage<T> {
    inner: T,
}

impl<T: Paginate> CheckSinglePage<T> {
    pub fn new(inner: T) -> Self {
        Self { inner }
    }

    pub fn inner(&self) -> &T {
        &self.inner
    }
}

impl<T: Paginate> Paginate for CheckSinglePage<T> {
    fn pager(&self) -> Pager {
        self.inner.pager()
    }

    fn change_page(&mut self, active_page: u16) {
        self.inner.change_page(active_page);
    }
}

impl<T: crate::ui::component::Component + Paginate> crate::ui::component::Component
    for CheckSinglePage<T>
{
    type Msg = T::Msg;

    fn place(&mut self, bounds: crate::ui::geometry::Rect) -> crate::ui::geometry::Rect {
        let area = self.inner.place(bounds);
        crate::ui::util::assert_single_page(self.inner.pager());
        area
    }

    fn event(
        &mut self,
        ctx: &mut crate::ui::component::EventCtx,
        event: crate::ui::component::Event,
    ) -> Option<Self::Msg> {
        self.inner.event(ctx, event)
    }

    fn render<'s>(&'s self, target: &mut impl crate::ui::shape::Renderer<'s>) {
        self.inner.render(target);
    }
}

#[cfg(feature = "ui_debug")]
impl<T: crate::trace::Trace + Paginate> crate::trace::Trace for CheckSinglePage<T> {
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        self.inner.trace(t)
    }
}
