use crate::ui::{
    component::{Child, Component, Event, EventCtx, Timeout, TimeoutMsg},
    geometry::Rect,
};

use super::super::layout::CancelConfirmMsg;

/// Used for simple displaying of information without user interaction.
/// Suitable for just showing a message, or having a timeout after which
/// the dialog is dismissed.
pub struct NoBtnDialog<T> {
    content: Child<T>,
    timeout: Option<Timeout>,
}

impl<T> NoBtnDialog<T>
where
    T: Component,
{
    pub fn new(content: T, timeout: Option<Timeout>) -> Self {
        Self {
            content: Child::new(content),
            timeout,
        }
    }

    pub fn inner(&self) -> &T {
        self.content.inner()
    }
}

impl<T> Component for NoBtnDialog<T>
where
    T: Component,
{
    type Msg = CancelConfirmMsg;

    fn place(&mut self, bounds: Rect) -> Rect {
        self.timeout.place(bounds);
        self.content.place(bounds);
        bounds
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        if let Some(TimeoutMsg::TimedOut) = self.timeout.event(ctx, event) {
            return Some(CancelConfirmMsg::Confirmed);
        }
        None
    }

    fn paint(&mut self) {
        self.content.paint();
        self.timeout.paint();
    }
}

// DEBUG-ONLY SECTION BELOW

#[cfg(feature = "ui_debug")]
impl<T> crate::trace::Trace for NoBtnDialog<T>
where
    T: crate::trace::Trace,
{
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.component("NoBtnDialog");
        t.child("content", &self.content);
    }
}
