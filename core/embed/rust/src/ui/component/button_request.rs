use crate::ui::{
    button_request::ButtonRequest,
    component::{Component, Event, EventCtx},
    geometry::Rect,
};

/// Component that sends a ButtonRequest after receiving Event::Attach. The
/// request is only sent once.
#[derive(Clone)]
pub struct OneButtonRequest<T> {
    button_request: Option<ButtonRequest>,
    page_count: Option<u16>,
    pub inner: T,
}

impl<T> OneButtonRequest<T> {
    pub const fn new(button_request: ButtonRequest, inner: T) -> Self {
        Self {
            button_request: Some(button_request),
            page_count: None,
            inner,
        }
    }

    pub const fn with_pages(mut self, page_count: u16) -> Self {
        self.page_count = Some(page_count);
        self
    }
}

impl<T: Component> Component for OneButtonRequest<T> {
    type Msg = T::Msg;

    fn place(&mut self, bounds: Rect) -> Rect {
        self.inner.place(bounds)
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        if let Some(page_count) = self.page_count {
            ctx.set_page_count(page_count.into());
        }
        if matches!(event, Event::Attach) {
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

#[cfg(all(feature = "micropython", feature = "touch"))]
impl<T> crate::ui::flow::Swipable for OneButtonRequest<T>
where
    T: Component + crate::ui::flow::Swipable,
{
    fn swipe_start(
        &mut self,
        ctx: &mut EventCtx,
        direction: crate::ui::component::SwipeDirection,
    ) -> bool {
        self.inner.swipe_start(ctx, direction)
    }

    fn swipe_finished(&self) -> bool {
        self.inner.swipe_finished()
    }
}
