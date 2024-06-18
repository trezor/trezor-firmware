use crate::{error, ui::geometry::Point};
use core::convert::TryInto;

#[cfg(feature = "touch")]
use crate::ui::component::SwipeDirection;

#[derive(Copy, Clone, PartialEq, Eq)]
#[cfg_attr(feature = "debug", derive(ufmt::derive::uDebug))]
pub enum PhysicalButton {
    Left,
    Right,
}

#[derive(Copy, Clone, PartialEq, Eq)]
#[cfg_attr(feature = "debug", derive(ufmt::derive::uDebug))]
pub enum ButtonEvent {
    /// Button pressed down.
    /// ▼ * | * ▼
    ButtonPressed(PhysicalButton),
    /// Button released up.
    /// ▲ * | * ▲
    ButtonReleased(PhysicalButton),
    HoldStarted,
    HoldEnded,
}

impl ButtonEvent {
    pub fn new(event: u32, button: u32) -> Result<Self, error::Error> {
        let button = match button {
            0 => PhysicalButton::Left,
            1 => PhysicalButton::Right,
            _ => return Err(error::Error::OutOfRange),
        };
        let result = match event {
            1 => Self::ButtonPressed(button),
            2 => Self::ButtonReleased(button),
            _ => return Err(error::Error::OutOfRange),
        };
        Ok(result)
    }
}

#[derive(Copy, Clone, PartialEq, Eq)]
#[cfg_attr(feature = "debug", derive(ufmt::derive::uDebug))]
pub enum TouchEvent {
    /// A person has started touching the screen at given absolute coordinates.
    /// `TouchMove` will usually follow, and `TouchEnd` should finish the
    /// interaction.
    TouchStart(Point),
    /// Touch has moved into a different point on the screen.
    TouchMove(Point),
    /// Touch has ended at a point on the screen.
    TouchEnd(Point),
    /// Touch event has been suppressed by more important event - i.e. Swipe.
    TouchAbort,
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

#[derive(Copy, Clone, PartialEq, Eq)]
#[cfg_attr(feature = "debug", derive(ufmt::derive::uDebug))]
pub enum USBEvent {
    /// USB host has connected/disconnected.
    Connected(bool),
}

#[cfg(feature = "touch")]
#[derive(Copy, Clone, PartialEq, Eq)]
#[cfg_attr(feature = "debug", derive(ufmt::derive::uDebug))]
pub enum SwipeEvent {
    Move(SwipeDirection, i16),
    End(SwipeDirection),
}
