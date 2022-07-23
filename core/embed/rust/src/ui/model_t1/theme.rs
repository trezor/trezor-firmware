use crate::ui::{
    component::text::{formatted::FormattedFonts, TextStyle},
    display::{Color, Font},
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

pub const TEXT_NORMAL: TextStyle = TextStyle::new(FONT_NORMAL, FG, BG, FG, FG);
pub const TEXT_MEDIUM: TextStyle = TextStyle::new(FONT_MEDIUM, FG, BG, FG, FG);
pub const TEXT_BOLD: TextStyle = TextStyle::new(FONT_BOLD, FG, BG, FG, FG);
pub const TEXT_MONO: TextStyle = TextStyle::new(FONT_MONO, FG, BG, FG, FG);

pub const FORMATTED: FormattedFonts = FormattedFonts {
    normal: FONT_NORMAL,
    medium: FONT_MEDIUM,
    bold: FONT_BOLD,
    mono: FONT_MONO,
};
