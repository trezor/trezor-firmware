use crate::ui::component::{EventCtx, SwipeDirection};
use num_traits::ToPrimitive;

/// Component must implement this trait in order to be part of swipe-based flow.
///
/// Default implementation ignores every swipe.
pub trait Swipable<T> {
    /// Attempt a swipe. Return `Ignored` if the component in its current state
    /// doesn't accept a swipe in that direction. Return `Animating` if
    /// component accepted the swipe and started a transition animation. The
    /// `Return(x)` variant indicates that the current flow should be terminated
    /// with the result `x`.
    fn swipe_start(
        &mut self,
        _ctx: &mut EventCtx,
        _direction: SwipeDirection,
    ) -> SwipableResult<T> {
        SwipableResult::Ignored
    }

    /// Return true when transition animation is finished. SwipeFlow needs to
    /// know this in order to resume normal input processing.
    fn swipe_finished(&self) -> bool {
        true
    }
}

pub enum SwipableResult<T> {
    Ignored,
    Animating,
    Return(T),
}

impl<T> SwipableResult<T> {
    pub fn map<U>(self, func: impl FnOnce(T) -> Option<U>) -> SwipableResult<U> {
        match self {
            SwipableResult::Ignored => SwipableResult::Ignored,
            SwipableResult::Animating => SwipableResult::Animating,
            SwipableResult::Return(x) => {
                if let Some(res) = func(x) {
                    SwipableResult::Return(res)
                } else {
                    SwipableResult::Ignored
                }
            }
        }
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
