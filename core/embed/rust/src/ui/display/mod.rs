pub mod color;
pub mod font;
pub mod image;
pub mod toif;

use super::geometry::{Offset, Point, Rect};

#[cfg(feature = "backlight")]
use crate::{time::Duration, trezorhal::time};

use crate::{strutil::TString, trezorhal::display};

#[cfg(feature = "backlight")]
use crate::ui::lerp::Lerp;

#[cfg(feature = "backlight")]
use crate::{time::Stopwatch, ui::util::animation_disabled};

// Reexports
pub use crate::ui::display::toif::Icon;
pub use color::Color;
pub use font::{Font, Glyph, GlyphMetrics};

pub const LOADER_MIN: u16 = 0;
pub const LOADER_MAX: u16 = 1000;

pub fn backlight() -> u8 {
    display::backlight(-1) as u8
}

#[cfg(feature = "backlight")]
pub fn set_backlight(val: u8) {
    display::backlight(val as i32);
}

#[cfg(feature = "backlight")]
pub fn fade_backlight(target: u8) {
    const FADE_DURATION_MS: u32 = 50;
    fade_backlight_duration(target, FADE_DURATION_MS);
}

#[cfg(feature = "backlight")]
pub fn fade_backlight_duration(target: u8, duration_ms: u32) {
    let target = target as i32;
    let current = backlight() as i32;
    let duration = Duration::from_millis(duration_ms);

    if animation_disabled() {
        set_backlight(target as u8);
        return;
    }

    let timer = Stopwatch::new_started();

    while timer.elapsed() < duration {
        let elapsed = timer.elapsed();
        let val = i32::lerp(current, target, elapsed / duration);
        set_backlight(val as u8);
        time::sleep(Duration::from_millis(1));
    }
    //account for imprecise rounding
    set_backlight(target as u8);
}

#[cfg(not(feature = "backlight"))]
pub fn set_backlight(_: u8) {}

#[cfg(not(feature = "backlight"))]
pub fn fade_backlight(_: u8) {}

#[cfg(not(feature = "backlight"))]
pub fn fade_backlight_duration(_: u8, _: u32) {}

#[derive(Clone)]
pub struct TextOverlay {
    area: Rect,
    text: TString<'static>,
    font: Font,
    max_height: i16,
    baseline: i16,
}

impl TextOverlay {
    pub fn new<T: Into<TString<'static>>>(text: T, font: Font) -> Self {
        let area = Rect::zero();

        Self {
            area,
            text: text.into(),
            font,
            max_height: font.text_max_height(),
            baseline: font.text_baseline(),
        }
    }

    pub fn set_text<T: Into<TString<'static>>>(&mut self, text: T) {
        self.text = text.into();
    }

    pub fn get_text(&self) -> TString<'static> {
        self.text
    }

    // baseline relative to the underlying render area
    pub fn place(&mut self, baseline: Point) {
        let text_width = self.text.map(|t| self.font.text_width(t));
        let text_height = self.font.text_height();

        let text_area_start = baseline + Offset::new(-(text_width / 2), -text_height);
        let text_area_end = baseline + Offset::new(text_width / 2, 0);
        let area = Rect::new(text_area_start, text_area_end);

        self.area = area;
    }
}

pub fn sync() {
    display::sync();
}

pub fn refresh() {
    display::refresh();
}
