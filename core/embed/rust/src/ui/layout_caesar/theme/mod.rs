use crate::ui::{
    component::{
        text::{layout::Chunks, TextStyle},
        LineBreaking, PageBreaking,
    },
    display::{Color, Font},
    geometry::Offset,
    util::include_icon,
};

use num_traits::FromPrimitive;

pub mod bootloader;

// Color palette.
pub const WHITE: Color = Color::white();
pub const BLACK: Color = Color::black();
pub const FG: Color = WHITE; // Default foreground (text & icon) color.
pub const BG: Color = BLACK; // Default background color.

// Font constants.
pub const FONT_BUTTON: Font = Font::NORMAL_UPPER;
pub const FONT_HEADER: Font = Font::BOLD_UPPER;
pub const FONT_CHOICE_ITEMS: Font = Font::BIG;

// Text constants.
pub const TEXT_NORMAL: TextStyle = TextStyle::new(Font::NORMAL, FG, BG, FG, FG)
    .with_page_breaking(PageBreaking::CutAndInsertEllipsisBoth)
    .with_ellipsis_icon(ICON_NEXT_PAGE, ELLIPSIS_ICON_MARGIN)
    .with_prev_page_icon(ICON_PREV_PAGE, PREV_PAGE_ICON_MARGIN);
pub const TEXT_BIG: TextStyle = TextStyle::new(Font::BIG, FG, BG, FG, FG);
pub const TEXT_DEMIBOLD: TextStyle = TextStyle::new(Font::DEMIBOLD, FG, BG, FG, FG);
pub const TEXT_BOLD: TextStyle = TextStyle::new(Font::BOLD, FG, BG, FG, FG)
    .with_page_breaking(PageBreaking::CutAndInsertEllipsisBoth)
    .with_ellipsis_icon(ICON_NEXT_PAGE, ELLIPSIS_ICON_MARGIN)
    .with_prev_page_icon(ICON_PREV_PAGE, PREV_PAGE_ICON_MARGIN);
pub const TEXT_BOLD_UPPER: TextStyle = TextStyle::new(Font::BOLD_UPPER, FG, BG, FG, FG)
    .with_page_breaking(PageBreaking::CutAndInsertEllipsisBoth)
    .with_ellipsis_icon(ICON_NEXT_PAGE, ELLIPSIS_ICON_MARGIN)
    .with_prev_page_icon(ICON_PREV_PAGE, PREV_PAGE_ICON_MARGIN);
pub const TEXT_MONO: TextStyle = TextStyle::new(Font::MONO, FG, BG, FG, FG)
    .with_page_breaking(PageBreaking::CutAndInsertEllipsisBoth)
    .with_ellipsis_icon(ICON_NEXT_PAGE, ELLIPSIS_ICON_MARGIN)
    .with_prev_page_icon(ICON_PREV_PAGE, PREV_PAGE_ICON_MARGIN);
/// Mono data text does not have hyphens
pub const TEXT_MONO_DATA: TextStyle =
    TEXT_MONO.with_line_breaking(LineBreaking::BreakWordsNoHyphen);
pub const TEXT_MONO_ADDRESS_CHUNKS: TextStyle = TEXT_MONO_DATA
    .with_chunks(MONO_CHUNKS)
    .with_line_spacing(2)
    .with_ellipsis_icon(ICON_NEXT_PAGE, -2);

// Chunks for this model
pub const MONO_CHUNKS: Chunks = Chunks::new(4, 4);

/// Convert Python-side numeric id to a `TextStyle`.
pub fn textstyle_number(num: i32) -> &'static TextStyle {
    let font = Font::from_i32(-num);
    match font {
        Some(Font::BOLD) => &TEXT_BOLD,
        Some(Font::DEMIBOLD) => &TEXT_BOLD,
        Some(Font::NORMAL) => &TEXT_NORMAL,
        _ => &TEXT_MONO_DATA,
    }
}

