mod loader;

/// Prototype scaffolding for lockscreen animation experiments. Debug builds
/// only — see `ui::util::lockscreen_anim_kind`.
#[cfg(feature = "ui_debug")]
mod halftone;
#[cfg(feature = "ui_debug")]
mod hatch_squares;
#[cfg(feature = "ui_debug")]
mod moire;
#[cfg(feature = "ui_debug")]
mod particles;
#[cfg(feature = "ui_debug")]
mod proto_util;
#[cfg(feature = "ui_debug")]
mod sand_clock;
#[cfg(feature = "ui_debug")]
mod strings;
#[cfg(feature = "ui_debug")]
mod stripe_gradient;

#[cfg(feature = "ui_debug")]
pub use halftone::Halftone;
#[cfg(feature = "ui_debug")]
pub use hatch_squares::HatchSquares;
#[cfg(feature = "ui_debug")]
pub use moire::{Moire, MoireDir};
#[cfg(feature = "ui_debug")]
pub use particles::Particles;
#[cfg(feature = "ui_debug")]
pub use sand_clock::SandClock;
#[cfg(feature = "ui_debug")]
pub use strings::Strings;
#[cfg(feature = "ui_debug")]
pub use stripe_gradient::{StripeDir, StripeGradient, BLOCK, SMOOTH};

#[cfg(feature = "ui_overlay")]
mod unlock_overlay;

#[cfg(feature = "ui_overlay")]
mod keyboard_overlay;

#[cfg(feature = "ui_overlay")]
pub use unlock_overlay::UnlockOverlay;

#[cfg(feature = "ui_overlay")]
pub use keyboard_overlay::KeyboardOverlay;

pub use loader::{render_loader, LoaderRange};
