use crate::ui::{
    component::text::TextStyle,
    display::{Color, Font},
    model_tr::{
        component::{ButtonStyle, ButtonStyleSheet},
        theme::{BG, BLACK, FG, WHITE},
    },
};

pub const BLD_BG: Color = BLACK;
pub const BLD_FG: Color = WHITE;

// Commonly used corner radius (i.e. for buttons).
pub const RADIUS: u8 = 2;

// Size of icons in the UI (i.e. inside buttons).
pub const ICON_SIZE: i32 = 16;

pub fn bld_button_default() -> ButtonStyleSheet {
    ButtonStyleSheet {
        normal: &ButtonStyle {
            font: Font::NORMAL,
            text_color: BG,
            border_horiz: true,
        },
        active: &ButtonStyle {
            font: Font::NORMAL,
            text_color: FG,
            border_horiz: true,
        },
    }
}

pub fn bld_button_cancel() -> ButtonStyleSheet {
    ButtonStyleSheet {
        normal: &ButtonStyle {
            font: Font::NORMAL,
            text_color: FG,
            border_horiz: false,
        },
        active: &ButtonStyle {
            font: Font::NORMAL,
            text_color: BG,
            border_horiz: false,
        },
    }
}

pub const TEXT_NORMAL: TextStyle = TextStyle::new(Font::NORMAL, BLD_FG, BLD_BG, BLD_FG, BLD_FG);
pub const TEXT_BOLD: TextStyle = TextStyle::new(Font::NORMAL, BLD_FG, BLD_BG, BLD_FG, BLD_FG);
