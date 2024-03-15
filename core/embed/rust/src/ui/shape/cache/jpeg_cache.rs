use crate::ui::{
    display::tjpgd,
    geometry::{Offset, Point, Rect},
    shape::{BasicCanvas, Bitmap, BitmapFormat, BitmapView, Canvas, Rgb565Canvas},
};

use core::cell::UnsafeCell;
use without_alloc::{alloc::LocalAllocLeakExt, FixedVec};

// JDEC work buffer size
//
// number of quantization tables (n_qtbl) = 2..4 (typical 2)
// number of huffman tables (n_htbl) = 2..4 (typical 2)
// mcu size = 1 * 1 .. 2 * 2 = 1..4 (typical 4)
//
// hufflut_ac & hufflut_dc are required only if JD_FASTDECODE == 2 (default)
//
// ---------------------------------------------------------------------
// table       | size calculation                   |  MIN..MAX   |  TYP
// ---------------------------------------------------------------------
// qttbl       | n_qtbl * size_of(i32) * 64         |  512..1024  |  512
// huffbits    | n_htbl * size_of(u8) * 16          |   32..64    |   32
// huffcode    | n_htbl * size_of(u16) * 256        | 1024..2048  | 1024
// huffdata    | n_htbl * size_of(u8) * 256         |  512..1024  |  512
// hufflut_ac  | n_htbl * size_of(u16) * 1024       | 4096..8192  | 4096
// hufflut_dc  | n_htbl * size_of(u8) * 1024        | 2048..4096  | 2048
// workbuf     | mcu_size * 192 + 64                |  256..832   |  832
// mcubuf      | (mcu_size + 2) * size_of(u16) * 64 |  384..768   |  768
// inbuff      | JD_SZBUF constant                  |  512..512   |  512
// ---------------------------------------------------------------|------
// SUM         |                                    | 9376..18560 | 10336
// ---------------------------------------------------------------|------

const JPEG_SCRATCHPAD_SIZE: usize = 10500; // the same const > 10336 as in original code

// Buffer for a cached row of JPEG MCUs (up to 240x16 RGB565 pixels)
const ALIGN_PAD: usize = 8;
const JPEG_BUFF_SIZE: usize = (240 * 2 * 16) + ALIGN_PAD;

pub struct JpegCacheSlot<'a> {
    // Reference to compressed data
    jpeg: &'a [u8],
    // value in range 0..3 leads into scale factor 1 << scale
    scale: u8,
    // Input buffer referencing compressed data
    input: Option<tjpgd::BufferInput<'a>>,
    // JPEG decoder instance
    decoder: Option<tjpgd::JDEC<'a>>,
    // Scratchpad memory used by the JPEG decoder
    // (it's used just by our decoder and nobody else)
    scratchpad: &'a UnsafeCell<[u8; JPEG_SCRATCHPAD_SIZE]>,
    // horizontal coordinate of cached row or None
    // (valid if row_canvas is Some)
    row_y: i16,
    // Canvas for recently decoded row of MCU's
    row_canvas: Option<Rgb565Canvas<'a>>,
    // Buffer for slice canvas
    row_buff: &'a UnsafeCell<[u8; JPEG_BUFF_SIZE]>,
}

