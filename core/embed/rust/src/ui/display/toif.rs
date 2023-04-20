use crate::{
    trezorhal::{
        display::ToifFormat,
        uzlib::{UzlibContext, UZLIB_WINDOW_SIZE},
    },
    ui::{
        component::image::Image,
        constant,
        display::{get_color_table, get_offset, pixeldata, pixeldata_dirty, set_window},
        geometry::{Alignment2D, Offset, Point, Rect},
    },
};

use crate::ui::geometry::TOP_LEFT;
#[cfg(feature = "dma2d")]
use crate::{
    trezorhal::{
        buffers::BufferLine16bpp,
        dma2d::{dma2d_setup_16bpp, dma2d_start, dma2d_wait_for_transfer},
    },
    ui::display::process_buffer,
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

#[no_mangle]
extern "C" fn display_image(
    x: cty::int16_t,
    y: cty::int16_t,
    data: *const cty::uint8_t,
    data_len: cty::uint32_t,
) {
    let data_slice = unsafe { core::slice::from_raw_parts(data, data_len as usize) };
    let image = Image::new(data_slice);
    image.draw(Point::new(x, y), TOP_LEFT);
}

#[cfg(feature = "dma2d")]
pub fn image(image: &Image, center: Point) {
    let r = Rect::from_center_and_size(center, image.toif.size());
    let area = r.translate(get_offset());
    let clamped = area.clamp(constant::screen());

    set_window(clamped);

    let mut window = [0; UZLIB_WINDOW_SIZE];
    let mut ctx = image.toif.decompression_context(Some(&mut window));

    let mut b1 = BufferLine16bpp::get_cleared();
    let mut b2 = BufferLine16bpp::get_cleared();

    let mut decompressed_lines = 0;
    let clamp_x = if clamped.x0 > area.x0 {
        area.x0 - clamped.x0
    } else {
        0
    };

    dma2d_setup_16bpp();

    for y in clamped.y0..clamped.y1 {
        let img_buffer_used = if y % 2 == 0 { &mut b1 } else { &mut b2 };

        process_buffer(
            y,
            area,
            Offset::x(clamp_x),
            &mut ctx,
            &mut img_buffer_used.buffer,
            &mut decompressed_lines,
            16,
        );

        dma2d_wait_for_transfer();
        unsafe { dma2d_start(&img_buffer_used.buffer, clamped.width()) };
    }

    dma2d_wait_for_transfer();
    pixeldata_dirty();
}

#[cfg(not(feature = "dma2d"))]
pub fn image(image: &Image, center: Point) {
    let r = Rect::from_center_and_size(center, image.toif.size());
    let area = r.translate(get_offset());
    let clamped = area.clamp(constant::screen());

    set_window(clamped);

    let mut dest = [0_u8; 2];

    let mut window = [0; UZLIB_WINDOW_SIZE];
    let mut ctx = image.toif.decompression_context(Some(&mut window));

    for py in area.y0..area.y1 {
        for px in area.x0..area.x1 {
            let p = Point::new(px, py);

            if clamped.contains(p) {
                unwrap!(ctx.uncompress(&mut dest), "Decompression failed");
                let c = Color::from_u16(u16::from_le_bytes(dest));
                pixeldata(c);
            } else {
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
pub struct Toif<'i> {
    data: &'i [u8],
}

impl<'i> Toif<'i> {
    pub const fn new(data: &'i [u8]) -> Option<Self> {
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

    pub fn zdata(&self) -> &'i [u8] {
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
    pub toif: Toif<'static>,
}

impl Icon {
    pub const fn new(data: &'static [u8]) -> Self {
        let toif = match Toif::new(data) {
            Some(t) => t,
            None => panic!("Invalid image."),
        };
        assert!(matches!(toif.format(), ToifFormat::GrayScaleEH));
        Self { toif }
    }

    /// Display the icon with baseline Point, aligned according to the
    /// `alignment` argument.
    pub fn draw(&self, baseline: Point, alignment: Alignment2D, fg_color: Color, bg_color: Color) {
        let r = Rect::snap(baseline, self.toif.size(), alignment);
        icon(self, r.center(), fg_color, bg_color);
    }
}
