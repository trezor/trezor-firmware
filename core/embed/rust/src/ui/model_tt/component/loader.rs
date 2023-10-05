use crate::{
    time::{Duration, Instant},
    ui::{
        animation::Animation,
        component::{Component, Event, EventCtx, Pad},
        display::{self, toif::Icon, Color},
        geometry::{Offset, Rect},
        model_tt::constant,
        util::animation_disabled,
    },
};

use super::theme;

const GROWING_DURATION_MS: u32 = 1000;
const SHRINKING_DURATION_MS: u32 = 500;

pub enum LoaderMsg {
    GrownCompletely,
    ShrunkCompletely,
}

enum State {
    Initial,
    Growing(Animation<u16>),
    Shrinking(Animation<u16>),
}

pub struct Loader {
    pub pad: Pad,
    state: State,
    growing_duration: Duration,
    shrinking_duration: Duration,
    styles: LoaderStyleSheet,
}

impl Loader {
    pub const SIZE: Offset = Offset::new(120, 120);

    pub fn new() -> Self {
        let styles = theme::loader_default();
        Self {
            pad: Pad::with_background(styles.normal.background_color),
            state: State::Initial,
            growing_duration: Duration::from_millis(GROWING_DURATION_MS),
            shrinking_duration: Duration::from_millis(SHRINKING_DURATION_MS),
            styles,
        }
    }

    pub fn with_durations(
        mut self,
        growing_duration: Duration,
        shrinking_duration: Duration,
    ) -> Self {
        self.growing_duration = growing_duration;
        self.shrinking_duration = shrinking_duration;
        self
    }

    pub fn start_growing(&mut self, ctx: &mut EventCtx, now: Instant) {
        let mut anim = Animation::new(
            display::LOADER_MIN,
            display::LOADER_MAX,
            self.growing_duration,
            now,
        );
        if let State::Shrinking(shrinking) = &self.state {
            anim.seek_to_value(shrinking.value(now));
        }
        self.state = State::Growing(anim);

        // The animation is starting, request an animation frame event.
        ctx.request_anim_frame();

        // We don't have to wait for the animation frame event with the first paint,
        // let's do that now.
        ctx.request_paint();
    }

    pub fn start_shrinking(&mut self, ctx: &mut EventCtx, now: Instant) {
        let mut anim = Animation::new(
            display::LOADER_MAX,
            display::LOADER_MIN,
            self.shrinking_duration,
            now,
        );
        if let State::Growing(growing) = &self.state {
            anim.seek_to_value(display::LOADER_MAX.saturating_sub(growing.value(now)));
        }
        self.state = State::Shrinking(anim);

        // Request anim frame as the animation may not be running, e.g. when already
        // grown completely.
        ctx.request_anim_frame();

        // We don't have to wait for the animation frame event with next paint,
        // let's do that now.
        ctx.request_paint();
    }

    pub fn reset(&mut self) {
        self.state = State::Initial;
    }

    pub fn animation(&self) -> Option<&Animation<u16>> {
        match &self.state {
            State::Initial => None,
            State::Growing(a) | State::Shrinking(a) => Some(a),
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

    pub fn is_completely_shrunk(&self, now: Instant) -> bool {
        matches!(self.progress(now), Some(display::LOADER_MIN))
    }
}

impl Component for Loader {
    type Msg = LoaderMsg;

    fn place(&mut self, bounds: Rect) -> Rect {
        self.pad.place(bounds);
        Rect::from_center_and_size(bounds.center(), Self::SIZE)
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        let now = Instant::now();

        if let Event::Timer(EventCtx::ANIM_FRAME_TIMER) = event {
            if self.is_animating() {
                // We have something to paint, so request to be painted in the next pass.
                if !animation_disabled() {
                    ctx.request_paint();
                }

                if self.is_completely_grown(now) {
                    return Some(LoaderMsg::GrownCompletely);
                } else if self.is_completely_shrunk(now) {
                    return Some(LoaderMsg::ShrunkCompletely);
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

        if let Some(progress) = self.progress(now) {
            let style = if progress < display::LOADER_MAX {
                self.styles.normal
            } else {
                self.styles.active
            };

            // Current loader API only takes Y-offset relative to screen center, which we
            // compute from the bounds center point.
            let screen_center = constant::screen().center();
            let offset_y = self.pad.area.center().y - screen_center.y;

            self.pad.paint();
            display::loader(
                progress,
                offset_y,
                style.loader_color,
                style.background_color,
                style.icon,
            );
        }
    }
}

pub struct LoaderStyleSheet {
    pub normal: &'static LoaderStyle,
    pub active: &'static LoaderStyle,
}

pub struct LoaderStyle {
    pub icon: Option<(Icon, Color)>,
    pub loader_color: Color,
    pub background_color: Color,
}

#[cfg(feature = "ui_debug")]
impl crate::trace::Trace for Loader {
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.component("Loader");
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn loader_yields_expected_progress() {
        let mut ctx = EventCtx::new();
        let mut l = Loader::new();
        let t = Instant::now();
        assert_eq!(l.progress(t), None);
        l.start_growing(&mut ctx, t);
        assert_eq!(l.progress(t), Some(0));
        let t = add_millis(t, 500);
        assert_eq!(l.progress(t), Some(500));
        l.start_shrinking(&mut ctx, t);
        assert_eq!(l.progress(t), Some(500));
        let t = add_millis(t, 125);
        assert_eq!(l.progress(t), Some(250));
        let t = add_millis(t, 125);
        assert_eq!(l.progress(t), Some(0));
    }

    fn add_millis(inst: Instant, millis: u32) -> Instant {
        inst.checked_add(Duration::from_millis(millis)).unwrap()
    }
}
