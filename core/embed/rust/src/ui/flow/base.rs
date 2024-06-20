use crate::ui::component::{base::AttachType, swipe_detect::SwipeConfig, SwipeDirection};

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
pub enum Decision {
    /// Do nothing, continue with processing next handler.
    Nothing,

    /// Initiate transition to another state, end event processing.
    /// NOTE: it might make sense to include Option<ButtonRequest> here
    Transition(AttachType),

    /// Yield a message to the caller of the flow (i.e. micropython), end event
    /// processing.
    Return(FlowMsg),
}

impl Decision {
    pub fn or_else(self, func: impl FnOnce() -> Self) -> Self {
        match self {
            Decision::Nothing => func(),
            _ => self,
        }
    }
}

/// State transition type.
///
/// Contains a new state (by convention it must be of the same concrete type as
/// the current one) and a Decision object that tells the flow what to do next.
pub type StateChange = (&'static dyn FlowState, Decision);

/// Encodes the flow logic as a set of states, and transitions between them
/// triggered by events and swipes.
pub trait FlowState {
    /// What to do when user swipes on screen and current component doesn't
    /// respond to swipe of that direction.
    ///
    /// By convention, the type of the new state inside the state change must be
    /// Self. This can't be enforced by the type system unfortunately, because
    /// this trait must remain object-safe and so can't refer to Self.
    fn handle_swipe(&'static self, direction: SwipeDirection) -> StateChange;

    /// What to do when the current component emits a message in response to an
    /// event.
    ///
    /// By convention, the type of the new state inside the state change must be
    /// Self. This can't be enforced by the type system unfortunately, because
    /// this trait must remain object-safe and so can't refer to Self.
    fn handle_event(&'static self, msg: FlowMsg) -> StateChange;

    /// Page index of the current state.
    fn index(&'static self) -> usize;
}

/// Helper trait for writing nicer flow logic.
pub trait DecisionBuilder: FlowState + Sized {
    #[inline]
    fn swipe(&'static self, direction: SwipeDirection) -> StateChange {
        (self, Decision::Transition(AttachType::Swipe(direction)))
    }

    #[inline]
    fn swipe_left(&'static self) -> StateChange {
        self.swipe(SwipeDirection::Left)
    }

    #[inline]
    fn swipe_right(&'static self) -> StateChange {
        self.swipe(SwipeDirection::Right)
    }

    #[inline]
    fn swipe_up(&'static self) -> StateChange {
        self.swipe(SwipeDirection::Up)
    }

    #[inline]
    fn swipe_down(&'static self) -> StateChange {
        self.swipe(SwipeDirection::Down)
    }

    #[inline]
    fn transit(&'static self) -> StateChange {
        (self, Decision::Transition(AttachType::Initial))
    }

    #[inline]
    fn do_nothing(&'static self) -> StateChange {
        (self, Decision::Nothing)
    }

    #[inline]
    fn return_msg(&'static self, msg: FlowMsg) -> StateChange {
        (self, Decision::Return(msg))
    }
}

impl<T: FlowState> DecisionBuilder for T {}
