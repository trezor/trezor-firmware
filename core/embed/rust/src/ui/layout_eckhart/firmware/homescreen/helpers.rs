use super::super::constant::{HEIGHT, WIDTH};
use super::super::theme;
use crate::io::BinaryData;
use crate::ui::display::image::ImageInfo;
use crate::ui::geometry::Rect;
use crate::ui::layout::util::get_user_custom_image;
use crate::ui::shape::{self, Renderer};

pub const SHADOW_HEIGHT: i16 = 54;

pub fn check_homescreen_format(image: BinaryData) -> bool {
    match ImageInfo::parse(image) {
        ImageInfo::Jpeg(info) => {
            info.width() == WIDTH && info.height() == HEIGHT && info.mcu_height() <= 16
        }
        _ => false,
    }
}

pub(super) fn get_homescreen_image() -> Option<BinaryData<'static>> {
    if let Ok(image) = get_user_custom_image() {
        if check_homescreen_format(image) {
            return Some(image);
        }
    }
    None
}

pub fn render_pill_shaped_background<'s>(area: Rect, target: &mut impl Renderer<'s>) {
    const SHADOW_ALPHA: u8 = 230; // 90%
    shape::Bar::new(area)
        .with_bg(theme::BG)
        .with_fg(theme::BG)
        .with_radius(area.height() / 2)
        .with_alpha(SHADOW_ALPHA)
        .render(target);
}