impl<'a> JpegCacheSlot<'a> {
    fn new<'alloc: 'a, T>(bump: &'alloc T) -> Option<Self>
    where
        T: LocalAllocLeakExt<'alloc>,
    {
        let scratchpad = bump
            .alloc_t::<UnsafeCell<[u8; JPEG_SCRATCHPAD_SIZE]>>()?
            .uninit
            .init(UnsafeCell::new([0; JPEG_SCRATCHPAD_SIZE]));

        let canvas_buff = bump
            .alloc_t::<UnsafeCell<[u8; JPEG_BUFF_SIZE]>>()?
            .uninit
            .init(UnsafeCell::new([0; JPEG_BUFF_SIZE]));

        Some(Self {
            jpeg: &[],
            scale: 0,
            input: None,
            decoder: None,
            scratchpad,
            row_y: 0,
            row_canvas: None,
            row_buff: canvas_buff,
        })
    }

    fn reset<'i: 'a>(&mut self, jpeg: &'i [u8], scale: u8) -> Result<(), tjpgd::Error> {
        // Drop the existing decoder holding
        // a mutable reference to the scratchpad and canvas buffer & c
        self.decoder = None;
        self.row_canvas = None;

        if !jpeg.is_empty() {
            // Now there's nobody else holding any reference to our scratchpad buffer
            // so we can get a mutable reference and pass it to a new
            // instance of the JPEG decoder
            let scratchpad = unsafe { &mut *self.scratchpad.get() };
            // Prepare a input buffer
            let mut input = tjpgd::BufferInput(jpeg);
            // Initialize the decoder by reading headers from input
            let mut decoder = tjpgd::JDEC::new(&mut input, scratchpad)?;
            // Set decoder scale factor
            decoder.set_scale(scale)?;
            self.decoder = Some(decoder);
            // Save modified input buffer
            self.input = Some(input);
        } else {
            self.input = None;
        }

        self.jpeg = jpeg;
        self.scale = scale;
        Ok(())
    }

    fn is_for<'i: 'a>(&self, jpeg: &'i [u8], scale: u8) -> bool {
        jpeg == self.jpeg && scale == self.scale && self.decoder.is_some()
    }

    pub fn get_size<'i: 'a>(&mut self, jpeg: &'i [u8], scale: u8) -> Result<Offset, tjpgd::Error> {
        if !self.is_for(jpeg, scale) {
            self.reset(jpeg, scale)?;
        }
        let decoder = unwrap!(self.decoder.as_mut()); // should never fail
        let divisor = 1 << self.scale;
        Ok(Offset::new(
            decoder.width() / divisor,
            decoder.height() / divisor,
        ))
    }

    // left-top origin of output rectangle must be aligned to JPEG MCU size
    pub fn decompress_mcu<'i: 'a>(
        &mut self,
        jpeg: &'i [u8],
        scale: u8,
        offset: Point,
        output: &mut dyn FnMut(Rect, BitmapView) -> bool,
    ) -> Result<(), tjpgd::Error> {
        // Reset the slot if the JPEG image is different
        if !self.is_for(jpeg, scale) {
            self.reset(jpeg, scale)?;
        }

        // Get coordinates of the next coming MCU
        let decoder = unwrap!(self.decoder.as_ref()); // should never fail
        let divisor = 1 << self.scale;
        let next_mcu = Offset::new(
            decoder.next_mcu().0 as i16 / divisor,
            decoder.next_mcu().1 as i16 / divisor,
        );

        // Get height of the MCUs (8 or 16pixels)
        let mcu_height = decoder.mcu_height() / (1 << self.scale);

        // Reset the decoder if pixel at the offset was already decoded
        if offset.y < next_mcu.y || (offset.x < next_mcu.x && offset.y < next_mcu.y + mcu_height) {
            self.reset(self.jpeg, scale)?;
        }

        let decoder = unwrap!(self.decoder.as_mut()); // should never fail
        let input = unwrap!(self.input.as_mut()); // should never fail
        let mut output = JpegFnOutput::new(output);

        match decoder.decomp2(input, &mut output) {
            Ok(_) | Err(tjpgd::Error::Interrupted) => Ok(()),
            Err(e) => Err(e),
        }
    }

    pub fn decompress_row<'i: 'a>(
        &mut self,
        jpeg: &'i [u8],
        scale: u8,
        mut offset_y: i16,
        output: &mut dyn FnMut(Rect, BitmapView) -> bool,
    ) -> Result<(), tjpgd::Error> {
        // Reset the slot if the JPEG image is different
        if !self.is_for(jpeg, scale) {
            self.reset(jpeg, scale)?;
        }

        let mut row_canvas = self.row_canvas.take();
        let mut row_y = self.row_y;

        // Use cached data if possible
        if let Some(row_canvas) = row_canvas.as_mut() {
            if offset_y >= self.row_y && offset_y < self.row_y + row_canvas.height() {
                if !output(
                    Rect::from_size(row_canvas.size()).translate(Offset::new(0, row_y)),
                    row_canvas.view(),
                ) {
                    return Ok(());
                }
                // Align to the next MCU row
                offset_y += row_canvas.height() - offset_y % row_canvas.height();
            }
        } else {
            // Create a new row for cahing decoded JPEG data
            // Now there's nobody else holding any reference to canvas_buff so
            // we can get a mutable reference and pass it to a new instance
            // of Rgb565Canvas
            let canvas_buff = unsafe { &mut *self.row_buff.get() };
            // Prepare canvas as a cache for a row of decoded JPEG MCUs
            let decoder = unwrap!(self.decoder.as_ref()); // shoud never fail
            let divisor = 1 << self.scale;
            row_canvas = Some(unwrap!(
                Rgb565Canvas::new(
                    Offset::new(decoder.width() / divisor, decoder.mcu_height() / divisor),
                    None,
                    canvas_buff
                ),
                "Buffer too small"
            ));
        }

        self.decompress_mcu(
            jpeg,
            scale,
            Point::new(0, offset_y),
            &mut |mcu_r, mcu_bitmap| {
                // Get canvas for MCU caching
                let row_canvas = unwrap!(row_canvas.as_mut()); // should never fail

                // Calculate coordinates in the row canvas
                let dst_r = Rect {
                    y0: 0,
                    y1: mcu_r.height(),
                    ..mcu_r
                };
                // Draw a MCU
                row_canvas.draw_bitmap(dst_r, mcu_bitmap);

                if mcu_r.x1 < row_canvas.size().x {
                    // We are not done with the row yet
                    true
                } else {
                    // We have a complete row, let's pass it to the callee
                    row_y = mcu_r.y0;
                    output(
                        Rect::from_size(row_canvas.size()).translate(Offset::new(0, row_y)),
                        row_canvas.view(),
                    )
                }
            },
        )?;

        // Store the recently decoded row for future use
        self.row_y = row_y;
        self.row_canvas = row_canvas;

        Ok(())
    }
}

struct JpegFnOutput<F>
where
    F: FnMut(Rect, BitmapView) -> bool,
{
    output: F,
}

impl<F> JpegFnOutput<F>
where
    F: FnMut(Rect, BitmapView) -> bool,
{
    pub fn new(output: F) -> Self {
        Self { output }
    }
}

impl<F> trezor_tjpgdec::JpegOutput for JpegFnOutput<F>
where
    F: FnMut(Rect, BitmapView) -> bool,
{
    fn write(
        &mut self,
        _jd: &tjpgd::JDEC,
        rect_origin: (u32, u32),
        rect_size: (u32, u32),
        pixels: &[u16],
    ) -> bool {
        // MCU coordinates in source image
        let mcu_r = Rect::from_top_left_and_size(
            Point::new(rect_origin.0 as i16, rect_origin.1 as i16),
            Offset::new(rect_size.0 as i16, rect_size.1 as i16),
        );

        // SAFETY: aligning from [u16] -> [u8]
        let (_, pixels, _) = unsafe { pixels.align_to() };

        // Create readonly bitmap
        let mcu_bitmap = unwrap!(Bitmap::new(
            BitmapFormat::RGB565,
            None,
            mcu_r.size(),
            None,
            pixels,
        ));

        // Return true to continue decompression
        (self.output)(mcu_r, BitmapView::new(&mcu_bitmap))
    }
}

pub struct JpegCache<'a> {
    slots: FixedVec<'a, JpegCacheSlot<'a>>,
}

