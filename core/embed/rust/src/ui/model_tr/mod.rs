use super::{geometry::Rect, layout::simplified::SimplifiedFeatures};

#[cfg(feature = "bootloader")]
pub mod bootloader;
pub mod common_messages;
pub mod component;
pub mod constant;
#[cfg(feature = "micropython")]
pub mod layout;
pub mod screens;
pub mod theme;

pub struct ModelTRFeatures {}

impl SimplifiedFeatures for ModelTRFeatures {
    const SCREEN: Rect = constant::SCREEN;
}
