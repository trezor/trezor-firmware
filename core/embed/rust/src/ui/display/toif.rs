use crate::{
    trezorhal::{
        display::ToifFormat,
        uzlib::{UzlibContext, UZLIB_WINDOW_SIZE},
    },
    ui::{
        constant,
        display::{get_color_table, get_offset, pixeldata, pixeldata_dirty, set_window},
        geometry::{Alignment2D, Offset, Point, Rect},
    },
};

use super::Color;

const TOIF_HEADER_LENGTH: usize = 12;

pub fn icon(icon: &Icon, center: Point, fg_color: Color, bg_color: Color) {
    let r = Rect::from_center_and_size(center, icon.toif.size());
    let area = r.translate(get_offset());
    let clamped = area.clamp(constant::screen());
    let colortable = get_color_table(fg_color, bg_color);

    set_window(clamped);

    let mut dest = [0_u8; 1];

    let mut window = [0; UZLIB_WINDOW_SIZE];
    let mut ctx = icon.toif.decompression_context(Some(&mut window));

    for py in area.y0..area.y1 {
        for px in area.x0..area.x1 {
            let p = Point::new(px, py);
            let x = p.x - area.x0;

            if clamped.contains(p) {
                if x % 2 == 0 {
                    unwrap!(ctx.uncompress(&mut dest), "Decompression failed");
                    pixeldata(colortable[(dest[0] & 0xF) as usize]);
                } else {
                    pixeldata(colortable[(dest[0] >> 4) as usize]);
                }
            } else if x % 2 == 0 {
                //continue unzipping but dont write to display
                unwrap!(ctx.uncompress(&mut dest), "Decompression failed");
            }
        }
    }

    pixeldata_dirty();
}

/// Holding toif data and allowing it to draw itself.
/// See https://docs.trezor.io/trezor-firmware/misc/toif.html for data format.
#[derive(PartialEq, Eq, Clone, Copy)]
pub struct Toif {
    data: &'static [u8],
}

impl Toif {
    pub const fn new(data: &'static [u8]) -> Option<Self> {
        if data.len() < TOIF_HEADER_LENGTH || data[0] != b'T' || data[1] != b'O' || data[2] != b'I'
        {
            return None;
        }
        let zdatalen = u32::from_le_bytes([data[8], data[9], data[10], data[11]]) as usize;
        if zdatalen + TOIF_HEADER_LENGTH != data.len() {
            return None;
        }
        Some(Self { data })
    }

    pub const fn format(&self) -> ToifFormat {
        match self.data[3] {
            b'f' => ToifFormat::FullColorBE,
            b'g' => ToifFormat::GrayScaleOH,
            b'F' => ToifFormat::FullColorLE,
            b'G' => ToifFormat::GrayScaleEH,
            _ => panic!(),
        }
    }

    pub const fn width(&self) -> i16 {
        u16::from_le_bytes([self.data[4], self.data[5]]) as i16
    }

    pub const fn height(&self) -> i16 {
        u16::from_le_bytes([self.data[6], self.data[7]]) as i16
    }

    pub const fn size(&self) -> Offset {
        Offset::new(self.width(), self.height())
    }

    pub fn zdata(&self) -> &'static [u8] {
        &self.data[TOIF_HEADER_LENGTH..]
    }

    pub fn uncompress(&self, dest: &mut [u8]) {
        let mut ctx = self.decompression_context(None);
        unwrap!(ctx.uncompress(dest));
    }

    pub fn decompression_context<'a>(
        &'a self,
        window: Option<&'a mut [u8; UZLIB_WINDOW_SIZE]>,
    ) -> UzlibContext {
        UzlibContext::new(self.zdata(), window)
    }
}

#[derive(PartialEq, Eq, Clone, Copy)]
pub struct Icon {
    pub toif: Toif,
}

impl Icon {
    pub fn new(data: &'static [u8]) -> Self {
        let toif = unwrap!(Toif::new(data));
        assert!(toif.format() == ToifFormat::GrayScaleEH);
        Self { toif }
    }

    /// Display the icon with baseline Point, aligned according to the
    /// `alignment` argument.
    pub fn draw(&self, baseline: Point, alignment: Alignment2D, fg_color: Color, bg_color: Color) {
        let r = Rect::snap(baseline, self.toif.size(), alignment);
        icon(self, r.center(), fg_color, bg_color);
    }
}
