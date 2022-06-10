use crate::ui::{
    component::text::layout::DefaultTextTheme,
    display::{Color, Font},
    model_tr::component::{LoaderStyle, LoaderStyleSheet},
};

use super::component::{ButtonStyle, ButtonStyleSheet};

// Font constants.
pub const FONT_NORMAL: Font = Font::new(-1);
pub const FONT_MEDIUM: Font = Font::new(-5);
pub const FONT_BOLD: Font = Font::new(-2);
pub const FONT_MONO: Font = Font::new(-3);

// Color palette.
pub const WHITE: Color = Color::rgb(255, 255, 255);
pub const BLACK: Color = Color::rgb(0, 0, 0);
pub const GREY_LIGHT: Color = WHITE; // Word/page break characters.
pub const FG: Color = WHITE; // Default foreground (text & icon) color.
pub const BG: Color = BLACK; // Default background color.

pub const ICON_SUCCESS: &[u8] = include_res!("model_tr/res/success.toif");
pub const ICON_FAIL: &[u8] = include_res!("model_tr/res/fail.toif");

pub fn button_default() -> ButtonStyleSheet {
    ButtonStyleSheet {
        normal: &ButtonStyle {
            font: FONT_BOLD,
            text_color: BG,
            border_horiz: true,
        },
        active: &ButtonStyle {
            font: FONT_BOLD,
            text_color: FG,
            border_horiz: true,
        },
    }
}

pub fn button_cancel() -> ButtonStyleSheet {
    ButtonStyleSheet {
        normal: &ButtonStyle {
            font: FONT_BOLD,
            text_color: FG,
            border_horiz: false,
        },
        active: &ButtonStyle {
            font: FONT_BOLD,
            text_color: BG,
            border_horiz: false,
        },
    }
}

pub fn loader_default() -> LoaderStyleSheet {
    LoaderStyleSheet {
        normal: &LoaderStyle {
            font: FONT_NORMAL,
            fg_color: FG,
            bg_color: BG,
        },
    }
}

pub struct TRDefaultText;

impl DefaultTextTheme for TRDefaultText {
    const BACKGROUND_COLOR: Color = BG;
    const TEXT_FONT: Font = FONT_NORMAL;
    const TEXT_COLOR: Color = FG;
    const HYPHEN_FONT: Font = FONT_NORMAL;
    const HYPHEN_COLOR: Color = FG;
    const ELLIPSIS_FONT: Font = FONT_NORMAL;
    const ELLIPSIS_COLOR: Color = FG;

    const NORMAL_FONT: Font = FONT_NORMAL;
    const MEDIUM_FONT: Font = FONT_MEDIUM;
    const BOLD_FONT: Font = FONT_BOLD;
    const MONO_FONT: Font = FONT_MONO;
}