impl<'a> JpegCache<'a> {
    pub fn new<'alloc: 'a, T>(bump: &'alloc T, slot_count: usize) -> Option<Self>
    where
        T: LocalAllocLeakExt<'alloc>,
    {
        assert!(slot_count <= 1); // we support just 1 decoder

        let mut cache = Self {
            slots: bump.fixed_vec(slot_count)?,
        };

        for _ in 0..cache.slots.capacity() {
            unwrap!(cache.slots.push(JpegCacheSlot::new(bump)?)); // should never fail
        }

        Some(cache)
    }

    pub fn get_size<'i: 'a>(&mut self, jpeg: &'i [u8], scale: u8) -> Result<Offset, tjpgd::Error> {
        if self.slots.capacity() > 0 {
            self.slots[0].get_size(jpeg, scale)
        } else {
            Err(tjpgd::Error::MemoryPool)
        }
    }

    pub fn decompress_mcu<'i: 'a>(
        &mut self,
        jpeg: &'i [u8],
        scale: u8,
        offset: Point,
        output: &mut dyn FnMut(Rect, BitmapView) -> bool,
    ) -> Result<(), tjpgd::Error> {
        if self.slots.capacity() > 0 {
            self.slots[0].decompress_mcu(jpeg, scale, offset, output)
        } else {
            Err(tjpgd::Error::MemoryPool)
        }
    }

    pub fn decompress_row<'i: 'a>(
        &mut self,
        jpeg: &'i [u8],
        scale: u8,
        offset_y: i16,
        output: &mut dyn FnMut(Rect, BitmapView) -> bool,
    ) -> Result<(), tjpgd::Error> {
        if self.slots.capacity() > 0 {
            self.slots[0].decompress_row(jpeg, scale, offset_y, output)
        } else {
            Err(tjpgd::Error::MemoryPool)
        }
    }
}
