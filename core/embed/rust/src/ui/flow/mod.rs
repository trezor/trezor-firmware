pub mod base;
pub mod page;
mod swipe;

use super::{model_mercury::ModelMercuryFeatures, UIFeaturesCommon};

pub use base::{FlowMsg, FlowState, Swipable};
pub use page::SwipePage;

pub type SwipeFlow = swipe::SwipeFlow<<ModelMercuryFeatures as UIFeaturesCommon>::Display>;
