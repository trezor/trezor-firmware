mod font_pixeloperator_bold_8;
mod font_pixeloperator_regular_8;
mod font_pixeloperatormono_regular_8;
mod font_unifont_bold_16;
mod font_unifont_regular_16;

use font_pixeloperator_bold_8::{
    Font_PixelOperator_Bold_8_info, Font_PixelOperator_Bold_8_upper_info,
};
use font_pixeloperator_regular_8::{
    Font_PixelOperator_Regular_8_info, Font_PixelOperator_Regular_8_upper_info,
};
use font_pixeloperatormono_regular_8::Font_PixelOperatorMono_Regular_8_info;
use font_unifont_bold_16::Font_Unifont_Bold_16_info;
use font_unifont_regular_16::Font_Unifont_Regular_16_info;

pub const FONT_NORMAL: crate::ui::display::Font = &Font_PixelOperator_Regular_8_info;
pub const FONT_BOLD: crate::ui::display::Font = &Font_PixelOperator_Bold_8_info;
pub const FONT_DEMIBOLD: crate::ui::display::Font = &Font_Unifont_Bold_16_info;
pub const FONT_MONO: crate::ui::display::Font = &Font_PixelOperatorMono_Regular_8_info;
pub const FONT_BIG: crate::ui::display::Font = &Font_Unifont_Regular_16_info;
pub const FONT_NORMAL_UPPER: crate::ui::display::Font = &Font_PixelOperator_Regular_8_upper_info;
pub const FONT_BOLD_UPPER: crate::ui::display::Font = &Font_PixelOperator_Bold_8_upper_info;
// TODO: remove SUB
pub const FONT_SUB: crate::ui::display::Font = &Font_PixelOperator_Regular_8_info;
