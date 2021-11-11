use crate::ui::{
    component::text::DefaultTextTheme,
    display::{Color, Font},
};

use super::component::{ButtonStyle, ButtonStyleSheet};

// Font constants.
pub const FONT_NORMAL: Font = Font::new(-1);
pub const FONT_BOLD: Font = Font::new(-2);
pub const FONT_MONO: Font = Font::new(-3);

// Color palette.
pub const WHITE: Color = Color::rgb(255, 255, 255);
pub const BLACK: Color = Color::rgb(0, 0, 0);
pub const GREY_LIGHT: Color = WHITE; // Word/page break characters.
pub const FG: Color = WHITE; // Default foreground (text & icon) color.
pub const BG: Color = BLACK; // Default background color.

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

pub struct T1DefaultText;

impl DefaultTextTheme for T1DefaultText {
    const BACKGROUND_COLOR: Color = BG;
    const TEXT_FONT: Font = FONT_NORMAL;
    const TEXT_COLOR: Color = FG;
    const HYPHEN_FONT: Font = FONT_NORMAL;
    const HYPHEN_COLOR: Color = FG;
    const ELLIPSIS_FONT: Font = FONT_NORMAL;
    const ELLIPSIS_COLOR: Color = FG;

    const NORMAL_FONT: Font = FONT_NORMAL;
    const BOLD_FONT: Font = FONT_BOLD;
    const MONO_FONT: Font = FONT_MONO;
}
