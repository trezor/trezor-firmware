use crate::{
    error::Error,
    trezorhal::uzlib::{UzlibContext, UZLIB_WINDOW_SIZE},
    ui::{
        component::image::Image,
        constant,
        display::{get_offset, pixeldata_dirty, set_window},
        geometry::{Alignment2D, Offset, Point, Rect},
    },
};

#[cfg(feature = "dma2d")]
use crate::{
    trezorhal::{
        buffers::BufferLine16bpp,
        dma2d::{dma2d_setup_16bpp, dma2d_start, dma2d_wait_for_transfer},
    },
    ui::display::process_buffer,
};

#[cfg(not(feature = "framebuffer"))]
use crate::ui::display::{get_color_table, pixeldata};

#[cfg(feature = "framebuffer")]
use crate::trezorhal::{buffers::BufferLine4bpp, dma2d::dma2d_setup_4bpp};
#[cfg(feature = "framebuffer")]
use core::cmp::max;

use super::Color;

const TOIF_HEADER_LENGTH: usize = 12;

#[derive(PartialEq, Debug, Eq, FromPrimitive, Clone, Copy)]
pub enum ToifFormat {
    FullColorBE = 0, // big endian
    GrayScaleOH = 1, // odd hi
    FullColorLE = 2, // little endian
    GrayScaleEH = 3, // even hi
}

pub fn render_icon(icon: &Icon, center: Point, fg_color: Color, bg_color: Color) {
    render_toif(&icon.toif, center, fg_color, bg_color);
}

#[cfg(not(feature = "framebuffer"))]
pub fn render_toif(toif: &Toif, center: Point, fg_color: Color, bg_color: Color) {
    let r = Rect::from_center_and_size(center, toif.size());
    let area = r.translate(get_offset());
    let clamped = area.clamp(constant::screen());
    let colortable = get_color_table(fg_color, bg_color);

    set_window(clamped);

    let mut dest = [0_u8; 1];

    let mut window = [0; UZLIB_WINDOW_SIZE];
    let mut ctx = toif.decompression_context(Some(&mut window));

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

#[cfg(feature = "framebuffer")]
pub fn render_toif(toif: &Toif, center: Point, fg_color: Color, bg_color: Color) {
    let r = Rect::from_center_and_size(center, toif.size());
    let area = r.translate(get_offset());
    let clamped = area.clamp(constant::screen()).ensure_even_width();

    set_window(clamped);

    let mut b1 = BufferLine4bpp::get_cleared();
    let mut b2 = BufferLine4bpp::get_cleared();

    let mut window = [0; UZLIB_WINDOW_SIZE];
    let mut ctx = toif.decompression_context(Some(&mut window));

    dma2d_setup_4bpp(fg_color.into(), bg_color.into());

    let x_shift = max(0, clamped.x0 - area.x0);

    for y in area.y0..clamped.y1 {
        let img_buffer_used = if y % 2 == 0 { &mut b1 } else { &mut b2 };

        unwrap!(ctx.uncompress(&mut (&mut img_buffer_used.buffer)[..(area.width() / 2) as usize]));

        if y >= clamped.y0 {
            dma2d_wait_for_transfer();
            unsafe {
                dma2d_start(
                    &img_buffer_used.buffer
                        [(x_shift / 2) as usize..((clamped.width() + x_shift) / 2) as usize],
                    clamped.width(),
                )
            };
        }
    }

    dma2d_wait_for_transfer();
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
    image.draw(Point::new(x, y), Alignment2D::TOP_LEFT);
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
    /// Due to toif limitations, image width must be divisible by 2.
    /// In cases the actual image is odd-width, it will have empty
    /// rightmost column and this flag will make account for it
    /// when determining the width and when drawing it.
    pub empty_right_column: bool,
}

impl<'i> Toif<'i> {
    pub const fn new(data: &'i [u8]) -> Result<Self, Error> {
        if data.len() < TOIF_HEADER_LENGTH || data[0] != b'T' || data[1] != b'O' || data[2] != b'I'
        {
            return Err(value_error!("Invalid TOIF header."));
        }
        let zdatalen = u32::from_le_bytes([data[8], data[9], data[10], data[11]]) as usize;
        if zdatalen + TOIF_HEADER_LENGTH != data.len() {
            return Err(value_error!("Invalid TOIF length."));
        }
        Ok(Self {
            data,
            empty_right_column: false,
        })
    }

    pub const fn with_empty_right_column(mut self) -> Self {
        self.empty_right_column = true;
        self
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

    pub const fn is_grayscale(&self) -> bool {
        matches!(
            self.format(),
            ToifFormat::GrayScaleOH | ToifFormat::GrayScaleEH
        )
    }

    pub const fn width(&self) -> i16 {
        let data_width = u16::from_le_bytes([self.data[4], self.data[5]]) as i16;
        if self.empty_right_column {
            data_width - 1
        } else {
            data_width
        }
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

    /// Display the data with baseline Point, aligned according to the
    /// `alignment` argument.
    pub fn draw(&self, baseline: Point, alignment: Alignment2D, fg_color: Color, bg_color: Color) {
        let r = Rect::snap(baseline, self.size(), alignment);
        render_toif(self, r.center(), fg_color, bg_color);
    }
}

#[no_mangle]
extern "C" fn display_icon(
    x: cty::int16_t,
    y: cty::int16_t,
    data: *const cty::uint8_t,
    data_len: cty::uint32_t,
    fg_color: cty::uint16_t,
    bg_color: cty::uint16_t,
) {
    let data_slice = unsafe { core::slice::from_raw_parts(data, data_len as usize) };
    let icon = Icon::new(data_slice);
    icon.draw(
        Point::new(x, y),
        Alignment2D::TOP_LEFT,
        Color::from_u16(fg_color),
        Color::from_u16(bg_color),
    );
}

#[derive(PartialEq, Eq, Clone, Copy)]
pub struct Icon {
    pub toif: Toif<'static>,
    #[cfg(feature = "ui_debug")]
    pub name: &'static str,
}

impl Icon {
    pub const fn new(data: &'static [u8]) -> Self {
        let toif = match Toif::new(data) {
            Ok(t) => t,
            _ => panic!("Invalid image."),
        };
        assert!(matches!(toif.format(), ToifFormat::GrayScaleEH));
        Self {
            toif,
            #[cfg(feature = "ui_debug")]
            name: "<unnamed>",
        }
    }

    pub const fn with_empty_right_column(mut self) -> Self {
        self.toif.empty_right_column = true;
        self
    }

    /// Create a named icon.
    /// The name is only stored in debug builds.
    pub const fn debug_named(data: &'static [u8], _name: &'static str) -> Self {
        Self {
            #[cfg(feature = "ui_debug")]
            name: _name,
            ..Self::new(data)
        }
    }

    /// Display the icon with baseline Point, aligned according to the
    /// `alignment` argument.
    pub fn draw(&self, baseline: Point, alignment: Alignment2D, fg_color: Color, bg_color: Color) {
        let r = Rect::snap(baseline, self.toif.size(), alignment);
        render_icon(self, r.center(), fg_color, bg_color);
    }
}
