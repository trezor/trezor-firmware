use crate::ui::{
    component::{Child, Component, Event, EventCtx},
    geometry::Rect,
};

pub enum NoBtnDialogMsg<T> {
    Controls(T),
}

/// Used for simple displaying of information without user interaction.
/// Suitable for just showing a message, or having a timeout after which
/// the dialog is dismissed.
pub struct NoBtnDialog<T, U> {
    content: Child<T>,
    controls: Child<U>,
}

impl<T, U> NoBtnDialog<T, U>
where
    T: Component,
    U: Component,
{
    pub fn new(content: T, controls: U) -> Self {
        Self {
            content: Child::new(content),
            controls: Child::new(controls),
        }
    }

    pub fn inner(&self) -> &T {
        self.content.inner()
    }
}

impl<T, U> Component for NoBtnDialog<T, U>
where
    T: Component,
    U: Component,
{
    type Msg = NoBtnDialogMsg<U::Msg>;

    fn place(&mut self, bounds: Rect) -> Rect {
        self.controls.place(bounds);
        self.content.place(bounds);
        bounds
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        self.controls.event(ctx, event).map(Self::Msg::Controls)
    }

    fn paint(&mut self) {
        self.content.paint();
        self.controls.paint();
    }
}

// DEBUG-ONLY SECTION BELOW

#[cfg(feature = "ui_debug")]
impl<T, U> crate::trace::Trace for NoBtnDialog<T, U>
where
    T: crate::trace::Trace,
    U: crate::trace::Trace,
{
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.open("NoBtnDialog");
        self.content.trace(t);
        t.close();
    }
}
