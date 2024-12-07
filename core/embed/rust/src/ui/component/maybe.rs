use crate::ui::{
    component::{Component, ComponentExt, Event, EventCtx, Pad},
    display::Color,
    geometry::Rect,
    shape::Renderer,
};

pub struct Maybe<T> {
    inner: T,
    pad: Pad,
    visible: bool,
}

impl<T> Maybe<T> {
    pub fn new(bg_color: Color, inner: T, visible: bool) -> Self {
        let pad = Pad::with_background(bg_color);
        Self {
            inner,
            visible,
            pad,
        }
    }

    pub fn visible(bg_color: Color, inner: T) -> Self {
        Self::new(bg_color, inner, true)
    }

    pub fn hidden(bg_color: Color, inner: T) -> Self {
        Self::new(bg_color, inner, false)
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

    fn render<'s>(&'s self, target: &mut impl Renderer<'s>) {
        self.pad.render(target);
        if self.visible {
            self.inner.render(target);
        }
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
