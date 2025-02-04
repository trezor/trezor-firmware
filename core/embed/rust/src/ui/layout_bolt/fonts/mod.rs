#[cfg(not(feature = "bootloader"))]
mod font_robotomono_medium_20;
mod font_tthoves_bold_17;
#[cfg(not(feature = "bootloader"))]
mod font_tthoves_demibold_21;
mod font_tthoves_regular_21;

#[cfg(not(feature = "bootloader"))]
use font_robotomono_medium_20::Font_RobotoMono_Medium_20_info;
use font_tthoves_bold_17::Font_TTHoves_Bold_17_upper_info;
#[cfg(not(feature = "bootloader"))]
use font_tthoves_demibold_21::Font_TTHoves_DemiBold_21_info;
use font_tthoves_regular_21::Font_TTHoves_Regular_21_info;

pub const FONT_NORMAL: crate::ui::display::Font = &Font_TTHoves_Regular_21_info;
pub const FONT_BOLD_UPPER: crate::ui::display::Font = &Font_TTHoves_Bold_17_upper_info;
#[cfg(feature = "bootloader")]
pub const FONT_DEMIBOLD: crate::ui::display::Font = FONT_NORMAL;
#[cfg(not(feature = "bootloader"))]
pub const FONT_DEMIBOLD: crate::ui::display::Font = &Font_TTHoves_DemiBold_21_info;
#[cfg(feature = "bootloader")]
pub const FONT_MONO: crate::ui::display::Font = FONT_NORMAL;
#[cfg(not(feature = "bootloader"))]
pub const FONT_MONO: crate::ui::display::Font = &Font_RobotoMono_Medium_20_info;
