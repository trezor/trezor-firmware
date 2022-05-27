use crate::ui::{
    component::{Component, Event, EventCtx, Never},
    geometry::Rect,
};

pub struct Painter<F> {
    area: Rect,
    func: F,
}

impl<F> Painter<F> {
    pub fn new(func: F) -> Self {
        Self {
            func,
            area: Rect::zero(),
        }
    }
}

impl<F> Component for Painter<F>
where
    F: FnMut(Rect),
{
    type Msg = Never;

    fn place(&mut self, bounds: Rect) -> Rect {
        self.area = bounds;
        self.area
    }

    fn event(&mut self, _ctx: &mut EventCtx, _event: Event) -> Option<Self::Msg> {
        None
    }

    fn paint(&mut self) {
        (self.func)(self.area);
    }
}
