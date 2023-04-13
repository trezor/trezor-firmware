use crate::ui::{
    component::text::TextStyle,
    display::{Color, Font},
};

pub const WHITE: Color = Color::white();
pub const BLACK: Color = Color::black();
pub const BLD_BG: Color = BLACK;
pub const BLD_FG: Color = WHITE;

pub const LOGO_EMPTY: &[u8] = include_res!("model_tr/res/logo_22_33_empty.toif");
pub const ICON_TRASH: &[u8] = include_res!("model_tr/res/trash.toif");
pub const ICON_ALERT: &[u8] = include_res!("model_tr/res/alert.toif");
pub const ICON_SPINNER: &[u8] = include_res!("model_tr/res/spinner.toif");
pub const ICON_REDO: &[u8] = include_res!("model_tr/res/redo.toif");
pub const ICON_EXIT: &[u8] = include_res!("model_tr/res/exit.toif");
pub const ICON_INFO: &[u8] = include_res!("model_tr/res/info.toif");

pub const TEXT_NORMAL: TextStyle = TextStyle::new(Font::NORMAL, BLD_FG, BLD_BG, BLD_FG, BLD_FG);
pub const TEXT_BOLD: TextStyle = TextStyle::new(Font::BOLD, BLD_FG, BLD_BG, BLD_FG, BLD_FG);
