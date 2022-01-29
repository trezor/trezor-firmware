use core::convert::TryInto;

use crate::{error, ui::geometry::Point};

#[derive(Copy, Clone, PartialEq, Eq)]
pub enum TouchEvent {
    TouchStart(Point),
    TouchMove(Point),
    TouchEnd(Point),
}

impl TouchEvent {
    pub fn new(event: u32, x: u32, y: u32) -> Result<Self, error::Error> {
        let point = Point::new(x.try_into()?, y.try_into()?);
        let result = match event {
            1 => Self::TouchStart(point),
            2 => Self::TouchMove(point),
            4 => Self::TouchEnd(point),
            _ => return Err(error::Error::OutOfRange),
        };
        Ok(result)
    }
}
