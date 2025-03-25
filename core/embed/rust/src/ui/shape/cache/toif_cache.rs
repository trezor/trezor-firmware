use crate::{
    io::BinaryData,
    ui::{
        display::{image::ToifInfo, Color},
        geometry::{Offset, Rect},
        shape::{Bitmap, BitmapFormat, Canvas},
    },
};
use core::cell::{Cell, UnsafeCell};
use without_alloc::{alloc::LocalAllocLeakExt, FixedVec};

// Fixed buffer size for each TOIF cache slot
// Each slot can hold up to 6000 bytes of uncompressed data, reasonable for Eckhart Homescreen tiles
const TOIF_SLOT_BUFFER_SIZE: usize = 6000;

struct ToifCacheSlot<'a> {
    /// Reference to original TOIF data
    image: Option<BinaryData<'a>>,
    /// Uncompressed bitmap data buffer
    data: &'a UnsafeCell<[u8; TOIF_SLOT_BUFFER_SIZE]>,
    /// Size of the image
    size: Offset,
    /// Bitmap format
    format: BitmapFormat,
    /// Stride in bytes
    stride: usize,
    /// Reference counter to track usage
    ref_count: Cell<usize>,
    /// Last access timestamp for LRU eviction
    last_access: Cell<u32>,
}

impl<'a> ToifCacheSlot<'a> {
    fn new<T>(bump: &'a T) -> Option<Self>
    where
        T: LocalAllocLeakExt<'a>,
    {
        // Allocate a fixed-size buffer using the bump allocator
        let data = bump
            .alloc_t()?
            .uninit
            .init(UnsafeCell::new([0; TOIF_SLOT_BUFFER_SIZE]));

        Some(Self {
            image: None,
            data,
            size: Offset::zero(),
            format: BitmapFormat::MONO4, // Default
            stride: 0,
            ref_count: Cell::new(0),
            last_access: Cell::new(0),
        })
    }

    fn reset(&mut self) {
        self.image = None;
        self.size = Offset::zero();
        self.stride = 0;
        self.ref_count.set(0);
    }

    fn is_for(&self, image: BinaryData<'a>) -> bool {
        match self.image {
            Some(current) => current == image,
            None => false,
        }
    }

    fn is_empty(&self) -> bool {
        self.image.is_none()
    }

    fn update_access(&self, timestamp: u32) {
        self.last_access.set(timestamp);
    }

    fn increment_ref(&self) {
        self.ref_count.set(self.ref_count.get() + 1);
    }

    fn decrement_ref(&self) -> bool {
        let count = self.ref_count.get();
        if count > 1 {
            self.ref_count.set(count - 1);
            false
        } else {
            self.ref_count.set(0);
            true
        }
    }

    fn draw_to_canvas(
        &self,
        canvas: &mut dyn Canvas,
        bounds: Rect,
        fg_color: Option<Color>,
        bg_color: Option<Color>,
        alpha: u8,
    ) -> bool {
        if self.image.is_none() {
            return false;
        }

        // Create a safe reference to the data
        let data_ref = unsafe { &*self.data.get() };

        // Create a temporary bitmap that references our long-lived data
        let bitmap = match Bitmap::new(self.format, Some(self.stride), self.size, None, data_ref) {
            Ok(bitmap) => bitmap,
            Err(_) => return false,
        };

        // Get a view with the desired properties
        let mut view = bitmap.view();

        // Apply customizations
        if let Some(fg) = fg_color {
            view = view.with_fg(fg);
        }

        view = view.with_alpha(alpha);

        // Draw to the canvas
        match bg_color {
            Some(bg) => canvas.draw_bitmap(bounds, view.with_bg(bg)),
            None => canvas.blend_bitmap(bounds, view),
        }

        true
    }
}

pub struct ToifCache<'a> {
    /// Slots for caching decompressed TOIFs
    slots: FixedVec<'a, ToifCacheSlot<'a>>,
    /// Time counter for LRU tracking
    time_counter: Cell<u32>,
}

