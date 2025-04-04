use super::ffi;

use crate::ui::{
    geometry::{Offset, Point, Rect},
    shape::{Bitmap, BitmapFormat, BitmapView},
};

use crate::io::BinaryData;
use num_traits::FromPrimitive;

pub const RGBA8888_BUFFER_SIZE: usize = ffi::JPEGDEC_RGBA8888_BUFFER_SIZE as _;
pub const MONO8_BUFFER_SIZE: usize = ffi::JPEGDEC_MONO8_BUFFER_SIZE as _;

#[derive(PartialEq, Debug, Eq, FromPrimitive, Clone, Copy)]
enum JpegDecState {
    NeedData = ffi::jpegdec_state_t_JPEGDEC_STATE_NEED_DATA as _,
    InfoReady = ffi::jpegdec_state_t_JPEGDEC_STATE_INFO_READY as _,
    SliceReady = ffi::jpegdec_state_t_JPEGDEC_STATE_SLICE_READY as _,
    Finished = ffi::jpegdec_state_t_JPEGDEC_STATE_FINISHED as _,
    Error = ffi::jpegdec_state_t_JPEGDEC_STATE_ERROR as _,
}

#[derive(PartialEq, Debug, Eq, FromPrimitive, Clone, Copy)]
pub enum JpegDecImageFormat {
    GrayScale = ffi::jpegdec_image_format_t_JPEGDEC_IMAGE_GRAYSCALE as _,
    YCBCR420 = ffi::jpegdec_image_format_t_JPEGDEC_IMAGE_YCBCR420 as _,
    YCBCR422 = ffi::jpegdec_image_format_t_JPEGDEC_IMAGE_YCBCR422 as _,
    YCBCR444 = ffi::jpegdec_image_format_t_JPEGDEC_IMAGE_YCBCR444 as _,
}

pub struct JpegDecImage {
    pub width: i16,
    pub height: i16,
    pub format: JpegDecImageFormat,
}

pub struct JpegDecoder<'a> {
    jpeg: BinaryData<'a>,
    jpeg_pos: usize,
    buff: [u8; 1024],
    buff_pos: usize,
    buff_len: usize,
}

impl Drop for JpegDecoder<'_> {
    fn drop(&mut self) {
        // SAFETY:
        // We cannot have more than one instance of JpegDecoder at a time.
        // The `jpegdec_close` is called in pair with `jpegdec_open`.
        unsafe {
            ffi::jpegdec_close();
        }
    }
}

impl<'a> JpegDecoder<'a> {
    /// Creates a new JPEG decoder instance from the given JPEG data.
    ///
    /// The function reads the JPEG header and returns.
    pub fn new(jpeg: BinaryData<'a>) -> Result<Self, ()> {
        // SAFETY:
        // `jpegdec_open()` is always called in pair with `jpegdec_close()`.
        if !unsafe { ffi::jpegdec_open() } {
            // Already open
            return Err(());
        }

        let mut dec = Self {
            jpeg,
            jpeg_pos: 0,
            buff: [0; 1024],
            buff_pos: 0,
            buff_len: 0,
        };

        loop {
            match dec.read_input() {
                JpegDecState::InfoReady => break,
                JpegDecState::NeedData => {}
                _ => return Err(()),
            };
        }

        Ok(dec)
    }

    // Returns the image format and dimensions.
    pub fn image(&self) -> Result<JpegDecImage, ()> {
        let mut info = ffi::jpegdec_image_t {
            width: 0,
            height: 0,
            format: 0,
        };

        // SAFETY:
        // - `info` is a valid pointer to a mutable `jpegdec_image_t` struct.
        if unsafe { ffi::jpegdec_get_info(&mut info) } {
            Ok(JpegDecImage {
                width: info.width,
                height: info.height,
                format: unwrap!(JpegDecImageFormat::from_u8(info.format as _)),
            })
        } else {
            Err(())
        }
    }

    /// Decodes the JPEG image and calls the output function for each slice.
    /// Requires a temporary buffer of size `RGBA8888_BUFFER_SIZE`.
    /// The output function should return `true` to continue decoding or `false`
    /// to stop. Returns `Ok(())` if the decoding was successful or
    /// `Err(())` if an error occurred.
    pub fn decode(
        &mut self,
        buff: &mut [u8],
        output: &mut dyn FnMut(Rect, BitmapView) -> bool,
    ) -> Result<(), ()> {
        loop {
            match self.read_input() {
                JpegDecState::SliceReady => {
                    if !self.write_output(buff, output) {
                        break;
                    };
                }
                JpegDecState::Finished => break,
                JpegDecState::NeedData => {}
                _ => return Err(()),
            };
        }
        Ok(())
    }

