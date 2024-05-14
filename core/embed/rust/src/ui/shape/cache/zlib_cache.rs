use crate::{
    io::BinaryData,
    trezorhal::uzlib::{ZlibInflate, UZLIB_WINDOW_SIZE},
    ui::display::image::ToifInfo,
};
use core::cell::UnsafeCell;
use without_alloc::{alloc::LocalAllocLeakExt, FixedVec};

struct ZlibCacheSlot<'a> {
    /// Decompression context for the current zdata.
    /// If `None`, the slot is free to be used.
    dc: Option<ZlibInflate<'a>>,
    /// Reference to compressed data
    image: Option<BinaryData<'a>>,
    /// Current offset in decompressed data
    output_offset: usize,
    /// Window used by current decompression context.
    /// (It's used just by own dc and nobody else.)
    window: &'a UnsafeCell<[u8; UZLIB_WINDOW_SIZE]>,
}

impl<'a> ZlibCacheSlot<'a> {
    fn new<T>(bump: &'a T) -> Option<Self>
    where
        T: LocalAllocLeakExt<'a>,
    {
        let window = bump
            .alloc_t()?
            .uninit
            .init(UnsafeCell::new([0; UZLIB_WINDOW_SIZE]));

        Some(Self {
            dc: None,
            image: None,
            output_offset: 0,
            window,
        })
    }

    /// Calling with None makes the slot free
    fn reset(&mut self, image: Option<BinaryData<'a>>) {
        // Drop the existing decompression context holding
        // a mutable reference to window buffer
        self.dc = None;

        if let Some(image) = image {
            // Now there's nobody else holding any reference to our window
            // so we can get mutable reference and pass it to a new
            // instance of the decompression context
            let window = unsafe { &mut *self.window.get() };

            self.dc = Some(ZlibInflate::new(image, ToifInfo::HEADER_LENGTH, window));
        }

        self.output_offset = 0;
        self.image = image;
    }

    fn uncompress(&mut self, dest_buf: &mut [u8]) -> Result<bool, ()> {
        if let Some(dc) = self.dc.as_mut() {
            match dc.read(dest_buf) {
                Ok(done) => {
                    if done {
                        self.reset(None);
                    } else {
                        self.output_offset += dest_buf.len();
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
                        self.reset(None);
                    } else {
                        self.output_offset += nbytes;
                    }

                    Ok(done)
                }
                Err(e) => Err(e),
            }
        } else {
            Err(())
        }
    }

    fn is_for(&self, image: BinaryData<'a>, offset: usize) -> bool {
        match self.image {
            Some(current) => current == image && self.output_offset == offset,
            None => false,
        }
    }
}

pub struct ZlibCache<'a> {
    slots: FixedVec<'a, ZlibCacheSlot<'a>>,
}

impl<'a> ZlibCache<'a> {
    pub fn new<T>(bump: &'a T, slot_count: usize) -> Option<Self>
    where
        T: LocalAllocLeakExt<'a>,
    {
        let mut cache = Self {
            slots: bump.fixed_vec(slot_count)?,
        };

        for _ in 0..cache.slots.capacity() {
            cache.slots.push(ZlibCacheSlot::new(bump)?).ok()?;
        }

        Some(cache)
    }

    fn select_slot_for_reuse(&self) -> Result<usize, ()> {
        if self.slots.capacity() > 0 {
            // Try to find a free slot.  If there's no free slot,
            // select the one that performed the least amount of work
            // based on the offset in the uncompressed data.
            let mut selected = 0;
            for (i, slot) in self.slots.iter().enumerate() {
                if slot.dc.is_none() {
                    selected = i;
                    break;
                } else if slot.output_offset < self.slots[selected].output_offset {
                    selected = i;
                }
            }
            Ok(selected)
        } else {
            Err(())
        }
    }

    pub fn uncompress(
        &mut self,
        image: BinaryData<'a>,
        offset: usize,
        dest_buf: &mut [u8],
    ) -> Result<bool, ()> {
        let slot = self
            .slots
            .iter_mut()
            .find(|slot| slot.is_for(image, offset));

        let slot = match slot {
            Some(slot) => slot,
            None => {
                let selected = self.select_slot_for_reuse()?;
                let slot = &mut self.slots[selected];
                slot.reset(Some(image));
                slot.skip(offset)?;
                slot
            }
        };

        slot.uncompress(dest_buf)
    }

    pub fn uncompress_toif(
        &mut self,
        image: BinaryData<'a>,
        from_row: i16,
        dest_buf: &mut [u8],
    ) -> Result<(), ()> {
        // TODO: optimize this
        let info = ToifInfo::parse(image).ok_or(())?;
        let from_offset = info.stride() * from_row as usize;
        self.uncompress(image, from_offset, dest_buf)?;
        Ok(())
    }

    pub const fn get_bump_size(slot_count: usize) -> usize {
        (core::mem::size_of::<ZlibCacheSlot>()
            + core::mem::size_of::<UnsafeCell<[u8; UZLIB_WINDOW_SIZE]>>()
            + 16)
            * slot_count
    }
}
