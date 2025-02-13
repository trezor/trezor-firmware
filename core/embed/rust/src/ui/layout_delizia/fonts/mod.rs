#[cfg(not(feature = "bootloader"))]
mod font_robotomono_medium_21;
#[cfg(not(feature = "bootloader"))]
mod font_ttsatoshi_demibold_18;
mod font_ttsatoshi_demibold_21;
#[cfg(not(feature = "bootloader"))]
mod font_ttsatoshi_demibold_42;

#[cfg(feature = "bootloader")]
mod font_tthoves_bold_17;

#[cfg(not(feature = "bootloader"))]
use font_robotomono_medium_21::Font_RobotoMono_Medium_21_info;
#[cfg(feature = "bootloader")]
use font_tthoves_bold_17::Font_TTHoves_Bold_17_upper_info;
#[cfg(not(feature = "bootloader"))]
use font_ttsatoshi_demibold_18::Font_TTSatoshi_DemiBold_18_info;
use font_ttsatoshi_demibold_21::Font_TTSatoshi_DemiBold_21_info;
#[cfg(not(feature = "bootloader"))]
use font_ttsatoshi_demibold_42::Font_TTSatoshi_DemiBold_42_info;

pub const FONT_DEMIBOLD: crate::ui::display::Font = &Font_TTSatoshi_DemiBold_21_info;

#[cfg(feature = "bootloader")]
pub const FONT_MONO: crate::ui::display::Font = FONT_DEMIBOLD;
#[cfg(not(feature = "bootloader"))]
pub const FONT_MONO: crate::ui::display::Font = &Font_RobotoMono_Medium_21_info;
#[cfg(feature = "bootloader")]
pub const FONT_BIG: crate::ui::display::Font = FONT_DEMIBOLD;
#[cfg(not(feature = "bootloader"))]
pub const FONT_BIG: crate::ui::display::Font = &Font_TTSatoshi_DemiBold_42_info;
#[cfg(feature = "bootloader")]
pub const FONT_SUB: crate::ui::display::Font = &Font_TTHoves_Bold_17_upper_info;
#[cfg(not(feature = "bootloader"))]
pub const FONT_SUB: crate::ui::display::Font = &Font_TTSatoshi_DemiBold_18_info;
