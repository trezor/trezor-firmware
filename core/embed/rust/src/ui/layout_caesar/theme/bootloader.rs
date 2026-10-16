use super::super::fonts;
pub use super::super::theme::{BLACK, WHITE};
use crate::ui::component::text::TextStyle;
use crate::ui::display::Color;
use crate::ui::util::include_icon;

pub const BLD_BG: Color = BLACK;
pub const BLD_FG: Color = WHITE;

include_icon!(ICON_ALERT, "layout_caesar/res/alert.toif");
include_icon!(ICON_SPINNER, "layout_caesar/res/spinner.toif");
include_icon!(ICON_SUCCESS, "layout_caesar/res/success.toif");

pub const TEXT_NORMAL: TextStyle =
    TextStyle::new(fonts::FONT_NORMAL, BLD_FG, BLD_BG, BLD_FG, BLD_FG);
pub const TEXT_BOLD: TextStyle = TextStyle::new(fonts::FONT_BOLD, BLD_FG, BLD_BG, BLD_FG, BLD_FG);
