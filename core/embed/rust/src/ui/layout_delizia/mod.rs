use super::{geometry::Rect, CommonUI};

#[cfg(feature = "ui_debug_overlay")]
use super::{
    display::Color,
    geometry::{Alignment, Alignment2D, Offset, Point},
    shape, DebugOverlay,
};

#[cfg(feature = "ui_debug_overlay")]
use crate::strutil::ShortString;

use theme::backlight;

#[cfg(feature = "bootloader")]
pub mod bootloader;
pub mod component;
pub mod constant;
pub mod theme;

#[cfg(feature = "micropython")]
pub mod component_msg_obj;
pub mod cshape;
#[cfg(feature = "micropython")]
pub mod flow;
pub mod fonts;
pub mod screens;
#[cfg(feature = "micropython")]
pub mod ui_firmware;

pub struct UIDelizia;

impl CommonUI for UIDelizia {
    #[cfg(feature = "backlight")]
    fn fadein() {
        crate::ui::display::fade_backlight_duration(backlight::get_backlight_normal(), 150);
    }

    #[cfg(feature = "backlight")]
    fn fadeout() {
        crate::ui::display::fade_backlight_duration(backlight::get_backlight_dim(), 150);
    }

    #[cfg(feature = "backlight")]
    fn backlight_on() {
        crate::ui::display::set_backlight(backlight::get_backlight_normal());
    }

    #[cfg(feature = "backlight")]
    fn get_backlight_none() -> u8 {
        backlight::get_backlight_none()
    }

    #[cfg(feature = "backlight")]
    fn get_backlight_normal() -> u8 {
        backlight::get_backlight_normal()
    }

    #[cfg(feature = "backlight")]
    fn get_backlight_low() -> u8 {
        backlight::get_backlight_low()
    }

    #[cfg(feature = "backlight")]
    fn get_backlight_dim() -> u8 {
        backlight::get_backlight_dim()
    }

    #[cfg(feature = "backlight")]
    fn get_backlight_max() -> u8 {
        backlight::get_backlight_max()
    }

    const SCREEN: Rect = constant::SCREEN;

    fn screen_fatal_error(title: &str, msg: &str, footer: &str) {
        screens::screen_fatal_error(title, msg, footer);
    }

    fn screen_boot_stage_2(fade_in: bool) {
        screens::screen_boot_stage_2(fade_in);
    }

    #[cfg(feature = "ui_debug_overlay")]
    fn render_debug_overlay<'s>(target: &mut impl shape::Renderer<'s>, info: DebugOverlay) {
        let mut text = ShortString::new();
        let t1 = info.render_time.min(99999) as u32;
        let t2 = info.refresh_time.min(99999) as u32;
        unwrap!(ufmt::uwrite!(
            text,
            "{}.{}|{}.{}",
            t1 / 1000,
            (t1 % 1000) / 100,
            t2 / 1000,
            (t2 % 1000) / 100
        ));
        let font = fonts::FONT_SUB;
        let size = Offset::new(
            font.visible_text_width("00.0|00.0"),
            font.visible_text_height("0"),
        );
        let pos = Point::new(constant::WIDTH, 0);
        let r = Rect::snap(pos, size, Alignment2D::TOP_RIGHT);
        shape::Bar::new(r)
            .with_alpha(192)
            .with_bg(Color::black())
            .render(target);
        shape::Text::new(r.bottom_right(), &text, font)
            .with_align(Alignment::End)
            .with_fg(Color::rgb(255, 255, 0))
            .render(target);
    }
}
