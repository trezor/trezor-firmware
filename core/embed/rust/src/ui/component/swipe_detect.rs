use crate::{
    time::{Duration, Instant},
    ui::{
        animation::Animation,
        component::{Event, EventCtx, SwipeDirection},
        constant::screen,
        event::TouchEvent,
        geometry::{Offset, Point},
        util::animation_disabled,
    },
};

#[derive(Copy, Clone)]
pub struct SwipeSettings {
    pub duration: Duration,
}

impl SwipeSettings {
    pub const fn new(duration: Duration) -> Self {
        Self { duration }
    }

    pub const fn default() -> Self {
        Self {
            duration: Duration::from_millis(333),
        }
    }

    pub const fn immediate() -> Self {
        Self {
            duration: Duration::from_millis(0),
        }
    }
}

#[derive(Copy, Clone, Default)]
pub struct SwipeConfig {
    pub horizontal_pages: bool,
    pub vertical_pages: bool,
    pub up: Option<SwipeSettings>,
    pub down: Option<SwipeSettings>,
    pub left: Option<SwipeSettings>,
    pub right: Option<SwipeSettings>,
}

impl SwipeConfig {
    pub const fn new() -> Self {
        Self {
            horizontal_pages: false,
            vertical_pages: false,
            up: None,
            down: None,
            left: None,
            right: None,
        }
    }

    pub fn with_swipe(mut self, dir: SwipeDirection, settings: SwipeSettings) -> Self {
        self[dir] = Some(settings);
        self
    }

    pub fn is_allowed(&self, dir: SwipeDirection) -> bool {
        self[dir].is_some()
    }

    /// Calculate how much progress over `threshold` was made in the swipe
    /// direction.
    ///
    /// If the swipe direction is not allowed, this will return 0.
    pub fn progress(&self, dir: SwipeDirection, movement: Offset, threshold: u16) -> u16 {
        if !self.is_allowed(dir) {
            return 0;
        }

        let correct_movement = match dir {
            SwipeDirection::Right => movement.x > 0,
            SwipeDirection::Left => movement.x < 0,
            SwipeDirection::Down => movement.y > 0,
            SwipeDirection::Up => movement.y < 0,
        };

        if !correct_movement {
            return 0;
        }

        let movement = movement.abs();

        match dir {
            SwipeDirection::Right => (movement.x as u16).saturating_sub(threshold),
            SwipeDirection::Left => (movement.x as u16).saturating_sub(threshold),
            SwipeDirection::Down => (movement.y as u16).saturating_sub(threshold),
            SwipeDirection::Up => (movement.y as u16).saturating_sub(threshold),
        }
    }

    pub fn duration(&self, dir: SwipeDirection) -> Option<Duration> {
        self[dir].as_ref().map(|s| s.duration)
    }
    pub fn has_horizontal_pages(&self) -> bool {
        self.horizontal_pages
    }

    pub fn has_vertical_pages(&self) -> bool {
        self.vertical_pages
    }

    pub fn with_horizontal_pages(mut self) -> Self {
        self.horizontal_pages = true;
        self
    }

    pub fn with_vertical_pages(mut self) -> Self {
        self.vertical_pages = true;
        self
    }
}

impl core::ops::Index<SwipeDirection> for SwipeConfig {
    type Output = Option<SwipeSettings>;

    fn index(&self, index: SwipeDirection) -> &Self::Output {
        match index {
            SwipeDirection::Up => &self.up,
            SwipeDirection::Down => &self.down,
            SwipeDirection::Left => &self.left,
            SwipeDirection::Right => &self.right,
        }
    }
}

impl core::ops::IndexMut<SwipeDirection> for SwipeConfig {
    fn index_mut(&mut self, index: SwipeDirection) -> &mut Self::Output {
        match index {
            SwipeDirection::Up => &mut self.up,
            SwipeDirection::Down => &mut self.down,
            SwipeDirection::Left => &mut self.left,
            SwipeDirection::Right => &mut self.right,
        }
    }
}

#[derive(Copy, Clone, Eq, PartialEq)]
pub enum SwipeDetectMsg {
    Start(SwipeDirection),
    Move(SwipeDirection, u16),
    Trigger(SwipeDirection),
}

pub struct SwipeDetect {
    origin: Option<Point>,
    locked: Option<SwipeDirection>,
    final_animation: Option<Animation<i16>>,
    moved: u16,
}

impl SwipeDetect {
    const DISTANCE: u16 = 120;
    pub const PROGRESS_MAX: i16 = 1000;

    const DURATION_MS: u32 = 333;
    const TRIGGER_THRESHOLD: f32 = 0.3;
    const DETECT_THRESHOLD: f32 = 0.1;

    const MIN_LOCK: u16 = (Self::DISTANCE as f32 * Self::DETECT_THRESHOLD) as u16;
    const MIN_TRIGGER: u16 = (Self::DISTANCE as f32 * Self::TRIGGER_THRESHOLD) as u16;

    pub fn new() -> Self {
        Self {
            origin: None,
            locked: None,
            final_animation: None,
            moved: 0,
        }
    }

    const fn min_lock(&self) -> u16 {
        Self::MIN_LOCK
    }

    const fn min_trigger(&self) -> u16 {
        Self::MIN_TRIGGER
    }

    fn is_lockable(&self, dir: SwipeDirection) -> bool {
        let Some(origin) = self.origin else {
            return false;
        };

        let min_distance = self.min_trigger() as i16;

        match dir {
            SwipeDirection::Up => origin.y > min_distance,
            SwipeDirection::Down => origin.y < (screen().height() - min_distance),
            SwipeDirection::Left => origin.x > min_distance,
            SwipeDirection::Right => origin.x < (screen().width() - min_distance),
        }
    }

