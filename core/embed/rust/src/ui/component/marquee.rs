use crate::{
    strutil::TString,
    time::{Duration, Instant},
    ui::{
        animation::Animation,
        component::{Component, Event, EventCtx, Never, Timer},
        display::{Color, Font},
        geometry::{Offset, Rect},
        shape::{self, Renderer},
        util::animation_disabled,
    },
};

const ANIMATION_DURATION_MS: u32 = 2000;
const PAUSE_DURATION_MS: u32 = 1000;

enum State {
    Initial,
    Left(Animation<i16>),
    PauseLeft,
    Right(Animation<i16>),
    PauseRight,
}

pub struct Marquee {
    area: Rect,
    pause_timer: Timer,
    min_offset: i16,
    max_offset: i16,
    state: State,
    text: TString<'static>,
    font: Font,
    fg: Color,
    bg: Color,
    duration: Duration,
    pause: Duration,
}

impl Marquee {
    pub fn new(text: TString<'static>, font: Font, fg: Color, bg: Color) -> Self {
        Self {
            area: Rect::zero(),
            pause_timer: Timer::new(),
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

    pub fn set_text(&mut self, text: TString<'static>) {
        self.text = text;
    }

    pub fn start(&mut self, ctx: &mut EventCtx, now: Instant) {
        // Not starting if animations are disabled.
        if animation_disabled() {
            return;
        }

        if let State::Initial = self.state {
            let text_width = self.text.map(|t| self.font.text_width(t));
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

    pub fn render_anim<'s>(&'s self, target: &mut impl Renderer<'s>, offset: i16) {
        target.in_window(self.area, &|target| {
            let text_height = self.font.text_height();
            let pos = self.area.top_left() + Offset::new(offset, text_height - 1);
            self.text.map(|t| {
                shape::Text::new(pos, t)
                    .with_font(self.font)
                    .with_fg(self.fg)
                    .render(target);
            });
        });
    }
}

impl Component for Marquee {
    type Msg = Never;

    fn place(&mut self, bounds: Rect) -> Rect {
        self.area = bounds;
        self.area
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        // Not doing anything if animations are disabled.
        if animation_disabled() {
            return None;
        }

        let now = Instant::now();

        if self.pause_timer.expire(event) {
            match self.state {
                State::PauseLeft => {
                    let anim = Animation::new(self.max_offset, self.min_offset, self.duration, now);
                    self.state = State::Right(anim);
                }
                State::PauseRight => {
                    let anim = Animation::new(self.min_offset, self.max_offset, self.duration, now);
                    self.state = State::Left(anim);
                }
                _ => {}
            }
            // We have something to paint, so request to be painted in the next pass.
            ctx.request_paint();
            // There is further progress in the animation, request an animation frame event.
            ctx.request_anim_frame();
        }

        if EventCtx::is_anim_frame(event) {
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
                        self.pause_timer.start(ctx, self.pause);
                        self.state = State::PauseRight;
                    }
                }
                State::Left(_) => {
                    if self.is_at_left(now) {
                        self.pause_timer.start(ctx, self.pause);
                        self.state = State::PauseLeft;
                    }
                }
                _ => {}
            }
        }

        None
    }

    fn render<'s>(&'s self, target: &mut impl Renderer<'s>) {
        let now = Instant::now();

        match self.state {
            State::Initial => {
                self.render_anim(target, 0);
            }
            State::PauseRight => {
                self.render_anim(target, self.min_offset);
            }
            State::PauseLeft => {
                self.render_anim(target, self.max_offset);
            }
            _ => {
                let progress = self.progress(now);
                if let Some(done) = progress {
                    self.render_anim(target, done);
                } else {
                    self.render_anim(target, 0);
                }
            }
        }
    }
}

#[cfg(feature = "ui_debug")]
impl crate::trace::Trace for Marquee {
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.component("Marquee");
        t.string("text", self.text);
    }
}
