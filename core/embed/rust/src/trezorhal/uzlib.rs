use super::ffi;
use crate::io::BinaryData;
use core::{marker::PhantomData, mem::MaybeUninit, ptr};

pub const UZLIB_WINDOW_SIZE: usize = 1 << 10;
pub use ffi::uzlib_uncomp;

impl Default for ffi::uzlib_uncomp {
    fn default() -> Self {
        unsafe { MaybeUninit::<Self>::zeroed().assume_init() }
    }
}

pub struct UzlibContext<'a> {
    uncomp: ffi::uzlib_uncomp,
    src_data: PhantomData<&'a [u8]>,
}

impl<'a> UzlibContext<'a> {
    pub fn new(src: &'a [u8], window: Option<&'a mut [u8; UZLIB_WINDOW_SIZE]>) -> Self {
        let mut ctx = Self {
            uncomp: uzlib_uncomp::default(),
            src_data: PhantomData,
        };

        unsafe {
            ctx.uncomp.source = src.as_ptr();
            ctx.uncomp.source_limit = src.as_ptr().add(src.len());

            if let Some(w) = window {
                ffi::uzlib_uncompress_init(
                    &mut ctx.uncomp,
                    w.as_mut_ptr() as _,
                    UZLIB_WINDOW_SIZE as u32,
                );
            } else {
                ffi::uzlib_uncompress_init(&mut ctx.uncomp, ptr::null_mut(), 0);
            }
        }

        ctx
    }

    /// Returns `Ok(true)` if all data was read.
    pub fn uncompress(&mut self, dest_buf: &mut [u8]) -> Result<bool, ()> {
        unsafe {
            self.uncomp.dest = dest_buf.as_mut_ptr();
            self.uncomp.dest_limit = self.uncomp.dest.add(dest_buf.len());

            let res = ffi::uzlib_uncompress(&mut self.uncomp);

            match res {
                0 => Ok(false),
                1 => Ok(true),
                _ => Err(()),
            }
        }
    }
}

pub struct ZlibInflate<'a> {
    /// Compressed data
    data: BinaryData<'a>,
    /// Ofsset in the compressed data
    // (points to the next byte to read)
    offset: usize,
    /// Internal buffer for reading compressed data
    buf: [u8; 128],
    buf_head: usize,
    buf_tail: usize,

    /// Uzlib context
    uncomp: ffi::uzlib_uncomp,
    window: PhantomData<&'a [u8]>,
}

impl<'a> ZlibInflate<'a> {
    /// Creates a new `ZlibInflate` instance.
    /// - `data` - compressed data
    /// - `offset` - initial offset in the compressed data
    /// - `window` - window buffer for decompression
    pub fn new(
        data: BinaryData<'a>,
        offset: usize,
        window: &'a mut [u8; UZLIB_WINDOW_SIZE],
    ) -> Self {
        let mut inflate = Self {
            data,
            offset,
            buf: [0; 128],
            buf_head: 0,
            buf_tail: 0,
            uncomp: uzlib_uncomp::default(),
            window: PhantomData,
        };

        // SAFETY:
        // `window` is a valid mutable slice with the size of UZLIB_WINDOW_SIZE
        // it remains valid until the `ZlibInflate` instance is dropped
        unsafe {
            let window_ptr = window.as_mut_ptr() as _;
            let window_size = UZLIB_WINDOW_SIZE as u32;
            ffi::uzlib_uncompress_init(&mut inflate.uncomp, window_ptr, window_size);
        }

        inflate
    }

    /// Reads uncompressed data into the destination buffer.
    /// Returns `Ok(true)` if all data was read
    pub fn read(&mut self, dest: &mut [u8]) -> Result<bool, ()> {
        // SAFETY:
        // Even if the `ZlibInflate` instance is moved, the source and context
        // pointers are still valid as we set them before calling `uzlib_uncompress`
        unsafe {
            // Source data
            self.uncomp.source = self.buf.as_ptr().add(self.buf_head);
            self.uncomp.source_limit = self.buf.as_ptr().add(self.buf_tail);

            // Source data callback (used to read more data when source is exhausted)
            self.uncomp.source_read_cb = Some(zlib_reader_callback);
            self.uncomp.source_read_cb_context = self as *mut _ as *mut cty::c_void;

            // Destination buffer
            self.uncomp.dest = dest.as_mut_ptr();
            self.uncomp.dest_limit = self.uncomp.dest.add(dest.len());

            let res = ffi::uzlib_uncompress(&mut self.uncomp);

            // `uzlib_uncompress` moved self.uncomp.source to the next byte to read
            // so we can now update `buf_head` to reflect the new position
            self.buf_head = self.uncomp.source.offset_from(self.buf.as_ptr()) as usize;

            // Clear the source read callback (just for safety)
            self.uncomp.source_read_cb_context = core::ptr::null_mut();

            match res {
                0 => Ok(false),
                1 => Ok(true),
                _ => Err(()),
            }
        }
    }

    /// Skips a specified number of bytes (`nbytes`) in the uncompressed stream.
    ///
    /// Returns `Ok(true)` if all data was read.
    pub fn skip(&mut self, nbytes: usize) -> Result<bool, ()> {
        let mut result = false; // false => OK, true => DONE
        let mut sink = [0u8; 256];
        for i in (0..nbytes).step_by(sink.len()) {
            let chunk_len = core::cmp::min(sink.len(), nbytes - i);
            let chunk = &mut sink[0..chunk_len];
            result = self.read(chunk)?;
        }
        Ok(result)
    }
}

/// This function is called by the uzlib library to read more data from the
/// input stream.
unsafe extern "C" fn zlib_reader_callback(uncomp: *mut ffi::uzlib_uncomp) -> i32 {
    // Get mutable reference to the ZlibInflate instance
    // SAFETY:
    // This routine is indirectly called from `Self::read()` where
    // self is a mutable reference. Nobody else holds this reference.
    // We are dereferencing here twice and in both cases, we are checking
    // that the pointers are not null.
    let ctx = unsafe {
        assert!(!uncomp.is_null());
        let ctx = (*uncomp).source_read_cb_context as *mut ZlibInflate;
        assert!(!ctx.is_null());
        &mut *ctx
    };

    // let the reader fill our internal buffer with new data
    let bytes_read = ctx.data.read(ctx.offset, ctx.buf.as_mut());
    ctx.buf_head = 0;
    ctx.buf_tail = bytes_read;
    ctx.offset += bytes_read;

    if ctx.buf_tail > 0 {
        ctx.buf_head += 1;
        // SAFETY:
        // We set uncomp source pointers to our cache buffer except
        // the first byte which is passed to the uzlib library directly
        // The data in cache is valid and unchanged until the next call
        // to this function
        unsafe {
            ctx.uncomp.source = ctx.buf.as_ptr().add(ctx.buf_head);
            ctx.uncomp.source_limit = ctx.buf.as_ptr().add(ctx.buf_tail);
        }
        // Pass the first byte to the uzlib library
        return ctx.buf[0] as i32;
    }

    -1 // EOF
}
