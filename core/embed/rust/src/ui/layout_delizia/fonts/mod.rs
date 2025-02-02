mod font_robotomono_medium_21;
mod font_ttsatoshi_demibold_18;
mod font_ttsatoshi_demibold_21;
mod font_ttsatoshi_demibold_42;

use font_robotomono_medium_21::Font_RobotoMono_Medium_21_info;
use font_ttsatoshi_demibold_18::Font_TTSatoshi_DemiBold_18_info;
use font_ttsatoshi_demibold_21::Font_TTSatoshi_DemiBold_21_info;
use font_ttsatoshi_demibold_42::Font_TTSatoshi_DemiBold_42_info;

pub const FONT_DEMIBOLD: crate::ui::display::Font = &Font_TTSatoshi_DemiBold_21_info;
pub const FONT_MONO: crate::ui::display::Font = &Font_RobotoMono_Medium_21_info;
pub const FONT_BIG: crate::ui::display::Font = &Font_TTSatoshi_DemiBold_42_info;
pub const FONT_SUB: crate::ui::display::Font = &Font_TTSatoshi_DemiBold_18_info;
