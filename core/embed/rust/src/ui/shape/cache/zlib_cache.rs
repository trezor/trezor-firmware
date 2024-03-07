use crate::{
    trezorhal::uzlib::{UzlibContext, UZLIB_WINDOW_SIZE},
    ui::display::toif::Toif,
};
use core::cell::UnsafeCell;
use without_alloc::{alloc::LocalAllocLeakExt, FixedVec};

struct ZlibCacheSlot<'a> {
    /// Reference to compressed data
    zdata: &'a [u8],
    /// Current offset in docempressed data
    offset: usize,
    /// Decompression context for the current zdata
    dc: Option<UzlibContext<'a>>,
    /// Window used by current decompression context.
    /// (It's used just by own dc and nobody else.)
    window: &'a UnsafeCell<[u8; UZLIB_WINDOW_SIZE]>,
}

impl<'a> ZlibCacheSlot<'a> {
    fn new<'alloc: 'a, T>(bump: &'alloc T) -> Option<Self>
    where
        T: LocalAllocLeakExt<'alloc>,
    {
        let window = bump
            .alloc_t::<UnsafeCell<[u8; UZLIB_WINDOW_SIZE]>>()?
            .uninit
            .init(UnsafeCell::new([0; UZLIB_WINDOW_SIZE]));

        Some(Self {
            zdata: &[],
            offset: 0,
            dc: None,
            window,
        })
    }

    /// May be called with zdata == &[] to make the slot free
    fn reset(&mut self, zdata: &'a [u8]) {
        // Drop the existing decompression context holding
        // a mutable reference to window buffer
        self.dc = None;

        if !zdata.is_empty() {
            // Now there's nobody else holding any reference to our window
            // so we can get mutable reference and pass it to a new
            // instance of the decompression context
            let window = unsafe { &mut *self.window.get() };

            self.dc = Some(UzlibContext::new(zdata, Some(window)));
        }

        self.offset = 0;
        self.zdata = zdata;
    }

    fn uncompress(&mut self, dest_buf: &mut [u8]) -> Result<bool, ()> {
        if let Some(dc) = self.dc.as_mut() {
            match dc.uncompress(dest_buf) {
                Ok(done) => {
                    if done {
                        self.reset(&[]);
                    } else {
                        self.offset += dest_buf.len();
                    }
                    Ok(done)
                }
                Err(e) => Err(e),
            }
        } else {
            Err(())
        }
    }

    fn skip(&mut self, nbytes: usize) -> Result<bool, ()> {
        if let Some(dc) = self.dc.as_mut() {
            match dc.skip(nbytes) {
                Ok(done) => {
                    if done {
                        self.reset(&[]);
                    } else {
                        self.offset += nbytes;
                    }

                    Ok(done)
                }
                Err(e) => Err(e),
            }
        } else {
            Err(())
        }
    }

    fn is_for(&self, zdata: &[u8], offset: usize) -> bool {
        self.zdata == zdata && self.offset == offset
    }
}

pub struct ZlibCache<'a> {
    slots: FixedVec<'a, ZlibCacheSlot<'a>>,
}

impl<'a> ZlibCache<'a> {
    pub fn new<'alloc: 'a, T>(bump: &'alloc T, slot_count: usize) -> Option<Self>
    where
        T: LocalAllocLeakExt<'alloc>,
    {
        let mut cache = Self {
            slots: bump.fixed_vec(slot_count)?,
        };

        for _ in 0..cache.slots.capacity() {
            unwrap!(cache.slots.push(ZlibCacheSlot::new(bump)?)); // should never fail
        }

        Some(cache)
    }

    fn select_slot_for_reuse(&self) -> Result<usize, ()> {
        if self.slots.capacity() > 0 {
            let mut selected = 0;
            for (i, slot) in self.slots.iter().enumerate() {
                if slot.dc.is_none() {
                    selected = i;
                    break;
                }
            }
            Ok(selected)
        } else {
            Err(())
        }
    }

    pub fn uncompress(
        &mut self,
        zdata: &'a [u8],
        offset: usize,
        dest_buf: &mut [u8],
    ) -> Result<bool, ()> {
        let slot = self
            .slots
            .iter_mut()
            .find(|slot| slot.is_for(zdata, offset));

        if let Some(slot) = slot {
            slot.uncompress(dest_buf)
        } else {
            let selected = self.select_slot_for_reuse()?;
            let slot = &mut self.slots[selected];
            slot.reset(zdata);
            slot.skip(offset)?;
            slot.uncompress(dest_buf)
        }
    }

    pub fn uncompress_toif(
        &mut self,
        toif: Toif<'a>,
        from_row: i16,
        dest_buf: &mut [u8],
    ) -> Result<(), ()> {
        let from_offset = toif.stride() * from_row as usize;
        self.uncompress(toif.zdata(), from_offset, dest_buf)?;
        Ok(())
    }
}
