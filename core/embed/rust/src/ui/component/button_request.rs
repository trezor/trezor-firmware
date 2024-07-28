use crate::ui::{
    button_request::ButtonRequest,
    component::{Component, Event, EventCtx},
    geometry::Rect,
};

#[cfg(all(feature = "micropython", feature = "touch", feature = "new_rendering"))]
use crate::ui::component::swipe_detect::SwipeConfig;

/// Component that sends a ButtonRequest after receiving Event::Attach. The
/// request is either sent only once or on every Event::Attach configured by
/// `policy`.
#[derive(Clone)]
pub struct SendButtonRequest<T> {
    button_request: Option<ButtonRequest>,
    pub inner: T,
    policy: SendButtonRequestPolicy,
}

#[derive(Clone)]
pub enum SendButtonRequestPolicy {
    OnAttachOnce,
    OnAttachAlways,
}

impl<T> SendButtonRequest<T> {
    pub const fn new(
        button_request: ButtonRequest,
        inner: T,
        policy: SendButtonRequestPolicy,
    ) -> Self {
        Self {
            button_request: Some(button_request),
            inner,
            policy,
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
            match self.policy {
                SendButtonRequestPolicy::OnAttachOnce => {
                    if let Some(br) = self.button_request.take() {
                        ctx.send_button_request(br.code, br.name)
                    }
                }
                SendButtonRequestPolicy::OnAttachAlways => {
                    if let Some(br) = self.button_request.clone() {
                        ctx.send_button_request(br.code, br.name);
                    }
                }
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
impl<T: crate::ui::flow::Swipable> crate::ui::flow::Swipable for SendButtonRequest<T> {
    fn get_swipe_config(&self) -> SwipeConfig {
        self.inner.get_swipe_config()
    }

    fn get_internal_page_count(&self) -> usize {
        self.inner.get_internal_page_count()
    }
}

#[cfg(feature = "ui_debug")]
impl<T: crate::trace::Trace> crate::trace::Trace for SendButtonRequest<T> {
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        self.inner.trace(t)
    }
}

pub trait ButtonRequestExt {
    fn one_button_request(self, br: ButtonRequest) -> SendButtonRequest<Self>
    where
        Self: Sized,
    {
        SendButtonRequest::new(br, self, SendButtonRequestPolicy::OnAttachOnce)
    }

    fn repeated_button_request(self, br: ButtonRequest) -> SendButtonRequest<Self>
    where
        Self: Sized,
    {
        SendButtonRequest::new(br, self, SendButtonRequestPolicy::OnAttachAlways)
    }
}

impl<T: Component> ButtonRequestExt for T {}
