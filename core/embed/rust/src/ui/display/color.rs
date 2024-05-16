use crate::ui::lerp::Lerp;

#[derive(Copy, Clone, PartialEq, Eq)]
pub struct Color(u16);

impl Color {
    pub const fn from_u16(val: u16) -> Self {
        Self(val)
    }
    pub const fn from_u32(val: u32) -> Self {
        Self::rgb(
            ((val >> 16) & 0xFF) as u8,
            ((val >> 8) & 0xFF) as u8,
            (val & 0xFF) as u8,
        )
    }

    pub const fn rgb(r: u8, g: u8, b: u8) -> Self {
        let r = (r as u16 & 0xF8) << 8;
        let g = (g as u16 & 0xFC) << 3;
        let b = (b as u16 & 0xF8) >> 3;
        Self(r | g | b)
    }

    pub const fn luminance(self) -> u32 {
        (self.r() as u32 * 299) / 1000
            + (self.g() as u32 * 587) / 1000
            + (self.b() as u32 * 114) / 1000
    }

    pub const fn rgba(bg: Color, r: u8, g: u8, b: u8, alpha: u16) -> Self {
        let r_u16 = r as u16;
        let g_u16 = g as u16;
        let b_u16 = b as u16;

        let r = ((256 - alpha) * bg.r() as u16 + alpha * r_u16) >> 8;
        let g = ((256 - alpha) * bg.g() as u16 + alpha * g_u16) >> 8;
        let b = ((256 - alpha) * bg.b() as u16 + alpha * b_u16) >> 8;

        let r = (r & 0xF8) << 8;
        let g = (g & 0xFC) << 3;
        let b = (b & 0xF8) >> 3;
        Self(r | g | b)
    }

    pub const fn alpha(bg: Color, alpha: u16) -> Self {
        Self::rgba(bg, 0xFF, 0xFF, 0xFF, alpha)
    }

    pub const fn r(self) -> u8 {
        (self.0 >> 8) as u8 & 0xF8
    }

    pub const fn g(self) -> u8 {
        (self.0 >> 3) as u8 & 0xFC
    }

    pub const fn b(self) -> u8 {
        (self.0 << 3) as u8 & 0xF8
    }

    pub fn to_u16(self) -> u16 {
        self.0
    }

    pub fn to_u32(self) -> u32 {
        ((self.r() as u32) << 16) | ((self.g() as u32) << 8) | (self.b() as u32) | 0xff000000
    }

    pub fn hi_byte(self) -> u8 {
        (self.to_u16() >> 8) as u8
    }

    pub fn lo_byte(self) -> u8 {
        (self.to_u16() & 0xFF) as u8
    }

    pub fn negate(self) -> Self {
        Self(!self.0)
    }

    pub const fn white() -> Self {
        Self::rgb(255, 255, 255)
    }

    pub const fn black() -> Self {
        Self::rgb(0, 0, 0)
    }

    /// Blends the color of `self` with the color of `fg` using specified
    /// `alpha` value (ranging from 0 to 255).
    ///
    /// If `alpha` equals 0, the background color (`self`) is used.
    /// If `alpha` equals 255, the foreground color (`fg`) is used.
    pub fn blend(self, fg: Color, alpha: u8) -> Color {
        let fg_mul = alpha as u16;
        let bg_mul = (255 - alpha) as u16;
        let r = (fg.r() as u16) * fg_mul + (self.r() as u16) * bg_mul;
        let g = (fg.g() as u16) * fg_mul + (self.g() as u16) * bg_mul;
        let b = (fg.b() as u16) * fg_mul + (self.b() as u16) * bg_mul;
        Color::rgb((r / 255) as u8, (g / 255) as u8, (b / 255) as u8)
    }
}

impl Lerp for Color {
    fn lerp(a: Self, b: Self, t: f32) -> Self {
        let r = u8::lerp(a.r(), b.r(), t);
        let g = u8::lerp(a.g(), b.g(), t);
        let b = u8::lerp(a.b(), b.b(), t);
        Color::rgb(r, g, b)
    }
}

impl From<u16> for Color {
    fn from(val: u16) -> Self {
        Self(val)
    }
}

impl From<Color> for u16 {
    fn from(val: Color) -> Self {
        val.to_u16()
    }
}

impl From<u32> for Color {
    fn from(val: u32) -> Self {
        Self::from_u32(val)
    }
}

impl From<Color> for u32 {
    fn from(val: Color) -> Self {
        val.to_u32()
    }
}
