use super::{Component, Event, EventCtx};
use crate::ui::{
    geometry::{Insets, Rect},
    shape::Renderer,
};

pub struct Border<T> {
    border: Insets,
    inner: T,
}

impl<T> Border<T>
where
    T: Component,
{
    pub fn new(border: Insets, inner: T) -> Self {
        Self { border, inner }
    }

    pub fn inner(&self) -> &T {
        &self.inner
    }
}

impl<T> Component for Border<T>
where
    T: Component,
{
    type Msg = T::Msg;

    fn place(&mut self, bounds: Rect) -> Rect {
        let inside = bounds.inset(self.border);
        self.inner.place(inside);
        inside
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        self.inner.event(ctx, event)
    }

    fn paint(&mut self) {
        self.inner.paint()
    }

    fn render<'s>(&'s self, target: &mut impl Renderer<'s>) {
        self.inner.render(target);
    }
}

#[cfg(feature = "ui_debug")]
impl<T> crate::trace::Trace for Border<T>
where
    T: Component + crate::trace::Trace,
{
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        self.inner.trace(t)
    }
}

#[cfg(feature = "micropython")]
mod micropython {
    use crate::{error::Error, micropython::obj::Obj, ui::layout::obj::ComponentMsgObj};
    impl<T: ComponentMsgObj> ComponentMsgObj for super::Border<T> {
        fn msg_try_into_obj(&self, msg: Self::Msg) -> Result<Obj, Error> {
            self.inner().msg_try_into_obj(msg)
        }
    }
}