    fn progress(&self, val: u16) -> u16 {
        ((val as f32 / Self::DISTANCE as f32) * Self::PROGRESS_MAX as f32) as u16
    }

    fn eval_anim_frame(&mut self, ctx: &mut EventCtx) -> Option<SwipeDetectMsg> {
        if let Some(locked) = self.locked {
            let mut finish = false;
            let res = if let Some(animation) = &self.final_animation {
                if animation.finished(Instant::now()) {
                    finish = true;
                    if animation.to != 0 {
                        Some(SwipeDetectMsg::Trigger(locked))
                    } else {
                        Some(SwipeDetectMsg::Move(locked, 0))
                    }
                } else {
                    ctx.request_anim_frame();
                    ctx.request_paint();
                    if animation_disabled() {
                        None
                    } else {
                        Some(SwipeDetectMsg::Move(
                            locked,
                            animation.value(Instant::now()).max(0) as u16,
                        ))
                    }
                }
            } else {
                None
            };

            if finish {
                self.locked = None;
                ctx.request_anim_frame();
                ctx.request_paint();
                self.final_animation = None;
                self.moved = 0;
            }

            return res;
        }
        None
    }

    pub fn trigger(&mut self, ctx: &mut EventCtx, dir: SwipeDirection, config: SwipeConfig) {
        ctx.request_anim_frame();
        ctx.request_paint();

        let duration = config
            .duration(dir)
            .unwrap_or(Duration::from_millis(Self::DURATION_MS));

        self.locked = Some(dir);
        self.final_animation = Some(Animation::new(
            0,
            Self::PROGRESS_MAX,
            duration,
            Instant::now(),
        ));
    }

    pub(crate) fn reset(&mut self) {
        self.origin = None;
        self.locked = None;
        self.final_animation = None;
        self.moved = 0;
    }

    pub(crate) fn event(
        &mut self,
        ctx: &mut EventCtx,
        event: Event,
        config: SwipeConfig,
    ) -> Option<SwipeDetectMsg> {
        match (event, self.origin) {
            (Event::Touch(TouchEvent::TouchStart(pos)), _) => {
                if self.final_animation.is_none() {
                    // Mark the starting position of this touch.
                    self.origin.replace(pos);
                } else {
                    return self.eval_anim_frame(ctx);
                }
            }
            (Event::Touch(TouchEvent::TouchMove(pos)), Some(origin)) => {
                if self.final_animation.is_none() {
                    // Compare the touch distance with our allowed directions and determine if it
                    // constitutes a valid swipe.
                    let ofs = pos - origin;

                    let res = match self.locked {
                        Some(locked) => {
                            // advance in locked direction only
                            let moved = config.progress(locked, ofs, self.min_lock());
                            Some(SwipeDetectMsg::Move(locked, self.progress(moved)))
                        }
                        None => {
                            let mut res = None;
                            for dir in SwipeDirection::iter() {
                                let progress = config.progress(dir, ofs, self.min_lock());
                                if progress > 0 && self.is_lockable(dir) {
                                    self.locked = Some(dir);
                                    res = Some(SwipeDetectMsg::Start(dir));
                                    break;
                                }
                            }
                            res
                        }
                    };

                    if let Some(SwipeDetectMsg::Move(_, progress)) = res {
                        self.moved = progress;
                    }

                    if animation_disabled() {
                        return None;
                    }

                    return res;
                } else {
                    return self.eval_anim_frame(ctx);
                }
            }
            (Event::Touch(TouchEvent::TouchEnd(pos)), Some(origin)) => {
                if self.final_animation.is_none() {
                    // Touch interaction is over, reset the position.
                    self.origin.take();

                    // Compare the touch distance with our allowed directions and determine if it
                    // constitutes a valid swipe.
                    let ofs = pos - origin;

                    let final_value = match self.locked {
                        // advance in locked direction only trigger animation towards ending
                        // position
                        Some(locked) if config.progress(locked, ofs, self.min_trigger()) > 0 => {
                            Self::PROGRESS_MAX
                        }
                        // advance in direction other than locked trigger animation towards starting
                        // position
                        Some(_) => 0,
                        None => return None,
                    };

                    let Some(locked) = self.locked else {
                        // Touch ended without triggering a swipe.
                        return None;
                    };

                    ctx.request_anim_frame();
                    ctx.request_paint();

                    if !animation_disabled() {
                        let done = self.moved as f32 / Self::PROGRESS_MAX as f32;
                        let ratio = if final_value == 0 { done } else { 1.0 - done };

                        let duration = config
                            .duration(locked)
                            .unwrap_or(Duration::from_millis(Self::DURATION_MS));

                        let duration = ((duration.to_millis() as f32 * ratio) as u32).max(0);
                        self.final_animation = Some(Animation::new(
                            self.moved as i16,
                            final_value,
                            Duration::from_millis(duration),
                            Instant::now(),
                        ));
                    } else {
                        // clear animation
                        self.final_animation = None;
                        self.moved = 0;
                        self.locked = None;
                        return Some(SwipeDetectMsg::Trigger(locked));
                    }
                    return None;
                } else {
                    return self.eval_anim_frame(ctx);
                }
            }
            (Event::Timer(EventCtx::ANIM_FRAME_TIMER), _) => {
                return self.eval_anim_frame(ctx);
            }
            _ => {
                // Do nothing.
            }
        }
        None
    }
}
