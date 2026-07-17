pub mod base;
pub mod page;
mod swipe;

pub use base::{FlowController, Swipable};
pub use page::SwipePage;
pub use swipe::SwipeFlow;

pub use crate::ui::component::FlowMsg;
