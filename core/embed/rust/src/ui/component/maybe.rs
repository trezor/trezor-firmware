use crate::ui::{
    component::{Component, ComponentExt, Event, EventCtx, Pad},
    display::{self, Color},
    geometry::Rect,
};

pub struct Maybe<T> {
    inner: T,
    pad: Pad,
    visible: bool,
}

impl<T> Maybe<T> {
    pub fn new(pad: Pad, inner: T, visible: bool) -> Self {
        Self {
            inner,
            visible,
            pad,
        }
    }

    pub fn visible(clear: Color, inner: T) -> Self {
        Self::new(Pad::with_background(clear), inner, true)
    }

    pub fn hidden(clear: Color, inner: T) -> Self {
        Self::new(Pad::with_background(clear), inner, false)
    }
}

impl<T> Maybe<T>
where
    T: Component,
{
    pub fn show_if(&mut self, ctx: &mut EventCtx, show: bool) {
        if self.visible != show {
            self.visible = show;

            // Invalidate the pad, so either we prepare a fresh canvas for the content, or
            // paint over it.
            self.pad.clear();
            if show {
                // Make sure the whole inner tree is painted.
                self.inner.request_complete_repaint(ctx);
            } else {
                // Just make sure out `paint` method is called, to clear the pad.
                ctx.request_paint();
            }
        }
    }

    pub fn show(&mut self, ctx: &mut EventCtx) {
        self.show_if(ctx, true)
    }

    pub fn hide(&mut self, ctx: &mut EventCtx) {
        self.show_if(ctx, false)
    }

    pub fn inner(&self) -> &T {
        &self.inner
    }

    pub fn inner_mut(&mut self) -> &mut T {
        &mut self.inner
    }
}

impl<T> Component for Maybe<T>
where
    T: Component,
{
    type Msg = T::Msg;

    fn place(&mut self, bounds: Rect) -> Rect {
        let area = self.inner.place(bounds);
        self.pad.place(area);
        area
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        if self.visible {
            self.inner.event(ctx, event)
        } else {
            None
        }
    }

    fn paint(&mut self) {
        self.pad.paint();
        if self.visible {
            self.inner.paint();
        }
    }

    #[cfg(feature = "ui_bounds")]
    fn bounds(&self, sink: &mut dyn FnMut(Rect)) {
        sink(self.pad.area);
        self.inner.bounds(sink);
    }
}

pub trait PaintOverlapping {
    /// Return area that would be cleared during regular paint, along with
    /// background color, or None if clearing isn't requested.
    fn cleared_area(&self) -> Option<(Rect, Color)>;

    /// Paint the component but do not clear background beforehand.
    fn paint_overlapping(&mut self);
}

impl<T> PaintOverlapping for Maybe<T>
where
    T: Component,
{
    fn cleared_area(&self) -> Option<(Rect, Color)> {
        self.pad.will_paint()
    }

    fn paint_overlapping(&mut self) {
        self.pad.cancel_clear();
        self.paint()
    }
}

/// Paint multiple Maybe<T> components, correctly handling clearing of
/// background in the case the areas overlap, i.e. clear the combined area first
/// and then paint over it.
pub fn paint_overlapping(components: &mut [&mut dyn PaintOverlapping]) {
    let mut area = Rect::zero();
    let mut color = Color::rgb(0, 0, 0);
    for component in components.iter() {
        if let Some((clear_area, clear_color)) = component.cleared_area() {
            area = area.union(clear_area);
            color = clear_color;
        }
    }

    if area != Rect::zero() {
        display::rect_fill(area, color)
    }

    for component in components.iter_mut() {
        component.paint_overlapping()
    }
}

// DEBUG-ONLY SECTION BELOW

#[cfg(feature = "ui_debug")]
impl<T> crate::trace::Trace for Maybe<T>
where
    T: Component + crate::trace::Trace,
{
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.component("Maybe");
        t.child("inner", &self.inner);
        t.bool("visible", self.visible);
    }
}
