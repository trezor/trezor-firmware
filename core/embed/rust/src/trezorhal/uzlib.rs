use super::ffi;
use crate::io::BinaryData;
use core::{cell::RefCell, marker::PhantomData, mem::MaybeUninit, ptr};

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

struct SourceReadContext<'a> {
    /// Compressed data
    data: BinaryData<'a>,
    /// Ofsset in the compressed data
    // (points to the next byte to read)
    offset: usize,
    /// Internal buffer for reading compressed data
    buf: [u8; 128],
    buf_head: usize,
    buf_tail: usize,
}

impl<'a> SourceReadContext<'a> {
    pub fn new(data: BinaryData<'a>, offset: usize) -> Self {
        Self {
            data,
            offset,
            buf: [0; 128],
            buf_head: 0,
            buf_tail: 0,
        }
    }

    /// Fill the uncomp struct with the appropriate pointers to the source data
    pub fn prepare_uncomp(&self, uncomp: &mut ffi::uzlib_uncomp) {
        // SAFETY: the offsets are within the buffer bounds.
        // - buf_head is either 0 or advanced by uzlib to at most buf_tail (via
        //   advance())
        // - buf_tail is at most the buffer size (via reader_callback())
        unsafe {
            uncomp.source = self.buf.as_ptr().add(self.buf_head);
            uncomp.source_limit = self.buf.as_ptr().add(self.buf_tail);
        }
    }

    /// Advance the internal buffer after a read operation
    ///
    /// # Safety
    ///
    /// The operation is only valid on an uncomp struct that has been filled via
    /// `prepare_uncomp` and the source pointer has been updated by the uzlib
    /// library after a single uncompress operation.
    pub unsafe fn advance(&mut self, uncomp: &ffi::uzlib_uncomp) {
        unsafe {
            // SAFETY: we trust uzlib to move the `source` pointer only up to `source_limit`
            self.buf_head = uncomp.source.offset_from(self.buf.as_ptr()) as usize;
        }
    }

    /// Implement uzlib reader callback.
    ///
    /// If the uncomp buffer is exhausted, a callback is invoked that should (a)
    /// read one byte of data, and optionally (b) update the uncomp buffer
    /// with more data.
    pub fn reader_callback(&mut self, uncomp: &mut ffi::uzlib_uncomp) -> Option<u8> {
        // fill the internal buffer first
        let bytes_read = self.data.read(self.offset, self.buf.as_mut());
        self.buf_head = 0;
        self.buf_tail = bytes_read;
        // advance total offset
        self.offset += bytes_read;

        if bytes_read > 0 {
            // "read" one byte
            self.buf_head += 1;
            // update the uncomp struct
            self.prepare_uncomp(uncomp);
            // return the first byte read
            Some(self.buf[0])
        } else {
            // EOF
            None
        }
    }
}

pub struct ZlibInflate<'a> {
    /// Compressed data reader
    data: RefCell<SourceReadContext<'a>>,
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
            data: RefCell::new(SourceReadContext::new(data, offset)),
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
        // Fill out source data pointers
        self.data.borrow().prepare_uncomp(&mut self.uncomp);

        let res = unsafe {
            // Source data callback (used to read more data when source is exhausted)
            self.uncomp.source_read_cb = Some(zlib_reader_callback);
            // Context for the source data callback
            self.uncomp.source_read_cb_context = &self.data as *const _ as *mut cty::c_void;

            // Destination buffer
            self.uncomp.dest = dest.as_mut_ptr();
            self.uncomp.dest_limit = self.uncomp.dest.add(dest.len());

            // SAFETY:
            // Even if the `ZlibInflate` instance is moved, the source and context
            // pointers are still valid as we set them before calling `uzlib_uncompress`
            let res = ffi::uzlib_uncompress(&mut self.uncomp);

            // `uzlib_uncompress` moved self.uncomp.source to the next byte to read
            // so we can now update `buf_head` to reflect the new position
            // SAFETY: we have just called `uzlib_uncompress`
            self.data.borrow_mut().advance(&self.uncomp);

            res
        };

        // Clear the source read callback (just for safety)
        self.uncomp.source_read_cb_context = core::ptr::null_mut();

        match res {
            0 => Ok(false),
            1 => Ok(true),
            _ => Err(()),
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
    // SAFETY: we assume that passed-in uncomp is not null and that we own it
    // exclusively (ensured by passing it as &mut into uzlib_uncompress())
    let uncomp = unwrap!(unsafe { uncomp.as_mut() });
    let ctx = uncomp.source_read_cb_context as *const RefCell<SourceReadContext>;
    // SAFETY: we assume that ctx is a valid pointer to the refcell holding the
    // source data
    let mut ctx = unwrap!(unsafe { ctx.as_ref() }).borrow_mut();

    match ctx.reader_callback(uncomp) {
        Some(byte) => byte as i32,
        None => -1, // EOF
    }
}
