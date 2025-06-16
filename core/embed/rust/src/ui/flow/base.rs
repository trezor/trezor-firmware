use crate::{
    error::Error,
    micropython::obj::Obj,
    ui::{
        component::{base::AttachType, swipe_detect::SwipeConfig},
        geometry::Direction,
        util::Pager,
    },
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
    Return(Result<Obj, Error>),
}

impl Decision {
    pub fn or_else(self, func: impl FnOnce() -> Self) -> Self {
        match self {
            Decision::Nothing => func(),
            _ => self,
        }
    }
}

impl From<FlowMsg> for Decision {
    fn from(msg: FlowMsg) -> Self {
        Self::Return(msg.try_into())
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
#[derive(Copy, Clone, PartialEq, Eq)]
pub struct FlowState(usize);

impl FlowState {
    pub(super) fn new(index: usize) -> Self {
        Self(index)
    }

    pub(super) fn index(&self) -> usize {
        self.0
    }

    #[inline]
    pub fn swipe(self, direction: Direction) -> Decision {
        Decision::Transition(self, AttachType::Swipe(direction))
    }

    #[inline]
    pub fn swipe_left(self) -> Decision {
        self.swipe(Direction::Left)
    }

    #[inline]
    pub fn swipe_right(self) -> Decision {
        self.swipe(Direction::Right)
    }

    #[inline]
    pub fn swipe_up(self) -> Decision {
        self.swipe(Direction::Up)
    }

    #[inline]
    pub fn swipe_down(self) -> Decision {
        self.swipe(Direction::Down)
    }

    #[inline]
    pub fn goto(self) -> Decision {
        Decision::Transition(self, AttachType::Initial)
    }

    #[inline]
    pub fn do_nothing(self) -> Decision {
        Decision::Nothing
    }
}
