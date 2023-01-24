use crate::ui::{
    component::{text::TextStyle, LineBreaking},
    display::{Color, Font, IconAndName},
    geometry::Offset,
};

use num_traits::FromPrimitive;

// Color palette.
pub const FG: Color = Color::white(); // Default foreground (text & icon) color.
pub const BG: Color = Color::black(); // Default background color.

// Font constants.
pub const FONT_BUTTON: Font = Font::MONO;
pub const FONT_HEADER: Font = Font::BOLD;
pub const FONT_CHOICE_ITEMS: Font = Font::NORMAL;

// Text constants.
pub const TEXT_NORMAL: TextStyle = TextStyle::new(Font::NORMAL, FG, BG, FG, FG);
pub const TEXT_DEMIBOLD: TextStyle = TextStyle::new(Font::DEMIBOLD, FG, BG, FG, FG);
pub const TEXT_BOLD: TextStyle = TextStyle::new(Font::BOLD, FG, BG, FG, FG);
/// Mono without ellipsis icon
pub const TEXT_MONO_RAW: TextStyle = TextStyle::new(Font::MONO, FG, BG, FG, FG);
/// Mono text has the icon ellipsis
pub const TEXT_MONO: TextStyle = TEXT_MONO_RAW.with_ellipsis_icon(ICON_NEXT_PAGE.0);
/// Mono data text does not have hyphens
pub const TEXT_MONO_DATA: TextStyle =
    TEXT_MONO.with_line_breaking(LineBreaking::BreakWordsNoHyphen);
pub const TEXT_HEADER: TextStyle = TextStyle::new(Font::BOLD, FG, BG, FG, FG);

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

// Icons with their names for debugging purposes
pub const ICON_ARM_LEFT: IconAndName =
    IconAndName::new(include_res!("model_tr/res/arm_left.toif"), "arm_left"); // 6*10
pub const ICON_ARM_RIGHT: IconAndName =
    IconAndName::new(include_res!("model_tr/res/arm_right.toif"), "arm_right"); // 6*10
pub const ICON_ARROW_LEFT: IconAndName =
    IconAndName::new(include_res!("model_tr/res/arrow_left.toif"), "arrow_left"); // 6*10
pub const ICON_ARROW_RIGHT: IconAndName =
    IconAndName::new(include_res!("model_tr/res/arrow_right.toif"), "arrow_right"); // 6*10
pub const ICON_ARROW_RIGHT_FAT: IconAndName = IconAndName::new(
    include_res!("model_tr/res/arrow_right_fat.toif"),
    "arrow_right_fat",
); // 4*8
pub const ICON_ARROW_UP: IconAndName =
    IconAndName::new(include_res!("model_tr/res/arrow_up.toif"), "arrow_up"); // 10*6
pub const ICON_ARROW_DOWN: IconAndName =
    IconAndName::new(include_res!("model_tr/res/arrow_down.toif"), "arrow_down"); // 10*6
pub const ICON_ARROW_BACK_UP: IconAndName = IconAndName::new(
    include_res!("model_tr/res/arrow_back_up.toif"),
    "arrow_back_up",
); // 8*8
pub const ICON_BIN: IconAndName = IconAndName::new(include_res!("model_tr/res/bin.toif"), "bin"); // 10*10
pub const ICON_CANCEL: IconAndName = IconAndName::new(
    include_res!("model_tr/res/cancel_no_outline.toif"),
    "cancel",
); // 8*8
pub const ICON_DELETE: IconAndName =
    IconAndName::new(include_res!("model_tr/res/delete.toif"), "delete"); // 10*7
pub const ICON_EYE: IconAndName =
    IconAndName::new(include_res!("model_tr/res/eye_round.toif"), "eye"); // 12*7
pub const ICON_LOCK: IconAndName = IconAndName::new(include_res!("model_tr/res/lock.toif"), "lock"); // 10*10
pub const ICON_NEXT_PAGE: IconAndName =
    IconAndName::new(include_res!("model_tr/res/next_page.toif"), "next_page"); // 10*8
pub const ICON_PREV_PAGE: IconAndName =
    IconAndName::new(include_res!("model_tr/res/prev_page.toif"), "prev_page"); // 8*10
pub const ICON_SPACE: IconAndName =
    IconAndName::new(include_res!("model_tr/res/space.toif"), "space"); // 12*3
pub const ICON_SUCCESS: IconAndName =
    IconAndName::new(include_res!("model_tr/res/success.toif"), "success");
pub const ICON_TICK: IconAndName = IconAndName::new(include_res!("model_tr/res/tick.toif"), "tick"); // 8*6
pub const ICON_TICK_FAT: IconAndName =
    IconAndName::new(include_res!("model_tr/res/tick_fat.toif"), "tick_fat"); // 8*6
pub const ICON_WARNING: IconAndName =
    IconAndName::new(include_res!("model_tr/res/warning.toif"), "warning"); // 12*12

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
pub const QR_SIDE_MAX: i16 = 66;
