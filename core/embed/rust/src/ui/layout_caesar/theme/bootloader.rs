//! Bootloader theme. It does not use the firmware theme, so that firmware UI
//! changes do not reach the bootloader unnoticed.

use super::super::fonts;
use crate::ui::component::text::TextStyle;
use crate::ui::display::{Color, Font};
use crate::ui::util::include_icon;

pub const BLD_BG: Color = Color::black();
pub const BLD_FG: Color = Color::white();

pub const TEXT_NORMAL: TextStyle =
    TextStyle::new(fonts::FONT_NORMAL, BLD_FG, BLD_BG, BLD_FG, BLD_FG);
pub const TEXT_BOLD: TextStyle = TextStyle::new(fonts::FONT_BOLD, BLD_FG, BLD_BG, BLD_FG, BLD_FG);

pub const FONT_BUTTON: Font = fonts::FONT_NORMAL_UPPER;
pub const FONT_MENU_ITEM: Font = fonts::FONT_NORMAL;
/// Page counter, the same digits as the firmware header font
pub const FONT_PAGE_COUNTER: Font = fonts::FONT_BOLD;

pub const TITLE_AREA_HEIGHT: i16 = 12;

// Button content is 7 pixels high, plus the outline on both sides.
pub const BUTTON_OUTLINE: i16 = 3;
pub const BUTTON_HEIGHT: i16 = 7 + 2 * BUTTON_OUTLINE;
pub const BUTTON_ICON_WIDTH: i16 = BUTTON_HEIGHT;
pub const ARMS_MARGIN: i16 = 2;
/// Width of an icon between the arms of a middle button.
pub const ARMED_ICON_WIDTH: i16 = 24;

include_icon!(ICON_ALERT, "layout_caesar/res/alert.toif");
include_icon!(ICON_SPINNER, "layout_caesar/res/spinner.toif");
include_icon!(ICON_SUCCESS, "layout_caesar/res/success.toif");
include_icon!(ICON_WARN_TITLE, "layout_caesar/res/bld_header_warn.toif");

include_icon!(ICON_ARM_LEFT, "layout_caesar/res/bootloader/arm_left.toif"); // 10*6
include_icon!(
    ICON_ARM_RIGHT,
    "layout_caesar/res/bootloader/arm_right.toif"
); // 10*6
include_icon!(
    ICON_ARROW_LEFT,
    "layout_caesar/res/bootloader/arrow_left.toif"
); // 4*7
include_icon!(
    ICON_ARROW_RIGHT,
    "layout_caesar/res/bootloader/arrow_right.toif"
); // 4*7
include_icon!(ICON_CLOSE, "layout_caesar/res/bootloader/close.toif"); // 8*7
include_icon!(ICON_MENU, "layout_caesar/res/bootloader/menu.toif"); // 6*7
include_icon!(
    ICON_PAGE_SEPARATOR,
    "layout_caesar/res/bootloader/page_separator.toif"
); // 3*5
include_icon!(
    ICON_SELECT,
    "layout_caesar/res/bootloader/mid_button_arrow_down.toif"
); // 8*4
