use crate::{
    time::{Duration, Instant},
    ui::{
        animation::Animation,
        component::{Component, Event, EventCtx},
        display,
        geometry::Rect,
        model_tr::theme,
    },
};

pub enum ResultAnimMsg {
    FullyGrown,
}

enum State {
    Initial,
    Growing(Animation<u16>),
    Grown,
}

pub struct ResultAnim {
    area: Rect,
    state: State,
    growing_duration: Duration,
    icon: &'static [u8],
}

impl ResultAnim {
    pub fn new(icon: &'static [u8]) -> Self {
        Self {
            area: Rect::zero(),
            state: State::Initial,
            growing_duration: Duration::from_millis(2000),
            icon,
        }
    }

    pub fn start_growing(&mut self, ctx: &mut EventCtx, now: Instant) {
        let anim = Animation::new(
            display::LOADER_MIN,
            display::LOADER_MAX,
            self.growing_duration,
            now,
        );

        self.state = State::Growing(anim);

        // The animation is starting, request an animation frame event.
        ctx.request_anim_frame();

        // We don't have to wait for the animation frame event with the first paint,
        // let's do that now.
        ctx.request_paint();
    }

    pub fn reset(&mut self) {
        self.state = State::Initial;
    }

    pub fn animation(&self) -> Option<&Animation<u16>> {
        match &self.state {
            State::Initial => None,
            State::Grown => None,
            State::Growing(a) => Some(a),
        }
    }

    pub fn progress(&self, now: Instant) -> Option<u16> {
        self.animation().map(|a| a.value(now))
    }

    pub fn is_animating(&self) -> bool {
        self.animation().is_some()
    }

    pub fn is_completely_grown(&self, now: Instant) -> bool {
        matches!(self.progress(now), Some(display::LOADER_MAX))
    }

    pub fn paint_anim(&mut self, done: i16) {
        display::rect_rounded2_partial(
            self.area,
            theme::FG,
            theme::BG,
            100 * done / 1000,
            Some((self.icon, theme::FG)),
        );
    }
}

impl Component for ResultAnim {
    type Msg = ResultAnimMsg;

    fn place(&mut self, bounds: Rect) -> Rect {
        self.area = bounds;
        self.area
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        let now = Instant::now();

        if let Event::Timer(EventCtx::ANIM_FRAME_TIMER) = event {
            if let State::Growing(_) = self.state {
                // We have something to paint, so request to be painted in the next pass.
                ctx.request_paint();

                if self.is_completely_grown(now) {
                    self.state = State::Grown;
                    return Some(ResultAnimMsg::FullyGrown);
                } else {
                    // There is further progress in the animation, request an animation frame event.
                    ctx.request_anim_frame();
                }
            }
        }
        None
    }

    fn paint(&mut self) {
        // TODO: Consider passing the current instant along with the event -- that way,
        // we could synchronize painting across the component tree. Also could be useful
        // in automated tests.
        // In practice, taking the current instant here is more precise in case some
        // other component in the tree takes a long time to draw.
        let now = Instant::now();

        if let State::Initial = self.state {
            self.paint_anim(0);
        } else if let State::Grown = self.state {
            self.paint_anim(display::LOADER_MAX as i16);
        } else {
            let progress = self.progress(now);
            if let Some(done) = progress {
                self.paint_anim(done as i16);
            } else {
                self.paint_anim(0);
            }
        }
    }
}

#[cfg(feature = "ui_debug")]
impl crate::trace::Trace for ResultAnim {
    fn trace(&self, d: &mut dyn crate::trace::Tracer) {
        d.open("ResultAnim");
        d.close();
    }
}
