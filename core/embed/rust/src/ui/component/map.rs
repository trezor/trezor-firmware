use super::{Component, Event, EventCtx};
use crate::ui::{geometry::Rect, shape::Renderer};

#[cfg(all(feature = "micropython", feature = "touch"))]
use crate::ui::component::swipe_detect::SwipeConfig;

pub struct MsgMap<T, F> {
    inner: T,
    func: F,
}

impl<T, F> MsgMap<T, F> {
    pub fn new(inner: T, func: F) -> Self {
        Self { inner, func }
    }
}

impl<T, F, U> Component for MsgMap<T, F>
where
    T: Component,
    F: Fn(T::Msg) -> Option<U>,
{
    type Msg = U;

    fn place(&mut self, bounds: Rect) -> Rect {
        self.inner.place(bounds)
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        self.inner.event(ctx, event).and_then(&self.func)
    }

    fn render<'s>(&'s self, target: &mut impl Renderer<'s>) {
        self.inner.render(target);
    }
}

#[cfg(all(feature = "micropython", feature = "touch"))]
impl<T, F> crate::ui::flow::Swipable for MsgMap<T, F>
where
    T: Component + crate::ui::flow::Swipable,
{
    fn get_swipe_config(&self) -> SwipeConfig {
        self.inner.get_swipe_config()
    }
    fn get_pager(&self) -> crate::ui::util::Pager {
        self.inner.get_pager()
    }
}

#[cfg(feature = "ui_debug")]
impl<T, F> crate::trace::Trace for MsgMap<T, F>
where
    T: Component + crate::trace::Trace,
{
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        self.inner.trace(t)
    }
}

pub struct PageMap<T, F> {
    inner: T,
    func: F,
}

impl<T, F> PageMap<T, F> {
    pub fn new(inner: T, func: F) -> Self {
        Self { inner, func }
    }
}

impl<T, F> Component for PageMap<T, F>
where
    T: Component,
    F: Fn(usize) -> usize,
{
    type Msg = T::Msg;

    fn place(&mut self, bounds: Rect) -> Rect {
        self.inner.place(bounds)
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        let res = self.inner.event(ctx, event);
        ctx.map_page_count(&self.func);
        res
    }

    fn render<'s>(&'s self, target: &mut impl Renderer<'s>) {
        self.inner.render(target);
    }
}

#[cfg(feature = "ui_debug")]
impl<T, F> crate::trace::Trace for PageMap<T, F>
where
    T: Component + crate::trace::Trace,
{
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        self.inner.trace(t)
    }
}

#[cfg(all(feature = "micropython", feature = "touch"))]
impl<T, F> crate::ui::flow::Swipable for PageMap<T, F>
where
    T: Component + crate::ui::flow::Swipable,
{
    fn get_swipe_config(&self) -> SwipeConfig {
        self.inner.get_swipe_config()
    }
    fn get_pager(&self) -> crate::ui::util::Pager {
        self.inner.get_pager()
    }
}
