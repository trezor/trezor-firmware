use crate::ui::{
    component::{text::TextStyle, LineBreaking},
    display::{Color, Font, toif::Icon},
    geometry::Offset,
};

use num_traits::FromPrimitive;

// Color palette.
pub const WHITE: Color = Color::white();
pub const BLACK: Color = Color::black();
pub const FG: Color = WHITE; // Default foreground (text & icon) color.
pub const BG: Color = BLACK; // Default background color.

// Font constants.
pub const FONT_BUTTON: Font = Font::MONO;
pub const FONT_HEADER: Font = Font::BOLD;
pub const FONT_CHOICE_ITEMS: Font = Font::NORMAL;

// Text constants.
pub const TEXT_NORMAL: TextStyle = TextStyle::new(Font::NORMAL, FG, BG, FG, FG);
pub const TEXT_DEMIBOLD: TextStyle = TextStyle::new(Font::DEMIBOLD, FG, BG, FG, FG);
pub const TEXT_BOLD: TextStyle = TextStyle::new(Font::BOLD, FG, BG, FG, FG)
    .with_ellipsis_icon(Icon::new(ICON_NEXT_PAGE), ELLIPSIS_ICON_MARGIN)
    .with_prev_page_icon(Icon::new(ICON_PREV_PAGE), PREV_PAGE_ICON_MARGIN);
pub const TEXT_MONO: TextStyle = TextStyle::new(Font::MONO, FG, BG, FG, FG)
    .with_ellipsis_icon(Icon::new(ICON_NEXT_PAGE), ELLIPSIS_ICON_MARGIN)
    .with_prev_page_icon(Icon::new(ICON_PREV_PAGE), PREV_PAGE_ICON_MARGIN);
/// Mono data text does not have hyphens
pub const TEXT_MONO_DATA: TextStyle =
    TEXT_MONO.with_line_breaking(LineBreaking::BreakWordsNoHyphen);

/// Convert Python-side numeric id to a `TextStyle`.
/// Using only BOLD or MONO fonts.
pub fn textstyle_number_bold_or_mono(num: i32) -> &'static TextStyle {
    let font = Font::from_i32(-num);
    match font {
        Some(Font::BOLD) => &TEXT_BOLD,
        Some(Font::DEMIBOLD) => &TEXT_BOLD,
        _ => &TEXT_MONO,
    }
}

// BLD icons
pub const LOGO_EMPTY: &[u8] = include_res!("model_tr/res/trezor_empty.toif");
pub const ICON_FAIL: &[u8] = include_res!("model_tr/res/fail.toif");

// Firmware icons
pub const ICON_ARM_LEFT: &[u8] = include_res!("model_tr/res/arm_left.toif"); // 6*10
pub const ICON_ARM_RIGHT: &[u8] = include_res!("model_tr/res/arm_right.toif"); // 6*10
pub const ICON_ARROW_LEFT: &[u8] = include_res!("model_tr/res/arrow_left.toif"); // 6*10
pub const ICON_ARROW_RIGHT: &[u8] = include_res!("model_tr/res/arrow_right.toif"); // 6*10
pub const ICON_ARROW_RIGHT_FAT: &[u8] = include_res!("model_tr/res/arrow_right_fat.toif"); // 4*8
pub const ICON_ARROW_UP: &[u8] = include_res!("model_tr/res/arrow_up.toif"); // 10*6
pub const ICON_ARROW_DOWN: &[u8] = include_res!("model_tr/res/arrow_down.toif"); // 10*6
pub const ICON_ARROW_BACK_UP: &[u8] = include_res!("model_tr/res/arrow_back_up.toif"); // 8*8
pub const ICON_BIN: &[u8] = include_res!("model_tr/res/bin.toif"); // 10*10
pub const ICON_CANCEL: &[u8] = include_res!("model_tr/res/cancel_no_outline.toif"); // 8*8
pub const ICON_DELETE: &[u8] = include_res!("model_tr/res/delete.toif"); // 10*7
pub const ICON_EYE: &[u8] = include_res!("model_tr/res/eye_round.toif"); // 12*7
pub const ICON_LOCK: &[u8] = include_res!("model_tr/res/lock.toif"); // 10*10
pub const ICON_NEXT_PAGE: &[u8] = include_res!("model_tr/res/next_page.toif"); // 10*8
pub const ICON_PREV_PAGE: &[u8] = include_res!("model_tr/res/prev_page.toif"); // 8*10
pub const ICON_SPACE: &[u8] = include_res!("model_tr/res/space.toif"); // 12*3
pub const ICON_SUCCESS: &[u8] = include_res!("model_tr/res/success.toif");
pub const ICON_TICK: &[u8] = include_res!("model_tr/res/tick.toif"); // 8*6
pub const ICON_TICK_FAT: &[u8] = include_res!("model_tr/res/tick_fat.toif"); // 8*6
pub const ICON_WARNING: &[u8] = include_res!("model_tr/res/warning.toif"); // 12*12

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

/// Full-size QR code.
/// Accounting for little larger QR code than the screen,
/// to fit taproot addresses (top and bottom row will not be visible).
// TODO: test if this is visible, as it had problems on T1
pub const QR_SIDE_MAX: i16 = 66;

// How many pixels should be between text and icons.
pub const ELLIPSIS_ICON_MARGIN: i16 = 4;
pub const PREV_PAGE_ICON_MARGIN: i16 = 6;
