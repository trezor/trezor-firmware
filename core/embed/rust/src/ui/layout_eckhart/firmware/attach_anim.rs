use crate::{
    time::{Duration, Stopwatch},
    ui::{
        component::{
            base::{AttachType, EventPropagation},
            Event, EventCtx,
        },
        geometry::{Direction, Offset},
        lerp::Lerp,
        util::animation_disabled,
    },
};

#[derive(Clone)]
pub struct AttachAnimationData {
    pub stopwatch: Stopwatch,
    pub dir: Direction,
    pub duration: Duration,
}

/// Trait for attach animations.
pub trait AttachAnimation {
    fn data(&self) -> &AttachAnimationData;

    fn data_mut(&mut self) -> &mut AttachAnimationData;

    fn is_active(&self) -> bool {
        if animation_disabled() {
            return false;
        }

        self.data()
            .stopwatch
            .is_running_within(self.data().duration)
    }

    /// Evaluates the animation progress in the range [0.0, 1.0].
    fn eval(&self) -> f32 {
        if animation_disabled() {
            return 1.0;
        }

        self.data().stopwatch.elapsed() / self.data().duration
    }

    /// Starts the attach animation timer.
    fn start(&mut self) {
        self.data_mut().stopwatch.start();
    }

    /// Event processor for the animation. Blocks events from further processing
    /// while the animation is running.
    fn process_events(&mut self, ctx: &mut EventCtx, event: Event) -> EventPropagation {
        match event {
            Event::Attach(attach_type) => {
                // Lazy start the animation: request the first animation frame but do not start
                // the timer yet
                if let AttachType::Swipe(dir) = attach_type {
                    self.data_mut().dir = dir;
                }
                ctx.request_anim_frame();
                ctx.request_paint();
                EventPropagation::Stop
            }
            Event::Timer(EventCtx::ANIM_FRAME_TIMER) if !self.data().stopwatch.is_running() => {
                // First animation frame after attach: start the timer
                self.start();
                ctx.request_anim_frame();
                ctx.request_paint();
                EventPropagation::Stop
            }
            Event::Timer(EventCtx::ANIM_FRAME_TIMER) if self.is_active() => {
                // Animation in progress: request next frame
                ctx.request_anim_frame();
                ctx.request_paint();
                EventPropagation::Stop
            }
            Event::Touch(_) | Event::Swipe(_) => {
                // Block touch and swipe events while the animation is active
                if self.is_active() {
                    EventPropagation::Stop
                } else {
                    EventPropagation::Continue
                }
            }
            // Other events are not blocked
            _ => EventPropagation::Continue,
        }
    }

    /// Default implementation for getting the content offset during the attach
    /// animation.
    fn get_content_offset(&self, t: f32) -> Offset {
        let initial_offset = match self.data().dir {
            Direction::Up => Offset::y(-60),
            Direction::Down => Offset::y(60),
            Direction::Left => Offset::x(-60),
            Direction::Right => Offset::x(60),
        };
        let value = pareen::constant(0.0)
            .seq_ease_in(
                0.0,
                easer::functions::Cubic,
                self.data().duration.to_millis() as f32 / 1000.0,
                pareen::constant(1.0),
            )
            .eval(t);
        Offset::lerp(initial_offset, Offset::zero(), value)
    }

    /// Default implementation for getting the content alpha during the attach
    /// animation.
    fn get_content_alpha(&self, t: f32) -> u8 {
        u8::lerp(u8::MIN, u8::MAX, t)
    }
}

pub struct BasicAttachAnimation {
    data: AttachAnimationData,
}

impl BasicAttachAnimation {
    pub fn new(dir: Direction, duration: Duration) -> Self {
        Self {
            data: AttachAnimationData {
                stopwatch: Stopwatch::default(),
                dir,
                duration,
            },
        }
    }
}

impl AttachAnimation for BasicAttachAnimation {
    fn data(&self) -> &AttachAnimationData {
        &self.data
    }

    fn data_mut(&mut self) -> &mut AttachAnimationData {
        &mut self.data
    }
}

impl Default for BasicAttachAnimation {
    fn default() -> Self {
        Self::new(Direction::Up, Duration::from_millis(200))
    }
}

pub struct HeaderAttachAnimation {
    data: AttachAnimationData,
}

impl HeaderAttachAnimation {
    pub fn new(dir: Direction, duration: Duration) -> Self {
        Self {
            data: AttachAnimationData {
                stopwatch: Stopwatch::default(),
                dir,
                duration,
            },
        }
    }
}

impl AttachAnimation for HeaderAttachAnimation {
    fn data(&self) -> &AttachAnimationData {
        &self.data
    }
    fn data_mut(&mut self) -> &mut AttachAnimationData {
        &mut self.data
    }

