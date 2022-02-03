use crate::ui::{
    component::{Component, ComponentExt, Event, EventCtx, Pad},
    display::Color,
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

    pub fn visible(area: Rect, clear: Color, inner: T) -> Self {
        Self::new(Pad::with_background(area, clear), inner, true)
    }

    pub fn hidden(area: Rect, clear: Color, inner: T) -> Self {
        Self::new(Pad::with_background(area, clear), inner, false)
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
}