impl<'a> ToifCache<'a> {
    pub fn new<T>(bump: &'a T, slot_count: usize) -> Option<Self>
    where
        T: LocalAllocLeakExt<'a>,
    {
        // Following the ZlibCache pattern of using FixedVec
        let mut cache = Self {
            slots: bump.fixed_vec(slot_count)?,
            time_counter: Cell::new(0),
        };

        // Initialize each slot
        for _ in 0..cache.slots.capacity() {
            cache.slots.push(ToifCacheSlot::new(bump)?).ok()?;
        }

        Some(cache)
    }

    fn tick(&self) -> u32 {
        let time = self.time_counter.get() + 1;
        self.time_counter.set(time);
        time
    }

    // Find index of slot containing the image
    fn find_slot_index_for_image(&self, image: BinaryData<'a>) -> Option<usize> {
        for (i, slot) in self.slots.iter().enumerate() {
            if slot.is_for(image) {
                return Some(i);
            }
        }
        None
    }

    // Find an empty slot or the least recently used one
    fn find_empty_or_lru_slot_index(&self) -> usize {
        let mut selected_idx = 0;
        let mut min_access_time = u32::MAX;

        // First pass: look for empty slots
        for (i, slot) in self.slots.iter().enumerate() {
            if slot.is_empty() {
                return i; // Return immediately if we find an empty slot
            }

            if slot.last_access.get() < min_access_time {
                min_access_time = slot.last_access.get();
                selected_idx = i;
            }
        }

        selected_idx
    }

    // Draw the image directly to canvas
    pub fn draw_to_canvas(
        &mut self,
        image: BinaryData<'a>,
        canvas: &mut dyn Canvas,
        bounds: Rect,
        fg_color: Option<Color>,
        bg_color: Option<Color>,
        alpha: u8,
        zlib_cache: &mut crate::ui::shape::cache::zlib_cache::ZlibCache<'a>,
    ) -> bool {
        // Try to find the image in the cache
        if let Some(slot_idx) = self.find_slot_index_for_image(image) {
            // Image found in cache
            let slot = &self.slots[slot_idx];

            // Update access tracking
            slot.update_access(self.tick());
            slot.increment_ref();

            // Draw it directly
            return slot.draw_to_canvas(canvas, bounds, fg_color, bg_color, alpha);
        }

        // Not found, need to cache it first

        // Get TOIF info
        let info = match ToifInfo::parse(image) {
            Some(info) => info,
            None => return false,
        };

        let stride = info.stride();
        let size = info.size();
        let total_size = stride * size.y as usize;

        // Check if the image is too large for our buffer
        if total_size > TOIF_SLOT_BUFFER_SIZE {
            return false;
        }

        // Get timestamp before any mutable borrows
        let timestamp = self.tick();

        // Find a slot to use
        let slot_idx = self.find_empty_or_lru_slot_index();

        // Reset the slot if it's not empty
        if !self.slots[slot_idx].is_empty() {
            self.slots[slot_idx].reset();
        }

        // Get the slot (now definitely empty)
        let slot = &mut self.slots[slot_idx];

        // Get data buffer
        let buffer = unsafe { &mut *slot.data.get() };

        // Decompress the image
        if zlib_cache
            .uncompress_toif(image, 0, &mut buffer[..total_size])
            .is_err()
        {
            return false;
        }

        // Update slot metadata
        slot.image = Some(image);
        slot.size = size;
        slot.format = if info.is_grayscale() {
            BitmapFormat::MONO4
        } else {
            BitmapFormat::RGB565
        };
        slot.stride = stride;
        slot.ref_count.set(1);
        slot.update_access(timestamp);

        // Draw it
        slot.draw_to_canvas(canvas, bounds, fg_color, bg_color, alpha)
    }

    pub fn release(&mut self, image: BinaryData<'a>) {
        if let Some(slot_idx) = self.find_slot_index_for_image(image) {
            let slot = &self.slots[slot_idx];
            if slot.decrement_ref() {
                // If reference count reaches zero, we could optionally reset
                // the slot, but it's probably better to keep the data
                // for potential reuse
            }
        }
    }

    pub fn clear(&mut self) {
        for slot in self.slots.iter_mut() {
            slot.reset();
        }
    }

    pub const fn get_bump_size(slot_count: usize) -> usize {
        // Size for the FixedVec structure
        let vec_size = core::mem::size_of::<FixedVec<ToifCacheSlot>>();
        // Size for each slot's structure
        let slot_size = core::mem::size_of::<ToifCacheSlot>() * slot_count;
        // Size for all the UnsafeCell buffers
        let buffer_size =
            core::mem::size_of::<UnsafeCell<[u8; TOIF_SLOT_BUFFER_SIZE]>>() * slot_count;
        // Total size with some padding for alignment
        vec_size + slot_size + buffer_size + 64
    }
}
