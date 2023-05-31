use crate::{
    time::{Duration, Instant},
    ui::{
        animation::Animation,
        component::{Component, Event, EventCtx, Never, TimerToken},
        display,
        display::{Color, Font},
        geometry::Rect,
        util::animation_disabled,
    },
};

const MILLIS_PER_LETTER_M: u32 = 300;
const ANIMATION_DURATION_MS: u32 = 2000;
const PAUSE_DURATION_MS: u32 = 1000;

enum State {
    Initial,
    Left(Animation<i16>),
    PauseLeft,
    Right(Animation<i16>),
    PauseRight,
}

pub struct Marquee<T> {
    area: Rect,
    pause_token: Option<TimerToken>,
    min_offset: i16,
    max_offset: i16,
    state: State,
    text: T,
    font: Font,
    fg: Color,
    bg: Color,
    duration: Duration,
    pause: Duration,
}

impl<T> Marquee<T>
where
    T: AsRef<str>,
{
    pub fn new(text: T, font: Font, fg: Color, bg: Color) -> Self {
        Self {
            area: Rect::zero(),
            pause_token: None,
            min_offset: 0,
            max_offset: 0,
            state: State::Initial,
            text,
            font,
            fg,
            bg,
            duration: Duration::from_millis(ANIMATION_DURATION_MS),
            pause: Duration::from_millis(PAUSE_DURATION_MS),
        }
    }

    pub fn set_text(&mut self, text: T) {
        self.text = text;
    }

    pub fn start(&mut self, ctx: &mut EventCtx, now: Instant) {
        // Not starting if animations are disabled.
        if animation_disabled() {
            return;
        }

        if let State::Initial = self.state {
            let text_width = self.font.text_width(self.text.as_ref());
            let max_offset = self.area.width() - text_width;

            self.min_offset = 0;
            self.max_offset = max_offset;

            let anim = Animation::new(self.min_offset, max_offset, self.duration, now);

            self.state = State::Left(anim);

            // The animation is starting, request an animation frame event.
            ctx.request_anim_frame();

            // We don't have to wait for the animation frame event with the first paint,
            // let's do that now.
            ctx.request_paint();
        }
    }

    pub fn reset(&mut self) {
        self.state = State::Initial;
    }

    pub fn animation(&self) -> Option<&Animation<i16>> {
        match &self.state {
            State::Initial => None,
            State::Left(a) => Some(a),
            State::PauseLeft => None,
            State::Right(a) => Some(a),
            State::PauseRight => None,
        }
    }

    pub fn is_at_right(&self, now: Instant) -> bool {
        if let Some(p) = self.progress(now) {
            return p == self.min_offset;
        }
        false
    }

    pub fn is_at_left(&self, now: Instant) -> bool {
        if let Some(p) = self.progress(now) {
            return p == self.max_offset;
        }
        false
    }

    pub fn progress(&self, now: Instant) -> Option<i16> {
        self.animation().map(|a| a.value(now))
    }

    pub fn is_animating(&self) -> bool {
        self.animation().is_some()
    }

    pub fn paint_anim(&mut self, offset: i16) {
        display::marquee(
            self.area,
            self.text.as_ref(),
            offset,
            self.font,
            self.fg,
            self.bg,
        );
    }
}

impl<T> Component for Marquee<T>
where
    T: AsRef<str>,
{
    type Msg = Never;

    fn place(&mut self, bounds: Rect) -> Rect {
        let base_width = self.font.text_width("M");
        let text_width = self.font.text_width(self.text.as_ref());
        let area_width = bounds.width();

        let shift_width = if area_width > text_width {
            area_width - text_width
        } else {
            text_width - area_width
        };

        let mut duration = (MILLIS_PER_LETTER_M * shift_width as u32) / base_width as u32;
        if duration < MILLIS_PER_LETTER_M {
            duration = MILLIS_PER_LETTER_M;
        }

        self.duration = Duration::from_millis(duration);
        self.area = bounds;
        self.area
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        // Not doing anything if animations are disabled.
        if animation_disabled() {
            return None;
        }

        let now = Instant::now();

        if let Event::Timer(token) = event {
            if self.pause_token == Some(token) {
                match self.state {
                    State::PauseLeft => {
                        let anim =
                            Animation::new(self.max_offset, self.min_offset, self.duration, now);
                        self.state = State::Right(anim);
                    }
                    State::PauseRight => {
                        let anim =
                            Animation::new(self.min_offset, self.max_offset, self.duration, now);
                        self.state = State::Left(anim);
                    }
                    _ => {}
                }
                // We have something to paint, so request to be painted in the next pass.
                ctx.request_paint();
                // There is further progress in the animation, request an animation frame event.
                ctx.request_anim_frame();
            }

            if token == EventCtx::ANIM_FRAME_TIMER {
                if self.is_animating() {
                    // We have something to paint, so request to be painted in the next pass.
                    ctx.request_paint();
                    // There is further progress in the animation, request an animation frame
                    // event.
                    ctx.request_anim_frame();
                }

                match self.state {
                    State::Right(_) => {
                        if self.is_at_right(now) {
                            self.pause_token = Some(ctx.request_timer(self.pause));
                            self.state = State::PauseRight;
                        }
                    }
                    State::Left(_) => {
                        if self.is_at_left(now) {
                            self.pause_token = Some(ctx.request_timer(self.pause));
                            self.state = State::PauseLeft;
                        }
                    }
                    _ => {}
                }
            }
        }
        None
    }

    fn paint(&mut self) {
        let now = Instant::now();

        match self.state {
            State::Initial => {
                self.paint_anim(0);
            }
            State::PauseRight => {
                self.paint_anim(self.min_offset);
            }
            State::PauseLeft => {
                self.paint_anim(self.max_offset);
            }
            _ => {
                let progress = self.progress(now);
                if let Some(done) = progress {
                    self.paint_anim(done);
                } else {
                    self.paint_anim(0);
                }
            }
        }
    }
}

#[cfg(feature = "ui_debug")]
impl<T> crate::trace::Trace for Marquee<T>
where
    T: AsRef<str>,
{
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.component("Marquee");
        t.string("text", self.text.as_ref());
    }
}
