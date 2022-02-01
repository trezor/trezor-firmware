use super::{Component, Event, EventCtx};

impl<T, A, B> Component for (A, B)
where
    A: Component<Msg = T>,
    B: Component<Msg = T>,
{
    type Msg = T;

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        self.0
            .event(ctx, event)
            .or_else(|| self.1.event(ctx, event))
    }

    fn paint(&mut self) {
        self.0.paint();
        self.1.paint();
    }
}

impl<T, A, B, C> Component for (A, B, C)
where
    A: Component<Msg = T>,
    B: Component<Msg = T>,
    C: Component<Msg = T>,
{
    type Msg = T;

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        self.0
            .event(ctx, event)
            .or_else(|| self.1.event(ctx, event))
            .or_else(|| self.2.event(ctx, event))
    }

    fn paint(&mut self) {
        self.0.paint();
        self.1.paint();
        self.2.paint();
    }
}
