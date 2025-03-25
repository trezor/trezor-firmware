/// Font definitions for the Eckhart layout
/// Allowed in Bootloader and Firmware:
///     - FONT_SATOSHI_MEDIUM_26
///     - FONT_SATOSHI_REGULAR_38
/// Allowed only in Firmware:
///     - FONT_MONO_LIGHT_30
///     - FONT_MONO_MEDIUM_38
///     - FONT_SATOSHI_EXTRALIGHT_46
///     - FONT_SATOSHI_EXTRALIGHT_72
///     - FONT_SATOSHI_REGULAR_22

#[cfg(feature = "micropython")]
mod font_robotomono_light_30;
#[cfg(feature = "micropython")]
mod font_robotomono_medium_38;
#[cfg(feature = "micropython")]
mod font_ttsatoshi_extralight_46;
#[cfg(feature = "micropython")]
mod font_ttsatoshi_extralight_72;
mod font_ttsatoshi_medium_26;
#[cfg(feature = "micropython")]
mod font_ttsatoshi_regular_22;
mod font_ttsatoshi_regular_38;

#[cfg(feature = "micropython")]
use font_robotomono_light_30::Font_RobotoMono_Light_30_info;
#[cfg(feature = "micropython")]
use font_robotomono_medium_38::Font_RobotoMono_Medium_38_info;
#[cfg(feature = "micropython")]
use font_ttsatoshi_extralight_46::Font_TTSatoshi_ExtraLight_46_info;
#[cfg(feature = "micropython")]
use font_ttsatoshi_extralight_72::Font_TTSatoshi_ExtraLight_72_info;
use font_ttsatoshi_medium_26::Font_TTSatoshi_Medium_26_info;
#[cfg(feature = "micropython")]
use font_ttsatoshi_regular_22::Font_TTSatoshi_Regular_22_info;
use font_ttsatoshi_regular_38::Font_TTSatoshi_Regular_38_info;

#[cfg(feature = "micropython")]
pub const FONT_MONO_LIGHT_30: crate::ui::display::Font = &Font_RobotoMono_Light_30_info;
#[cfg(feature = "micropython")]
pub const FONT_MONO_MEDIUM_38: crate::ui::display::Font = &Font_RobotoMono_Medium_38_info;
#[cfg(feature = "micropython")]
pub const FONT_SATOSHI_EXTRALIGHT_46: crate::ui::display::Font = &Font_TTSatoshi_ExtraLight_46_info;
#[cfg(feature = "micropython")]
pub const FONT_SATOSHI_EXTRALIGHT_72: crate::ui::display::Font = &Font_TTSatoshi_ExtraLight_72_info;
pub const FONT_SATOSHI_MEDIUM_26: crate::ui::display::Font = &Font_TTSatoshi_Medium_26_info;
#[cfg(feature = "micropython")]
pub const FONT_SATOSHI_REGULAR_22: crate::ui::display::Font = &Font_TTSatoshi_Regular_22_info;
pub const FONT_SATOSHI_REGULAR_38: crate::ui::display::Font = &Font_TTSatoshi_Regular_38_info;
