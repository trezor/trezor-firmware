use crate::ui::{
    component::{base::AttachType, swipe_detect::SwipeConfig},
    geometry::Direction,
    util::Pager,
};

pub use crate::ui::component::FlowMsg;

pub trait Swipable {
    fn get_swipe_config(&self) -> SwipeConfig;

    fn get_pager(&self) -> Pager;
}

/// Composable event handler result.
#[derive(Clone)]
pub enum Decision {
    /// Do nothing, continue with processing next handler.
    Nothing,

    /// Initiate transition to another state, end event processing.
    /// NOTE: it might make sense to include Option<ButtonRequest> here
    Transition(FlowState, AttachType),

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

/// Flow state type
///
/// It is a static dyn reference to a FlowController, which, due to this, is
/// required to be a plain enum type. Its concrete values then are individual
/// states.
///
/// By convention, a Decision emitted by a controller must embed a reference to
/// the same type of controller.
pub type FlowState = &'static dyn FlowController;

/// Encodes the flow logic as a set of states, and transitions between them
/// triggered by events and swipes.
pub trait FlowController {
    /// What to do when user swipes on screen and current component doesn't
    /// respond to swipe of that direction.
    ///
    /// By convention, the type of the new state inside the state change must be
    /// Self. This can't be enforced by the type system unfortunately, because
    /// this trait must remain object-safe and so can't refer to Self.
    fn handle_swipe(&'static self, direction: Direction) -> Decision;

    /// What to do when the current component emits a message in response to an
    /// event.
    ///
    /// By convention, the type of the new state inside the state change must be
    /// Self. This can't be enforced by the type system unfortunately, because
    /// this trait must remain object-safe and so can't refer to Self.
    fn handle_event(&'static self, msg: FlowMsg) -> Decision;

    /// Page index of the current state.
    fn index(&'static self) -> usize;
}

/// Helper trait for writing nicer flow logic.
pub trait DecisionBuilder: FlowController + Sized {
    #[inline]
    fn swipe(&'static self, direction: Direction) -> Decision {
        Decision::Transition(self, AttachType::Swipe(direction))
    }

    #[inline]
    fn swipe_left(&'static self) -> Decision {
        self.swipe(Direction::Left)
    }

    #[inline]
    fn swipe_right(&'static self) -> Decision {
        self.swipe(Direction::Right)
    }

    #[inline]
    fn swipe_up(&'static self) -> Decision {
        self.swipe(Direction::Up)
    }

    #[inline]
    fn swipe_down(&'static self) -> Decision {
        self.swipe(Direction::Down)
    }

    #[inline]
    fn goto(&'static self) -> Decision {
        Decision::Transition(self, AttachType::Initial)
    }

    #[inline]
    fn do_nothing(&'static self) -> Decision {
        Decision::Nothing
    }

    #[inline]
    fn return_msg(&'static self, msg: FlowMsg) -> Decision {
        Decision::Return(msg)
    }
}

impl<T: FlowController> DecisionBuilder for T {}
