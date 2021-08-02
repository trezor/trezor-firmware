use crate::ui::display::{Color, Font};

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
            background_color: FG,
            border_horiz: true,
        },
        active: &ButtonStyle {
            font: FONT_BOLD,
            text_color: FG,
            background_color: BG,
            border_horiz: true,
        },
        disabled: &ButtonStyle {
            font: FONT_BOLD,
            text_color: FG,
            background_color: BG,
            border_horiz: true,
        },
    }
}

pub fn button_cancel() -> ButtonStyleSheet {
    ButtonStyleSheet {
        normal: &ButtonStyle {
            font: FONT_BOLD,
            text_color: FG,
            background_color: BG,
            border_horiz: false,
        },
        active: &ButtonStyle {
            font: FONT_BOLD,
            text_color: BG,
            background_color: FG,
            border_horiz: false,
        },
        disabled: &ButtonStyle {
            font: FONT_BOLD,
            text_color: BG,
            background_color: FG,
            border_horiz: false,
        },
    }
}
