use crate::{
    trezorhal,
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

/// Storing the icon together with its name
/// Needs to be a tuple-struct, so it can be made `const`
#[derive(Debug, Clone, Copy)]
pub struct NamedToif(pub &'static [u8], pub &'static str);

pub fn toif_info(data: &[u8]) -> Option<(Offset, ToifFormat)> {
    if let Ok(info) = trezorhal::display::toif_info(data) {
        Some((
            Offset::new(
                unwrap!(info.width.try_into()),
                unwrap!(info.height.try_into()),
            ),
            info.format,
        ))
    } else {
        None
    }
}

pub fn icon(icon: &Icon, center: Point, fg_color: Color, bg_color: Color) {
    let r = Rect::from_center_and_size(center, icon.toif.size);
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
#[derive(PartialEq, Eq, Clone, Copy)]
pub struct Toif {
    pub data: &'static [u8],
    pub name: &'static str, // useful for debugging purposes.
    pub size: Offset,
    pub format: ToifFormat,
}

impl Toif {
    pub fn new(named_toif: NamedToif) -> Self {
        let info = unwrap!(toif_info(named_toif.0));
        Self {
            data: named_toif.0[TOIF_HEADER_LENGTH..].as_ref(),
            name: named_toif.1,
            size: info.0,
            format: info.1,
        }
    }

    pub fn width(&self) -> i16 {
        self.size.x
    }

    pub fn height(&self) -> i16 {
        self.size.y
    }

    pub fn uncompress(&self, dest: &mut [u8]) {
        let mut ctx = self.decompression_context(None);
        unwrap!(ctx.uncompress(dest), self.name);
    }

    pub fn decompression_context<'a>(
        &'a self,
        window: Option<&'a mut [u8; UZLIB_WINDOW_SIZE]>,
    ) -> UzlibContext {
        UzlibContext::new(self.data, window)
    }
}

#[derive(PartialEq, Eq, Clone, Copy)]
pub struct Icon {
    pub toif: Toif,
}

impl Icon {
    pub fn new(named_toif: NamedToif) -> Self {
        let toif = Toif::new(named_toif);
        ensure!(toif.format == ToifFormat::GrayScaleEH, toif.name);
        Self { toif }
    }

    /// Display the icon with baseline Point, aligned according to the
    /// `alignment` argument.
    pub fn draw(&self, baseline: Point, alignment: Alignment2D, fg_color: Color, bg_color: Color) {
        let r = Rect::snap(baseline, self.toif.size, alignment);
        icon(self, r.center(), fg_color, bg_color);
    }
}
