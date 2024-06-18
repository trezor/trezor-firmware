use crate::ui::{
    component::{base::AttachType, Component, Event, EventCtx, SwipeDetect, SwipeDetectMsg},
    event::{SwipeEvent, TouchEvent},
    flow::Swipable,
    geometry::Rect,
    shape::Renderer,
};

/// Wrapper component adding "swipe up" handling to `content`.
pub struct SwipeUpScreen<T> {
    content: T,
    swipe: SwipeDetect,
}

pub enum SwipeUpScreenMsg<T> {
    Swiped,
    Content(T),
}

impl<T> SwipeUpScreen<T>
where
    T: Component,
{
    pub fn new(content: T) -> Self
    where
        T: Swipable,
    {
        Self {
            content,
            swipe: SwipeDetect::new(),
        }
    }

    pub fn inner(&self) -> &T {
        &self.content
    }
}

impl<T: Swipable + Component> Component for SwipeUpScreen<T> {
    type Msg = SwipeUpScreenMsg<T::Msg>;

    fn place(&mut self, bounds: Rect) -> Rect {
        self.content.place(bounds);
        bounds
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        let e = match self
            .swipe
            .event(ctx, event, self.content.get_swipe_config())
        {
            Some(SwipeDetectMsg::Trigger(dir)) => {
                ctx.set_transition_out(AttachType::Swipe(dir));
                return Some(SwipeUpScreenMsg::Swiped);
            }
            Some(SwipeDetectMsg::Move(dir, progress)) => {
                Event::Swipe(SwipeEvent::Move(dir, progress as i16))
            }
            Some(SwipeDetectMsg::Start(_)) => Event::Touch(TouchEvent::TouchAbort),
            _ => event,
        };

        self.content.event(ctx, e).map(SwipeUpScreenMsg::Content)
    }

    fn paint(&mut self) {
        todo!()
    }

    fn render<'s>(&'s self, target: &mut impl Renderer<'s>) {
        self.content.render(target);
    }

    #[cfg(feature = "ui_bounds")]
    fn bounds(&self, sink: &mut dyn FnMut(Rect)) {
        self.content.bounds(sink);
    }
}

#[cfg(feature = "ui_debug")]
impl<T> crate::trace::Trace for SwipeUpScreen<T>
where
    T: crate::trace::Trace,
{
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.component("SwipeUpScreen");
        t.child("content", &self.content);
    }
}
