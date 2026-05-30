use super::ffi;
use crate::io::BinaryData;
use core::{cell::RefCell, marker::PhantomData, mem::MaybeUninit, ptr};

pub const UZLIB_WINDOW_SIZE: usize = 1 << 10;
// Upstream renamed `struct uzlib_uncomp` to the typedef `uzlib_uncomp_t`
// (struct `_uzlib_uncomp_t`) after v1.19.1; keep the old short name as an alias.
pub use ffi::uzlib_uncomp_t as uzlib_uncomp;

impl Default for ffi::uzlib_uncomp_t {
    fn default() -> Self {
        unsafe { MaybeUninit::<Self>::zeroed().assume_init() }
    }
}

pub struct UzlibContext<'a> {
    uncomp: ffi::uzlib_uncomp_t,
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

    /// Implement the uzlib source-read callback: return the next byte of
    /// compressed data, or `None` at EOF.
    ///
    /// In MicroPython >= 1.20 the source callback receives only the user
    /// context (`source_read_data`), not the `uzlib_uncomp` struct, so we can
    /// no longer hand uzlib a buffer window to consume directly. Instead we
    /// keep our own small read buffer and feed uzlib one byte per call,
    /// refilling it from the backing data as needed.
    pub fn reader_callback(&mut self) -> Option<u8> {
        if self.buf_head >= self.buf_tail {
            // internal buffer exhausted: refill from the backing data
            let bytes_read = self.data.read(self.offset, self.buf.as_mut());
            self.buf_head = 0;
            self.buf_tail = bytes_read;
            self.offset += bytes_read;
            if bytes_read == 0 {
                return None; // EOF
            }
        }
        let byte = self.buf[self.buf_head];
        self.buf_head += 1;
        Some(byte)
    }
}

pub struct ZlibInflate<'a> {
    /// Compressed data reader
    data: RefCell<SourceReadContext<'a>>,
    /// Uzlib context
    uncomp: ffi::uzlib_uncomp_t,
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
        let res = unsafe {
            // Source data callback, invoked by uzlib one byte at a time. We keep
            // `uncomp.source`/`source_limit` null so every input byte is read
            // through this callback (see `SourceReadContext::reader_callback`).
            self.uncomp.source_read_cb = Some(zlib_reader_callback);
            // Context for the source data callback: the SourceReadContext cell.
            self.uncomp.source_read_data = &self.data as *const _ as *mut cty::c_void;

            // Destination buffer
            self.uncomp.dest = dest.as_mut_ptr();
            self.uncomp.dest_limit = self.uncomp.dest.add(dest.len());

            // SAFETY:
            // Even if the `ZlibInflate` instance is moved, the context pointer is
            // still valid as we set it before calling `uzlib_uncompress`.
            ffi::uzlib_uncompress(&mut self.uncomp)
        };

        // Clear the source read context (just for safety)
        self.uncomp.source_read_data = core::ptr::null_mut();

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
unsafe extern "C" fn zlib_reader_callback(context: *mut cty::c_void) -> i32 {
    // SAFETY: `context` is the `source_read_data` we set in `read()`, a pointer
    // to the RefCell holding the source-read state. It stays valid for the
    // duration of the `uzlib_uncompress` call.
    let ctx = context as *const RefCell<SourceReadContext>;
    let mut ctx = unwrap!(unsafe { ctx.as_ref() }).borrow_mut();

    match ctx.reader_callback() {
        Some(byte) => byte as i32,
        None => -1, // EOF
    }
}
