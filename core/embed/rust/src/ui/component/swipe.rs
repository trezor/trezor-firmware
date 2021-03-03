use core::ops::RangeInclusive;

use crate::ui::{
    display,
    math::{Point, Rect},
    theme,
};

use super::component::{Component, Event, EventCtx, Widget};

pub enum SwipeDirection {
    Up,
    Down,
    Left,
    Right,
}

pub struct Swipe {
    widget: Widget,
    allow_up: bool,
    allow_down: bool,
    allow_left: bool,
    allow_right: bool,
    backlight: RangeInclusive<i32>,
    origin: Option<Point>,
}

impl Swipe {
    const DISTANCE: i32 = 120;
    const THRESHOLD: f32 = 0.3;

    pub fn new(area: Rect) -> Self {
        Self {
            widget: Widget::new(area),
            allow_up: false,
            allow_down: false,
            allow_left: false,
            allow_right: false,
            backlight: theme::BACKLIGHT_NORMAL..=theme::BACKLIGHT_NONE,
            origin: None,
        }
    }

    pub fn vertical(area: Rect) -> Self {
        Self::new(area).up().down()
    }

    pub fn horizontal(area: Rect) -> Self {
        Self::new(area).left().right()
    }

    pub fn up(mut self) -> Self {
        self.allow_up = true;
        self
    }

    pub fn down(mut self) -> Self {
        self.allow_down = true;
        self
    }

    pub fn left(mut self) -> Self {
        self.allow_left = true;
        self
    }

    pub fn right(mut self) -> Self {
        self.allow_right = true;
        self
    }

    fn ratio(&self, dist: i32) -> f32 {
        (dist as f32 / Self::DISTANCE as f32).min(1.0)
    }

    fn backlight(&self, ratio: f32) {
        let start = *self.backlight.start() as f32;
        let end = *self.backlight.end() as f32;
        let value = start + ratio * (end - start);
        display::backlight(value as i32);
    }
}

impl Component for Swipe {
    type Msg = SwipeDirection;

    fn widget(&mut self) -> &mut Widget {
        &mut self.widget
    }

    fn event(&mut self, _ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        let area = self.area();
        match (event, self.origin) {
            (Event::TouchStart(pos), _) if area.contains(pos) => {
                // Mark the starting position of this touch.
                self.origin.replace(pos);
            }
            (Event::TouchMove(pos), Some(origin)) => {
                // Consider our allowed directions and the touch distance and modify the display
                // backlight accordingly.
                let ofs = pos - origin;
                let abs = ofs.abs();
                if abs.x > abs.y && (self.allow_left || self.allow_right) {
                    // Horizontal direction.
                    if (ofs.x < 0 && self.allow_left) || (ofs.x > 0 && self.allow_right) {
                        self.backlight(self.ratio(abs.x));
                    }
                } else if abs.x < abs.y && (self.allow_up || self.allow_down) {
                    // Vertical direction.
                    if (ofs.y < 0 && self.allow_up) || (ofs.y > 0 && self.allow_down) {
                        self.backlight(self.ratio(abs.y));
                    }
                };
            }
            (Event::TouchEnd(pos), Some(origin)) => {
                // Touch interaction is over, reset the position.
                self.origin.take();

                // Compare the touch distance with our allowed directions and determine if it
                // constitutes a valid swipe.
                let ofs = pos - origin;
                let abs = ofs.abs();
                if abs.x > abs.y && (self.allow_left || self.allow_right) {
                    // Horizontal direction.
                    if self.ratio(abs.x) >= Self::THRESHOLD {
                        if ofs.x < 0 && self.allow_left {
                            return Some(SwipeDirection::Left);
                        } else if ofs.x > 0 && self.allow_right {
                            return Some(SwipeDirection::Right);
                        }
                    }
                } else if abs.x < abs.y && (self.allow_up || self.allow_down) {
                    // Vertical direction.
                    if self.ratio(abs.y) >= Self::THRESHOLD {
                        if ofs.y < 0 && self.allow_up {
                            return Some(SwipeDirection::Up);
                        } else if ofs.y > 0 && self.allow_down {
                            return Some(SwipeDirection::Down);
                        }
                    }
                };

                // Swipe did not happen, reset the backlight.
                self.backlight(0.0);
            }
            _ => {
                // Do nothing.
            }
        }
        None
    }

    fn paint(&mut self) {}
}
