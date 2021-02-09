use crate::ui::math::{Point, Rect};

pub trait Component {
    type Msg;

    fn widget(&mut self) -> &mut Widget;

    fn area(&mut self) -> Rect {
        self.widget().area
    }

    fn set_area(&mut self, area: Rect) {
        self.widget().area = area;
    }

    fn event(&mut self, _event: Event) -> Option<Self::Msg> {
        None
    }

    fn paint(&mut self) {}
}

pub struct Widget {
    pub area: Rect,
}

impl Widget {
    pub fn new(area: Rect) -> Self {
        Self { area }
    }
}

#[derive(Copy, Clone, PartialEq, Eq)]
pub enum Event {
    TouchStart(Point),
    TouchMove(Point),
    TouchEnd(Point),
}
