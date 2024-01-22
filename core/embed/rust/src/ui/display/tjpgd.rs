use trezor_tjpgdec::{BlackHoleOutput, JpegOutput};
pub use trezor_tjpgdec::{BufferInput, Error, JDEC};

use crate::{
    trezorhal::{
        buffers::{BufferJpeg, BufferJpegWork},
        display::pixeldata,
    },
    ui::{
        constant,
        display::set_window,
        geometry::{Offset, Point, Rect},
    },
};

pub fn jpeg(data: &[u8], pos: Point, scale: u8) {
    let mut buffer = BufferJpegWork::get_cleared();
    let pool = buffer.buffer.as_mut_slice();
    let mut out = PixelDataOutput(pos);
    let mut inp = BufferInput(data);
    if let Ok(mut jd) = JDEC::new(&mut inp, pool) {
        let _ = jd.set_scale(scale);
        let _ = jd.decomp(&mut inp, &mut out);
    }
}

pub fn jpeg_info(data: &[u8]) -> Option<(Offset, i16)> {
    let mut buffer = BufferJpegWork::get_cleared();
    let pool = buffer.buffer.as_mut_slice();
    let mut inp = BufferInput(data);
    let result = if let Ok(jd) = JDEC::new(&mut inp, pool) {
        let mcu_height = jd.mcu_height();
        if mcu_height > 16 {
            return None;
        }
        Some((Offset::new(jd.width(), jd.height()), mcu_height))
    } else {
        None
    };
    result
}

pub fn jpeg_test(data: &[u8]) -> bool {
    let mut buffer = BufferJpegWork::get_cleared();
    let pool = buffer.buffer.as_mut_slice();
    let mut inp = BufferInput(data);
    let result = if let Ok(mut jd) = JDEC::new(&mut inp, pool) {
        if jd.mcu_height() > 16 {
            return false;
        }

        let mut out = BlackHoleOutput;
        let mut res = jd.decomp(&mut inp, &mut out);
        while res == Err(Error::Interrupted) {
            res = jd.decomp(&mut inp, &mut out);
        }
        res.is_ok()
    } else {
        false
    };
    result
}

pub struct BufferOutput {
    buffer: BufferJpeg,
    buffer_width: i16,
    buffer_height: i16,
    current_line: i16,
    current_line_pix: i16,
}

impl BufferOutput {
    pub fn new(buffer_width: i16, buffer_height: i16) -> Self {
        Self {
            buffer: BufferJpeg::get_cleared(),
            buffer_width,
            buffer_height,
            current_line: 0,
            current_line_pix: 0,
        }
    }

    pub fn buffer(&mut self) -> &mut BufferJpeg {
        &mut self.buffer
    }
}

impl JpegOutput for BufferOutput {
    fn write(
        &mut self,
        jd: &JDEC,
        rect_origin: (u32, u32),
        rect_size: (u32, u32),
        bitmap: &[u16],
    ) -> bool {
        let w = rect_size.0 as i16;
        let h = rect_size.1 as i16;
        let x = rect_origin.0 as i16;

        if h > self.buffer_height {
            // unsupported height, call and let know
            return true;
        }

        let buffer_len = (self.buffer_width * self.buffer_height) as usize;

        for i in 0..h {
            for j in 0..w {
                let buffer_pos = ((x + j) + (i * self.buffer_width)) as usize;
                if buffer_pos < buffer_len {
                    self.buffer.buffer[buffer_pos] = bitmap[(i * w + j) as usize];
                }
            }
        }

        self.current_line_pix += w;

        if self.current_line_pix >= jd.width() {
            self.current_line_pix = 0;
            self.current_line += jd.mcu_height();
            // finished line, abort and continue later
            return false;
        }

        true
    }
}

pub struct PixelDataOutput(Point);

impl JpegOutput for PixelDataOutput {
    fn write(
        &mut self,
        _jd: &JDEC,
        rect_origin: (u32, u32),
        rect_size: (u32, u32),
        bitmap: &[u16],
    ) -> bool {
        let pos = self.0;
        let rect = Rect::from_top_left_and_size(
            Point::new(rect_origin.0 as i16, rect_origin.1 as i16),
            Offset::new(rect_size.0 as i16, rect_size.1 as i16),
        );
        let r = rect.translate(pos.into());
        let clamped = r.clamp(constant::screen());
        set_window(clamped);
        for py in r.y0..r.y1 {
            for px in r.x0..r.x1 {
                let p = Point::new(px, py);
                if clamped.contains(p) {
                    let off = p - r.top_left();
                    let c = bitmap[(off.y * rect.width() + off.x) as usize];
                    pixeldata(c);
                }
            }
        }
        true
    }
}
