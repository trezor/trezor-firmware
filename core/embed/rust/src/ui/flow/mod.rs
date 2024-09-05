pub mod base;
pub mod page;
mod swipe;

pub use crate::ui::component::FlowMsg;
pub use base::{FlowController, Swipable};
pub use page::SwipePage;
pub use swipe::SwipeFlow;
