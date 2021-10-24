use crate::{
    time::{Duration, Instant},
    ui::{
        animation::Animation,
        component::{Component, Event, EventCtx, Never},
        display::{self, Color},
    },
};

use super::theme;

enum State {
    Initial,
    Growing(Animation<u16>),
    Shrinking(Animation<u16>),
}

pub struct Loader {
    offset_y: i32,
    state: State,
    growing_duration: Duration,
    shrinking_duration: Duration,
    styles: LoaderStyleSheet,
}

impl Loader {
    pub fn new(offset_y: i32) -> Self {
        Self {
            offset_y,
            state: State::Initial,
            growing_duration: Duration::from_millis(1000),
            shrinking_duration: Duration::from_millis(500),
            styles: theme::loader_default(),
        }
    }

    pub fn start(&mut self, now: Instant) {
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
    }

    pub fn stop(&mut self, now: Instant) {
        let mut anim = Animation::new(
            display::LOADER_MAX,
            display::LOADER_MIN,
            self.shrinking_duration,
            now,
        );
        if let State::Growing(growing) = &self.state {
            anim.seek_to_value(growing.value(now));
        }
        self.state = State::Shrinking(anim);
    }

    pub fn reset(&mut self) {
        self.state = State::Initial;
    }

    pub fn progress(&self, now: Instant) -> Option<u16> {
        match &self.state {
            State::Initial => None,
            State::Growing(anim) | State::Shrinking(anim) => Some(anim.value(now)),
        }
    }

    pub fn is_started(&self) -> bool {
        matches!(self.state, State::Growing(_) | State::Shrinking(_))
    }

    pub fn is_finished(&self, now: Instant) -> bool {
        self.progress(now) == Some(display::LOADER_MAX)
    }
}

impl Component for Loader {
    type Msg = Never;

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        if let Event::Timer(EventCtx::ANIM_FRAME_TIMER) = event {
            if self.is_started() {
                ctx.request_paint();
                ctx.request_anim_frame();
            }
        }
        None
    }

    fn paint(&mut self) {
        if let Some(progress) = self.progress(Instant::now()) {
            let style = if progress < display::LOADER_MAX {
                self.styles.normal
            } else {
                self.styles.active
            };
            display::loader(
                progress,
                self.offset_y,
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
    pub icon: Option<(&'static [u8], Color)>,
    pub loader_color: Color,
    pub background_color: Color,
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn loader_yields_expected_progress() {
        let mut l = Loader::new(0);
        let t = Instant::now();
        assert_eq!(l.progress(t), None);
        l.start(t);
        assert_eq!(l.progress(t), Some(0));
        let t = add_millis(t, 500);
        assert_eq!(l.progress(t), Some(500));
        l.stop(t);
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
