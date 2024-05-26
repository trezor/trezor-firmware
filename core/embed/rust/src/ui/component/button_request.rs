use crate::ui::{
    button_request::ButtonRequest,
    component::{Component, Event, EventCtx},
    geometry::Rect,
};

#[cfg(all(feature = "micropython", feature = "touch", feature = "new_rendering"))]
use crate::ui::component::swipe_detect::SwipeConfig;

/// Component that sends a ButtonRequest after receiving Event::Attach. The
/// request is only sent once.
#[derive(Clone)]
pub struct OneButtonRequest<T> {
    button_request: Option<ButtonRequest>,
    pub inner: T,
}

impl<T> OneButtonRequest<T> {
    pub const fn new(button_request: ButtonRequest, inner: T) -> Self {
        Self {
            button_request: Some(button_request),
            inner,
        }
    }
}

impl<T: Component> Component for OneButtonRequest<T> {
    type Msg = T::Msg;

    fn place(&mut self, bounds: Rect) -> Rect {
        self.inner.place(bounds)
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        if matches!(event, Event::Attach(_)) {
            if let Some(button_request) = self.button_request.take() {
                ctx.send_button_request(button_request.code, button_request.br_type)
            }
        }
        self.inner.event(ctx, event)
    }

    fn paint(&mut self) {
        self.inner.paint()
    }

    fn render<'s>(&'s self, target: &mut impl crate::ui::shape::Renderer<'s>) {
        self.inner.render(target)
    }
}

#[cfg(all(feature = "micropython", feature = "touch", feature = "new_rendering"))]
impl<T: crate::ui::flow::Swipable> crate::ui::flow::Swipable for OneButtonRequest<T> {
    fn get_swipe_config(&self) -> SwipeConfig {
        self.inner.get_swipe_config()
    }

    fn get_internal_page_count(&self) -> usize {
        self.inner.get_internal_page_count()
    }
}

#[cfg(feature = "ui_debug")]
impl<T: crate::trace::Trace> crate::trace::Trace for OneButtonRequest<T> {
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        self.inner.trace(t)
    }
}

pub trait ButtonRequestExt {
    fn one_button_request(self, br: ButtonRequest) -> OneButtonRequest<Self>
    where
        Self: Sized,
    {
        OneButtonRequest::new(br, self)
    }
}

impl<T: Component> ButtonRequestExt for T {}
