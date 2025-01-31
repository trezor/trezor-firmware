use crate::ui::{component::text::TextStyle, display::Color, util::include_icon};

use super::super::fonts;
pub use super::super::theme::{BLACK, WHITE};

pub const BLD_BG: Color = BLACK;
pub const BLD_FG: Color = WHITE;

include_icon!(ICON_TRASH, "layout_caesar/res/trash.toif");
include_icon!(ICON_ALERT, "layout_caesar/res/alert.toif");
include_icon!(ICON_SPINNER, "layout_caesar/res/spinner.toif");
include_icon!(ICON_SUCCESS, "layout_caesar/res/success.toif");
include_icon!(ICON_REDO, "layout_caesar/res/redo.toif");
include_icon!(ICON_EXIT, "layout_caesar/res/exit.toif");

pub const TEXT_NORMAL: TextStyle =
    TextStyle::new(fonts::FONT_NORMAL, BLD_FG, BLD_BG, BLD_FG, BLD_FG);
pub const TEXT_BOLD: TextStyle = TextStyle::new(fonts::FONT_BOLD, BLD_FG, BLD_BG, BLD_FG, BLD_FG);
