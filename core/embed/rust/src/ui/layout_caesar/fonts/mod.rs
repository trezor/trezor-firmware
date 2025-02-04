mod font_pixeloperator_bold_8;
mod font_pixeloperator_regular_8;
#[cfg(not(feature = "bootloader"))]
mod font_pixeloperatormono_regular_8;
#[cfg(not(feature = "bootloader"))]
mod font_unifont_bold_16;
#[cfg(not(feature = "bootloader"))]
mod font_unifont_regular_16;

use font_pixeloperator_bold_8::Font_PixelOperator_Bold_8_info;
#[cfg(not(feature = "bootloader"))]
use font_pixeloperator_bold_8::Font_PixelOperator_Bold_8_upper_info;
use font_pixeloperator_regular_8::{
    Font_PixelOperator_Regular_8_info, Font_PixelOperator_Regular_8_upper_info,
};
#[cfg(not(feature = "bootloader"))]
use font_pixeloperatormono_regular_8::Font_PixelOperatorMono_Regular_8_info;
#[cfg(not(feature = "bootloader"))]
use font_unifont_bold_16::Font_Unifont_Bold_16_info;
#[cfg(not(feature = "bootloader"))]
use font_unifont_regular_16::Font_Unifont_Regular_16_info;

pub const FONT_NORMAL: crate::ui::display::Font = &Font_PixelOperator_Regular_8_info;
pub const FONT_BOLD: crate::ui::display::Font = &Font_PixelOperator_Bold_8_info;
pub const FONT_NORMAL_UPPER: crate::ui::display::Font = &Font_PixelOperator_Regular_8_upper_info;
#[cfg(feature = "bootloader")]
pub const FONT_DEMIBOLD: crate::ui::display::Font = FONT_NORMAL;
#[cfg(not(feature = "bootloader"))]
pub const FONT_DEMIBOLD: crate::ui::display::Font = &Font_Unifont_Bold_16_info;
#[cfg(feature = "bootloader")]
pub const FONT_MONO: crate::ui::display::Font = FONT_NORMAL;
#[cfg(not(feature = "bootloader"))]
pub const FONT_MONO: crate::ui::display::Font = &Font_PixelOperatorMono_Regular_8_info;
#[cfg(feature = "bootloader")]
pub const FONT_BIG: crate::ui::display::Font = FONT_NORMAL;
#[cfg(not(feature = "bootloader"))]
pub const FONT_BIG: crate::ui::display::Font = &Font_Unifont_Regular_16_info;
#[cfg(feature = "bootloader")]
pub const FONT_BOLD_UPPER: crate::ui::display::Font = FONT_NORMAL_UPPER;
#[cfg(not(feature = "bootloader"))]
pub const FONT_BOLD_UPPER: crate::ui::display::Font = &Font_PixelOperator_Bold_8_upper_info;