    fn get_content_offset(&self, t: f32) -> Offset {
        const OFFSET: i16 = 37;
        if matches!(self.data().dir, Direction::Up | Direction::Down) {
            return Offset::zero();
        }
        let initial_offset = match self.data().dir {
            Direction::Left => Offset::x(OFFSET),
            Direction::Right => Offset::x(-OFFSET),
            _ => Offset::zero(),
        };
        let value = pareen::constant(0.0)
            .seq_ease_in(
                0.0,
                easer::functions::Cubic,
                self.data().duration.to_millis() as f32 / 1000.0,
                pareen::constant(1.0),
            )
            .eval(t);
        Offset::lerp(initial_offset, Offset::zero(), value)
    }

    fn get_content_alpha(&self, t: f32) -> u8 {
        let value = pareen::constant(0.0)
            .seq_ease_in_out(
                0.0,
                easer::functions::Cubic,
                self.data().duration.to_millis() as f32 / 1000.0,
                pareen::constant(1.0),
            )
            .eval(t);
        u8::lerp(u8::MIN, u8::MAX, value)
    }
}

impl Default for HeaderAttachAnimation {
    fn default() -> Self {
        Self::new(Direction::Up, Duration::from_millis(500))
    }
}

pub struct MenuAttachAnimation {
    data: AttachAnimationData,
    n_items: u16,
    factor_item: f32,
    factor_delay: f32,
}

impl MenuAttachAnimation {
    const DURATION_PER_ITEM: Duration = Duration::from_millis(200);
    const DELAY_PER_ITEM: Duration = Duration::from_millis(100);

    pub fn new(n_items: u16) -> Self {
        debug_assert!(n_items > 0);
        let total_duration = Self::DURATION_PER_ITEM
            .checked_add(Self::DELAY_PER_ITEM * f32::from(n_items - 1))
            .unwrap_or(Self::DURATION_PER_ITEM);
        let factor_item = Self::DURATION_PER_ITEM / total_duration;
        let factor_delay = Self::DELAY_PER_ITEM / total_duration;
        dbg_println!(
            "MenuAttachAnimation::new: n_items={:#?}, total_duration={:#?}",
            n_items,
            total_duration.to_millis()
        );
        Self {
            data: AttachAnimationData {
                stopwatch: Stopwatch::default(),
                dir: Direction::Up,
                duration: total_duration,
            },
            n_items,
            factor_item,
            factor_delay,
        }
    }

    pub fn get_item_alpha(&self, idx: u16, t: f32) -> u8 {
        debug_assert!(idx < self.n_items);
        if t >= 1.0 {
            return u8::MAX;
        }

        let adjusted_t = (t - self.factor_delay * f32::from(idx)) / self.factor_item;
        let adjusted_t = adjusted_t.clamp(0.0, 1.0);

        let res = u8::lerp(u8::MIN, u8::MAX, adjusted_t);
        dbg_println!(
            "MenuAttachAnimation::get_item_alpha: idx={:#?}, res={:#?}",
            idx,
            res
        );

        res
    }

    pub fn get_separator_alpha(&self, idx: u16, t: f32) -> u8 {
        if t >= 1.0 || t > self.factor_delay * f32::from(idx) {
            u8::MAX
        } else {
            u8::MIN
        }
    }
}

impl AttachAnimation for MenuAttachAnimation {
    fn data(&self) -> &AttachAnimationData {
        &self.data
    }
    fn data_mut(&mut self) -> &mut AttachAnimationData {
        &mut self.data
    }
}

impl Default for MenuAttachAnimation {
    fn default() -> Self {
        Self::new(1)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_basic_attach_animation() {}
    #[test]
    fn test_header_attach_animation_offset() {}

    #[test]
    fn test_header_attach_animation_constants() {
        // Sanity check of set constants
        assert!(MenuAttachAnimation::DURATION_PER_ITEM > Duration::from_millis(0));
        assert!(MenuAttachAnimation::DELAY_PER_ITEM > Duration::from_millis(0));
        assert!(MenuAttachAnimation::DURATION_PER_ITEM > MenuAttachAnimation::DELAY_PER_ITEM);
    }

    #[test]
    fn test_menu_attach_animation_total_durations() {
        let m1 = MenuAttachAnimation::new(1);
        assert_eq!(m1.data().duration, MenuAttachAnimation::DURATION_PER_ITEM);

        let m2 = MenuAttachAnimation::new(2);
        assert_eq!(
            m2.data().duration,
            MenuAttachAnimation::DURATION_PER_ITEM
                .checked_add(MenuAttachAnimation::DELAY_PER_ITEM)
                .unwrap()
        );

        let m4 = MenuAttachAnimation::new(4);
        assert_eq!(
            m4.data().duration,
            MenuAttachAnimation::DURATION_PER_ITEM
                .checked_add(MenuAttachAnimation::DELAY_PER_ITEM * 3.0)
                .unwrap()
        )
    }

    #[test]
    fn test_menu_attach_animation_items_alpha() {}
}
