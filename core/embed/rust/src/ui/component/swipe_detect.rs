use crate::{
    time::{Duration, Instant},
    ui::{
        animation::Animation,
        component::{Event, EventCtx},
        constant::screen,
        event::{SwipeEvent, TouchEvent},
        geometry::{Axis, Direction, Offset, Point},
        util::{animation_disabled, Pager},
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
    pub page_axis: Option<Axis>,
    pub up: Option<SwipeSettings>,
    pub down: Option<SwipeSettings>,
    pub left: Option<SwipeSettings>,
    pub right: Option<SwipeSettings>,
}

impl SwipeConfig {
    pub const fn new() -> Self {
        Self {
            page_axis: None,
            up: None,
            down: None,
            left: None,
            right: None,
        }
    }

    pub fn with_swipe(mut self, dir: Direction, settings: SwipeSettings) -> Self {
        self[dir] = Some(settings);
        self
    }

    pub fn is_allowed(&self, dir: Direction) -> bool {
        self[dir].is_some()
    }

    /// Calculate how much progress over `threshold` was made in the swipe
    /// direction.
    ///
    /// If the swipe direction is not allowed, this will return 0.
    pub fn progress(&self, dir: Direction, movement: Offset, threshold: u16) -> u16 {
        if !self.is_allowed(dir) {
            return 0;
        }

        let correct_movement = match dir {
            Direction::Right => movement.x > 0,
            Direction::Left => movement.x < 0,
            Direction::Down => movement.y > 0,
            Direction::Up => movement.y < 0,
        };

        if !correct_movement {
            return 0;
        }

        let movement = movement.abs();

        match dir {
            Direction::Right => (movement.x as u16).saturating_sub(threshold),
            Direction::Left => (movement.x as u16).saturating_sub(threshold),
            Direction::Down => (movement.y as u16).saturating_sub(threshold),
            Direction::Up => (movement.y as u16).saturating_sub(threshold),
        }
    }

    pub fn duration(&self, dir: Direction) -> Option<Duration> {
        self[dir].as_ref().map(|s| s.duration)
    }

    pub fn with_horizontal_pages(mut self) -> Self {
        self.page_axis = Some(Axis::Horizontal);
        self
    }

    pub fn with_vertical_pages(mut self) -> Self {
        self.page_axis = Some(Axis::Vertical);
        self
    }

    pub fn with_pager(mut self, pager: Pager) -> Self {
        match self.page_axis {
            Some(Axis::Horizontal) => {
                if pager.has_prev() {
                    self.right = Some(SwipeSettings::default());
                }
                if pager.has_next() {
                    self.left = Some(SwipeSettings::default());
                }
            }
            Some(Axis::Vertical) => {
                if pager.has_prev() {
                    self.down = Some(SwipeSettings::default());
                }
                if pager.has_next() {
                    self.up = Some(SwipeSettings::default());
                }
            }
            _ => {}
        }
        self
    }

    pub fn paging_event(&self, dir: Direction, pager: Pager) -> u16 {
        match (self.page_axis, dir) {
            (Some(Axis::Horizontal), Direction::Right) => pager.prev(),
            (Some(Axis::Horizontal), Direction::Left) => pager.next(),
            (Some(Axis::Vertical), Direction::Down) => pager.prev(),
            (Some(Axis::Vertical), Direction::Up) => pager.next(),
            _ => pager.current(),
        }
    }
}

impl core::ops::Index<Direction> for SwipeConfig {
    type Output = Option<SwipeSettings>;

    fn index(&self, index: Direction) -> &Self::Output {
        match index {
            Direction::Up => &self.up,
            Direction::Down => &self.down,
            Direction::Left => &self.left,
            Direction::Right => &self.right,
        }
    }
}

impl core::ops::IndexMut<Direction> for SwipeConfig {
    fn index_mut(&mut self, index: Direction) -> &mut Self::Output {
        match index {
            Direction::Up => &mut self.up,
            Direction::Down => &mut self.down,
            Direction::Left => &mut self.left,
            Direction::Right => &mut self.right,
        }
    }
}

pub struct SwipeDetect {
    origin: Option<Point>,
    locked: Option<Direction>,
    final_animation: Option<Animation<i16>>,
    moved: i16,
}

impl SwipeDetect {
    const DISTANCE: u16 = 120;
    pub const PROGRESS_MAX: i16 = 1000;

    const DURATION_MS: u32 = 333;
    const TRIGGER_THRESHOLD: f32 = 0.3;
    const DETECT_THRESHOLD: f32 = 0.1;

    const VERTICAL_PREFERENCE: f32 = 2.0;

    const MIN_LOCK: f32 = Self::DISTANCE as f32 * Self::DETECT_THRESHOLD;
    const MIN_TRIGGER: f32 = Self::DISTANCE as f32 * Self::TRIGGER_THRESHOLD;

    pub fn new() -> Self {
        Self {
            origin: None,
            locked: None,
            final_animation: None,
            moved: 0,
        }
    }

    fn min_lock(&self, dir: Direction) -> u16 {
        match dir {
            Direction::Up | Direction::Down => Self::MIN_LOCK as u16,
            Direction::Left | Direction::Right => {
                (Self::MIN_LOCK * Self::VERTICAL_PREFERENCE) as u16
            }
        }
    }

    fn min_trigger(&self, dir: Direction) -> u16 {
        match dir {
            Direction::Up | Direction::Down => Self::MIN_TRIGGER as u16,
            Direction::Left | Direction::Right => {
                (Self::MIN_TRIGGER * Self::VERTICAL_PREFERENCE) as u16
            }
        }
    }

    fn is_lockable(&self, dir: Direction) -> bool {
        let Some(origin) = self.origin else {
            return false;
        };

        let min_distance = self.min_trigger(dir) as i16;

        match dir {
            Direction::Up => origin.y > min_distance,
            Direction::Down => origin.y < (screen().height() - min_distance),
            Direction::Left => origin.x > min_distance,
            Direction::Right => origin.x < (screen().width() - min_distance),
        }
    }

    fn progress(&self, val: u16) -> i16 {
        ((val as f32 / Self::DISTANCE as f32) * Self::PROGRESS_MAX as f32) as i16
    }

    fn eval_anim_frame(&mut self, ctx: &mut EventCtx) -> Option<SwipeEvent> {
        if let Some(locked) = self.locked {
            let mut finish = false;
            let res = if let Some(animation) = &self.final_animation {
                if animation.finished(Instant::now()) {
                    finish = true;
                    if animation.to != 0 {
                        Some(SwipeEvent::End(locked))
                    } else {
                        Some(SwipeEvent::Move(locked, 0))
                    }
                } else {
                    ctx.request_anim_frame();
                    ctx.request_paint();
                    if animation_disabled() {
                        None
                    } else {
                        Some(SwipeEvent::Move(
                            locked,
                            animation.value(Instant::now()).max(0),
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

    pub fn trigger(&mut self, ctx: &mut EventCtx, dir: Direction, config: SwipeConfig) {
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
    ) -> Option<SwipeEvent> {
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
                            let moved = config.progress(locked, ofs, self.min_lock(locked));
                            Some(SwipeEvent::Move(locked, self.progress(moved)))
                        }
                        None => {
                            let mut res = None;
                            for dir in Direction::iter() {
                                let progress = config.progress(dir, ofs, self.min_lock(dir));
                                if progress > 0 && self.is_lockable(dir) {
                                    self.locked = Some(dir);
                                    res = Some(SwipeEvent::Start(dir));
                                    break;
                                }
                            }
                            res
                        }
                    };

                    if let Some(SwipeEvent::Move(_, progress)) = res {
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
                        Some(locked)
                            if config.progress(locked, ofs, self.min_trigger(locked)) > 0 =>
                        {
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
                            self.moved,
                            final_value,
                            Duration::from_millis(duration),
                            Instant::now(),
                        ));
                    } else {
                        // clear animation
                        self.final_animation = None;
                        self.moved = 0;
                        self.locked = None;
                        return Some(SwipeEvent::End(locked));
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
