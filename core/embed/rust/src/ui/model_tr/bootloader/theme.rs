use crate::ui::{
    component::text::TextStyle,
    display::{Color, Font},
    model_tr::{
        component::{ButtonStyleSheet},
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
    ButtonStyleSheet::new(
        BG,
        FG,
        false,
        false,
        None,
        None,
    )
}

pub fn bld_button_cancel() -> ButtonStyleSheet {
    ButtonStyleSheet::new(
        FG,
        BG,
        false,
        false,
        None,
        None,
    )
}

pub const TEXT_NORMAL: TextStyle = TextStyle::new(Font::NORMAL, BLD_FG, BLD_BG, BLD_FG, BLD_FG);
pub const TEXT_BOLD: TextStyle = TextStyle::new(Font::NORMAL, BLD_FG, BLD_BG, BLD_FG, BLD_FG);
