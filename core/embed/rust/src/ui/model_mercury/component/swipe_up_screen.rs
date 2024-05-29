use crate::ui::{
    component::{Component, Event, EventCtx, Swipe, SwipeDirection},
    geometry::Rect,
    shape::Renderer,
};

/// Wrapper component adding "swipe up" handling to `content`.
pub struct SwipeUpScreen<T> {
    content: T,
    swipe: Swipe,
}

pub enum SwipeUpScreenMsg<T> {
    Swiped,
    Content(T),
}

impl<T> SwipeUpScreen<T>
where
    T: Component,
{
    pub fn new(content: T) -> Self {
        Self {
            content,
            swipe: Swipe::new().up(),
        }
    }
}

impl<T> Component for SwipeUpScreen<T>
where
    T: Component,
{
    type Msg = SwipeUpScreenMsg<T::Msg>;

    fn place(&mut self, bounds: Rect) -> Rect {
        self.swipe.place(bounds);
        self.content.place(bounds);
        bounds
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        if let Some(SwipeDirection::Up) = self.swipe.event(ctx, event) {
            return Some(SwipeUpScreenMsg::Swiped);
        }
        self.content
            .event(ctx, event)
            .map(SwipeUpScreenMsg::Content)
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
