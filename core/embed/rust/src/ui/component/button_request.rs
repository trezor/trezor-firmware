use crate::ui::{
    button_request::ButtonRequest,
    component::{Component, Event, EventCtx},
    geometry::Rect,
};

#[cfg(all(feature = "micropython", feature = "touch"))]
use crate::ui::component::swipe_detect::SwipeConfig;

/// Component that sends a ButtonRequest after receiving Event::Attach.
/// The request is sent only once.
#[derive(Clone)]
pub struct SendButtonRequest<T> {
    button_request: Option<ButtonRequest>,
    pub inner: T,
}

impl<T> SendButtonRequest<T> {
    pub const fn new(
        button_request: ButtonRequest,
        inner: T,
    ) -> Self {
        Self {
            button_request: Some(button_request),
            inner,
        }
    }
}

impl<T: Component> Component for SendButtonRequest<T> {
    type Msg = T::Msg;

    fn place(&mut self, bounds: Rect) -> Rect {
        self.inner.place(bounds)
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        if matches!(event, Event::Attach(_)) {
            if let Some(br) = self.button_request.take() {
                ctx.send_button_request(br.code, br.name)
            }
        }
        self.inner.event(ctx, event)
    }

    fn render<'s>(&'s self, target: &mut impl crate::ui::shape::Renderer<'s>) {
        self.inner.render(target)
    }
}

#[cfg(all(feature = "micropython", feature = "touch"))]
impl<T: crate::ui::flow::Swipable> crate::ui::flow::Swipable for SendButtonRequest<T> {
    fn get_swipe_config(&self) -> SwipeConfig {
        self.inner.get_swipe_config()
    }

    fn get_pager(&self) -> crate::ui::util::Pager {
        self.inner.get_pager()
    }
}

#[cfg(feature = "ui_debug")]
impl<T: crate::trace::Trace> crate::trace::Trace for SendButtonRequest<T> {
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        self.inner.trace(t)
    }
}

pub trait ButtonRequestExt {
    fn with_button_request(self, br: ButtonRequest) -> SendButtonRequest<Self>
    where
        Self: Sized,
    {
        SendButtonRequest::new(br, self)
    }
}

impl<T: Component> ButtonRequestExt for T {}
