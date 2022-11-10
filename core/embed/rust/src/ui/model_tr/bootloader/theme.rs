use crate::ui::{
    component::text::TextStyle,
    display::{Color, Font},
};

pub const WHITE: Color = Color::white();
pub const BLACK: Color = Color::black();
pub const BLD_BG: Color = BLACK;
pub const BLD_FG: Color = WHITE;

// Commonly used corner radius (i.e. for buttons).
pub const RADIUS: u8 = 2;

// Size of icons in the UI (i.e. inside buttons).
pub const ICON_SIZE: i32 = 16;

pub const LOGO_EMPTY: &[u8] = include_res!("model_tr/res/trezor_empty.toif");
pub const ICON_TRASH: &[u8] = include_res!("model_tr/res/trash.toif");
pub const ICON_ALERT: &[u8] = include_res!("model_tr/res/alert.toif");
pub const ICON_SPINNER: &[u8] = include_res!("model_tr/res/spinner.toif");
pub const ICON_REDO: &[u8] = include_res!("model_tr/res/redo.toif");
pub const ICON_DOWNLOAD: &[u8] = include_res!("model_tr/res/download.toif");
pub const ICON_EXIT: &[u8] = include_res!("model_tr/res/exit.toif");
pub const ICON_WARN_TITLE: &[u8] = include_res!("model_tr/res/bld_header_warn.toif");

pub const TEXT_NORMAL: TextStyle = TextStyle::new(Font::NORMAL, BLD_FG, BLD_BG, BLD_FG, BLD_FG);
pub const TEXT_BOLD: TextStyle = TextStyle::new(Font::BOLD, BLD_FG, BLD_BG, BLD_FG, BLD_FG);
