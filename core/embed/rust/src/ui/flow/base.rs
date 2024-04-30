use crate::ui::{
    component::{EventCtx, SwipeDirection},
    geometry::Offset,
};
use num_traits::ToPrimitive;

impl SwipeDirection {
    pub fn as_offset(self, size: Offset) -> Offset {
        match self {
            SwipeDirection::Up => Offset::y(-size.y),
            SwipeDirection::Down => Offset::y(size.y),
            SwipeDirection::Left => Offset::x(-size.x),
            SwipeDirection::Right => Offset::x(size.x),
        }
    }
}

/// Component must implement this trait in order to be part of swipe-based flow.
///
/// Default implementation ignores every swipe.
pub trait Swipable {
    /// Attempt a swipe. Return false if component in its current state doesn't
    /// accept a swipe in the given direction. Start a transition animation
    /// if true is returned.
    fn swipe_start(&mut self, _ctx: &mut EventCtx, _direction: SwipeDirection) -> bool {
        false
    }

    /// Return true when transition animation is finished. SwipeFlow needs to
    /// know this in order to resume normal input processing.
    fn swipe_finished(&self) -> bool {
        true
    }
}

/// Component::Msg for component parts of a flow. Converting results of
/// different screens to a shared type makes things easier to work with.
///
/// Also currently the type for message emitted by Flow::event to
/// micropython. They don't need to be the same.
#[derive(Copy, Clone)]
pub enum FlowMsg {
    Confirmed,
    Cancelled,
    Info,
    Choice(usize),
}

/// Composable event handler result.
#[derive(Copy, Clone)]
pub enum Decision<Q> {
    /// Do nothing, continue with processing next handler.
    Nothing,

    /// Initiate transition to another state, end event processing.
    /// NOTE: it might make sense to include Option<ButtonRequest> here
    Goto(Q, SwipeDirection),

    /// Yield a message to the caller of the flow (i.e. micropython), end event
    /// processing.
    Return(FlowMsg),
}

impl<Q> Decision<Q> {
    pub fn or_else(self, func: impl FnOnce() -> Self) -> Self {
        match self {
            Decision::Nothing => func(),
            _ => self,
        }
    }
}

/// Encodes the flow logic as a set of states, and transitions between them
/// triggered by events and swipes. Roughly the C in MVC.
pub trait FlowState
where
    Self: Sized + Copy + Eq + ToPrimitive,
{
    /// There needs to be a mapping from states to indices of the FlowStore
    /// array. Default implementation works for states that are enums, the
    /// FlowStore has to have number of elements equal to number of states.
    fn index(&self) -> usize {
        unwrap!(self.to_usize())
    }

    /// What to do when user swipes on screen and current component doesn't
    /// respond to swipe of that direction.
    fn handle_swipe(&self, direction: SwipeDirection) -> Decision<Self>;

    /// What to do when the current component emits a message in response to an
    /// event.
    fn handle_event(&self, msg: FlowMsg) -> Decision<Self>;
}
