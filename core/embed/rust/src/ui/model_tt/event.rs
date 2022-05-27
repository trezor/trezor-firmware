use core::convert::TryInto;

use crate::{error, ui::geometry::Point};

#[derive(Copy, Clone, PartialEq, Eq)]
pub enum TouchEvent {
    /// A person has started touching the screen at given absolute coordinates.
    /// `TouchMove` will usually follow, and `TouchEnd` should finish the
    /// interaction.
    TouchStart(Point),
    /// Touch has moved into a different point on the screen.
    TouchMove(Point),
    /// Touch has ended at a point on the screen.
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
