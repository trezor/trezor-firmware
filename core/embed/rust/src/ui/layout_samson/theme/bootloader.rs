use crate::ui::{
    component::text::TextStyle,
    display::{Color, Font},
    util::include_icon,
};

pub use super::super::theme::{BLACK, WHITE};

pub const BLD_BG: Color = BLACK;
pub const BLD_FG: Color = WHITE;

include_icon!(ICON_TRASH, "layout_samson/res/trash.toif");
include_icon!(ICON_ALERT, "layout_samson/res/alert.toif");
include_icon!(ICON_SPINNER, "layout_samson/res/spinner.toif");
include_icon!(ICON_SUCCESS, "layout_samson/res/success.toif");
include_icon!(ICON_REDO, "layout_samson/res/redo.toif");
include_icon!(ICON_EXIT, "layout_samson/res/exit.toif");

pub const TEXT_NORMAL: TextStyle = TextStyle::new(Font::NORMAL, BLD_FG, BLD_BG, BLD_FG, BLD_FG);
pub const TEXT_BOLD: TextStyle = TextStyle::new(Font::BOLD, BLD_FG, BLD_BG, BLD_FG, BLD_FG);