    /// Decodes the JPEG image and calls the output function for each slice.
    /// The function decodes only the Y component of the image, so
    /// the output is always grayscale (BitmapFormat::MONO8).
    /// Requires a temporary buffer of size `RGBA8888_BUFFER_SIZE`.
    /// The output function should return `true` to continue decoding or `false`
    /// to stop. Returns `Ok(())` if the decoding was successful or
    /// `Err(())` if an error occurred.
    pub fn decode_mono8(
        &mut self,
        buff: &mut [u8],
        output: &mut dyn FnMut(Rect, BitmapView) -> bool,
    ) -> Result<(), ()> {
        loop {
            match self.read_input() {
                JpegDecState::SliceReady => {
                    if !self.write_output_mono8(buff, output) {
                        break;
                    };
                }
                JpegDecState::Finished => break,
                JpegDecState::NeedData => {}
                _ => return Err(()),
            };
        }
        Ok(())
    }

    fn read_input(&mut self) -> JpegDecState {
        if self.buff_pos == self.buff_len {
            self.buff_len = self.jpeg.read(self.jpeg_pos, &mut self.buff);
            self.buff_pos = 0;
            self.jpeg_pos += self.buff_len;
        }

        let mut inp = ffi::jpegdec_input_t {
            data: self.buff.as_ptr(),
            size: self.buff_len,
            offset: self.buff_pos,
            last_chunk: self.buff_len < self.buff.len(),
        };

        // SAFETY:
        // - `inp.data` points to the mutable buffer we own
        // - `inp.size` is valid buffer size
        // - `inp.offset` is a valid offset in the buffer
        // - jpegdec_process() doesn't retain the pointers to the data for later use
        let state_u8 = unsafe { ffi::jpegdec_process(&mut inp) };
        self.buff_pos = inp.offset;

        unwrap!(JpegDecState::from_u8(state_u8 as _))
    }

    fn write_output(
        &self,
        buff: &mut [u8],
        output: &mut dyn FnMut(Rect, BitmapView) -> bool,
    ) -> bool {
        // SAFETY:
        // - after aligning the buffer to u32, the we check the
        //  length of the buffer to be at least `RGBA8888_BUFFER_SIZE`
        let rgba_u32 = unsafe { buff.align_to_mut::<u32>().1 };
        assert!(rgba_u32.len() * 4 >= RGBA8888_BUFFER_SIZE);

        let mut slice = ffi::jpegdec_slice_t {
            x: 0,
            y: 0,
            width: 0,
            height: 0,
        };

        // SAFETY:
        //  - `rgba_u32` is a valid pointer to a mutable buffer of length at least
        //    `RGBA8888_BUFFER_SIZE` aligned to u32
        //  - `slice` is a valid pointer to a mutable `jpegdec_slice_t`
        //  - `jpegdec_get_slice_rgba8888` doesn't retain the pointers to the data for
        //    later use
        unsafe { ffi::jpegdec_get_slice_rgba8888(rgba_u32.as_mut_ptr(), &mut slice) };

        let r = Rect::from_top_left_and_size(
            Point::new(slice.x, slice.y),
            Offset::new(slice.width, slice.height),
        );

        // SAFETY:
        // - reinterpreting &[u32] to &[u8] is safe
        let rgba_u8 = unsafe { buff.align_to::<u8>().1 };

        let bitmap = unwrap!(Bitmap::new(
            BitmapFormat::RGBA8888,
            None,
            r.size(),
            None,
            rgba_u8
        ));

        let view = BitmapView::new(&bitmap);

        output(r, view)
    }

    fn write_output_mono8(
        &self,
        buff: &mut [u8],
        output: &mut dyn FnMut(Rect, BitmapView) -> bool,
    ) -> bool {
        // SAFETY:
        // - after aligning the buffer to u32, the we check the
        //  length of the buffer to be at least `MONO8_BUFFER_SIZE`
        let buff_u32 = unsafe { buff.align_to_mut::<u32>().1 };
        assert!(buff_u32.len() * 4 >= MONO8_BUFFER_SIZE);

        let mut slice = ffi::jpegdec_slice_t {
            x: 0,
            y: 0,
            width: 0,
            height: 0,
        };

        // SAFETY:
        //  - `buff` is a valid pointer to a mutable buffer of length at least
        //    `MONO8_BUFFER_SIZE` bytes aligned to u32
        //  - `slice` is a valid pointer to a mutable `jpegdec_slice_t`
        //  - `jpegdec_get_slice_yonly` doesn't retain the pointers to the data for
        //    later use
        unsafe { ffi::jpegdec_get_slice_mono8(buff_u32.as_mut_ptr(), &mut slice) };

        let r = Rect::from_top_left_and_size(
            Point::new(slice.x, slice.y),
            Offset::new(slice.width, slice.height),
        );

        // SAFETY:
        // - reinterpreting &[u32] to &[u8] is safe
        let buff_u8 = unsafe { buff.align_to::<u8>().1 };

        let bitmap = unwrap!(Bitmap::new(
            BitmapFormat::MONO8,
            None,
            r.size(),
            None,
            buff_u8
        ));

        let view = BitmapView::new(&bitmap);

        output(r, view)
    }
}
