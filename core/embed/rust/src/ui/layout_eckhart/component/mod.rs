mod button;
mod error;
mod fuel_gauge;
mod update_screen;
mod welcome_screen;

pub use button::{Button, ButtonContent, ButtonMsg, ButtonStyle, ButtonStyleSheet};
pub use error::ErrorScreen;
pub use fuel_gauge::FuelGauge;
pub use update_screen::UpdateScreen;
pub use welcome_screen::WelcomeScreen;

use super::{fonts, theme};
use crate::ui::{
    display::Font,
    geometry::{Alignment2D, Offset, Point},
    shape::{self, Renderer},
};

pub fn render_logo<'s>(target: &mut impl Renderer<'s>) {
    const TEXT_ORIGIN: Point = Point::new(24, 76);
    const STRIDE: i16 = 46;
    const ICON_ORIGIN: Point = Point::new(24, 147);
    const FONT: Font = fonts::FONT_SATOSHI_REGULAR_38;

    shape::Text::new(TEXT_ORIGIN, "Trezor", FONT)
        .with_fg(theme::GREY_LIGHT)
        .render(target);
    shape::Text::new(TEXT_ORIGIN + Offset::y(STRIDE), "Safe", FONT)
        .with_fg(theme::GREY_LIGHT)
        .render(target);
    shape::ToifImage::new(ICON_ORIGIN, theme::ICON_SEVEN.toif)
        .with_fg(theme::GREY_DARK)
        .with_align(Alignment2D::TOP_LEFT)
        .render(target);
}
