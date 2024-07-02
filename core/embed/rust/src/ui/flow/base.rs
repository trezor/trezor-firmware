use crate::ui::component::{base::AttachType, swipe_detect::SwipeConfig, SwipeDirection};
use num_traits::ToPrimitive;

pub trait Swipable {
    fn get_swipe_config(&self) -> SwipeConfig;

    fn get_internal_page_count(&self) -> usize;
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
    Goto(Q, AttachType),

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
/// triggered by events and swipes.
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
