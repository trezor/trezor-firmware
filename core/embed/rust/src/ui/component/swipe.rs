use crate::ui::{
    component::{Component, Event, EventCtx},
    event::TouchEvent,
    geometry::{Direction, Point, Rect},
    shape::Renderer,
};

#[derive(Clone)]
pub struct Swipe {
    pub allow_up: bool,
    pub allow_down: bool,
    pub allow_left: bool,
    pub allow_right: bool,

    origin: Option<Point>,
}

impl Swipe {
    const DISTANCE: i32 = 120;
    const THRESHOLD: f32 = 0.2;

    pub fn new() -> Self {
        Self {
            allow_up: false,
            allow_down: false,
            allow_left: false,
            allow_right: false,
            origin: None,
        }
    }

    pub fn vertical() -> Self {
        Self::new().up().down()
    }

    pub fn horizontal() -> Self {
        Self::new().left().right()
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

    fn is_active(&self) -> bool {
        self.allow_up || self.allow_down || self.allow_left || self.allow_right
    }

    fn ratio(&self, dist: i16) -> f32 {
        (dist as f32 / Self::DISTANCE as f32).min(1.0)
    }
}

impl Component for Swipe {
    type Msg = Direction;

    fn place(&mut self, bounds: Rect) -> Rect {
        bounds
    }

    fn event(&mut self, _ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        if !self.is_active() {
            return None;
        }
        match (event, self.origin) {
            (Event::Touch(TouchEvent::TouchStart(pos)), _) => {
                // Mark the starting position of this touch.
                self.origin.replace(pos);
            }
            (Event::Touch(TouchEvent::TouchMove(pos)), Some(origin)) => {
                // Consider our allowed directions and the touch distance and modify the display
                // backlight accordingly.
                let ofs = pos - origin;
                let abs = ofs.abs();
                if abs.x > abs.y && (self.allow_left || self.allow_right) {
                    // Horizontal direction.
                    if (ofs.x < 0 && self.allow_left) || (ofs.x > 0 && self.allow_right) {
                        // self.backlight(self.ratio(abs.x));
                    }
                } else if abs.x < abs.y && (self.allow_up || self.allow_down) {
                    // Vertical direction.
                    if (ofs.y < 0 && self.allow_up) || (ofs.y > 0 && self.allow_down) {
                        // self.backlight(self.ratio(abs.y));
                    }
                };
            }
            (Event::Touch(TouchEvent::TouchEnd(pos)), Some(origin)) => {
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
                            return Some(Direction::Left);
                        } else if ofs.x > 0 && self.allow_right {
                            return Some(Direction::Right);
                        }
                    }
                } else if abs.x < abs.y && (self.allow_up || self.allow_down) {
                    // Vertical direction.
                    if self.ratio(abs.y) >= Self::THRESHOLD {
                        if ofs.y < 0 && self.allow_up {
                            return Some(Direction::Up);
                        } else if ofs.y > 0 && self.allow_down {
                            return Some(Direction::Down);
                        }
                    }
                };
            }
            _ => {
                // Do nothing.
            }
        }
        None
    }

    fn paint(&mut self) {}

    fn render<'s>(&'s self, _target: &mut impl Renderer<'s>) {}
}