// Firmware icons
include_icon!(ICON_ARM_LEFT, "layout_caesar/res/arm_left.toif"); // 10*6
include_icon!(ICON_ARM_RIGHT, "layout_caesar/res/arm_right.toif"); // 10*6
include_icon!(ICON_ARROW_LEFT, "layout_caesar/res/arrow_left.toif"); // 4*7
include_icon!(ICON_ARROW_LEFT_BIG, "layout_caesar/res/arrow_left_big.toif"); // 8*7
include_icon!(ICON_ARROW_RIGHT, "layout_caesar/res/arrow_right.toif"); // 4*7
include_icon!(
    ICON_ARROW_RIGHT_FAT,
    "layout_caesar/res/arrow_right_fat.toif"
); // 4*8
include_icon!(ICON_ARROW_UP, "layout_caesar/res/arrow_up.toif"); // 8*4
include_icon!(ICON_ARROW_DOWN, "layout_caesar/res/arrow_down.toif"); // 7*4
include_icon!(ICON_ARROW_BACK_UP, "layout_caesar/res/arrow_back_up.toif"); // 8*8
include_icon!(ICON_BIN, "layout_caesar/res/bin.toif"); // 10*10
include_icon!(ICON_CANCEL, "layout_caesar/res/cancel.toif"); // 7*7
include_icon!(ICON_COINJOIN, "layout_caesar/res/coinjoin.toif"); // 12*12
include_icon!(ICON_DELETE, "layout_caesar/res/delete.toif"); // 9*7
include_icon!(ICON_DEVICE_NAME, "layout_caesar/res/device_name.toif"); // 116*18
include_icon!(ICON_EYE, "layout_caesar/res/eye_round.toif"); // 12*7
include_icon!(ICON_LOCK, "layout_caesar/res/lock.toif"); // 10*10
include_icon!(ICON_LOCK_SMALL, "layout_caesar/res/lock_small.toif"); // 6*7
include_icon!(ICON_LOGO, "layout_caesar/res/logo_22_33.toif"); // 22*33
include_icon!(ICON_LOGO_EMPTY, "layout_caesar/res/logo_22_33_empty.toif");
include_icon!(ICON_NEXT_PAGE, "layout_caesar/res/next_page.toif"); // 9*8
include_icon!(ICON_PREV_PAGE, "layout_caesar/res/prev_page.toif"); // 8*10
include_icon!(ICON_SPACE, "layout_caesar/res/space.toif"); // 12*3
include_icon!(ICON_TICK, "layout_caesar/res/tick.toif"); // 8*6
include_icon!(ICON_TICK_FAT, "layout_caesar/res/tick_fat.toif"); // 8*6
include_icon!(ICON_WARNING, "layout_caesar/res/warning.toif"); // 11*12
include_icon!(ICON_WARN_TITLE, "layout_caesar/res/bld_header_warn.toif");

// checklist settings
pub const CHECKLIST_SPACING: i16 = 5;
pub const CHECKLIST_CHECK_WIDTH: i16 = 12;
pub const CHECKLIST_CURRENT_OFFSET: Offset = Offset::x(3);

// Button height is constant for both text and icon buttons.
// It is a combination of content and (optional) outline/border.
// It is not possible to have icons 7*7, therefore having 8*8
// with empty LEFT column and BOTTOM row.
pub const BUTTON_CONTENT_HEIGHT: i16 = 7;
pub const BUTTON_OUTLINE: i16 = 3;
pub const BUTTON_HEIGHT: i16 = BUTTON_CONTENT_HEIGHT + 2 * BUTTON_OUTLINE;
pub const BUTTON_ICON_WIDTH: i16 = BUTTON_HEIGHT;
pub const TITLE_AREA_HEIGHT: i16 = 12;
pub const ARMS_MARGIN: i16 = 2;

// How many pixels should be between text and icons.
pub const ELLIPSIS_ICON_MARGIN: i16 = 4;
pub const PREV_PAGE_ICON_MARGIN: i16 = 6;
