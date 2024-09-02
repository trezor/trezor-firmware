use crate::{ui::shape::DrawingCache, util::Lock};

use spin::MutexGuard;
use static_alloc::Bump;

/// Memory reserved for `ProgressiveRenderer`s shape storage.
/// ProgressiveRenderer is used if framebuffer is not available.
#[cfg(not(feature = "xframebuffer"))]
pub const SHAPE_MEM_SIZE: usize = 5 * 1024;
#[cfg(feature = "xframebuffer")]
pub const SHAPE_MEM_SIZE: usize = 0;

/// Maximum number of shapes on a single screen
/// (if you change it, you will probably need to change
/// the memory size above)
#[cfg(not(feature = "xframebuffer"))]
pub const SHAPE_MAX_COUNT: usize = 45;
#[cfg(feature = "xframebuffer")]
pub const SHAPE_MAX_COUNT: usize = 0;

/// Size of bump memory that might not be accessible by DMA
pub const BUMP_NODMA_SIZE: usize = DrawingCache::get_bump_nodma_size() + SHAPE_MEM_SIZE;
/// Bump allocator that doesn't need DMA.
#[cfg_attr(not(target_os = "macos"), link_section = ".no_dma_buffers")]
static mut BUMP_NODMA: Bump<[u8; BUMP_NODMA_SIZE]> = Bump::uninit();

/// Size of bump memory that must be accessible by DMA
pub const BUMP_DMA_SIZE: usize = DrawingCache::get_bump_dma_size();
/// Bump allocator B that needs DMA.
#[cfg_attr(not(target_os = "macos"), link_section = ".buf")]
static mut BUMP_DMA: Bump<[u8; BUMP_DMA_SIZE]> = Bump::uninit();

pub struct Bumps<'a> {
    /// Mutex guard ensuring that we are the only ones holding the bump
    /// allocators. Note that the lifetime argument 'a unifies with the &'a
    /// mut Bump, forcing the lifetime of those mut refs to not outlive the
    /// guard.
    guard: MutexGuard<'a, ()>,
    pub nodma: &'a mut Bump<[u8; BUMP_NODMA_SIZE]>,
    pub dma: &'a mut Bump<[u8; BUMP_DMA_SIZE]>,
}

static BUMPS_LOCK: Lock<()> = Lock::new(());

impl<'a> Bumps<'a> {
    /// Lock the bump allocator memory and gain access to it through the
    /// returned guard.
    pub fn lock() -> Self {
        let guard = BUMPS_LOCK.lock();

        // SAFETY:
        // Guard is locked so no other mut refs to bump allocators exist
        let nodma = unsafe { &mut *core::ptr::addr_of_mut!(BUMP_NODMA) };
        let dma = unsafe { &mut *core::ptr::addr_of_mut!(BUMP_DMA) };

        nodma.reset();
        dma.reset();

        Self { guard, nodma, dma }
    }

    /// Force unlock the bump allocator memory.
    ///
    /// # Safety
    ///
    /// This function must be invoked exclusively in failure scenarios.
    pub unsafe fn force_unlock() {
        unsafe { BUMPS_LOCK.force_unlock() };
    }
}

/// This function enables nested invocations of `run_with_bumps()`,
/// which is necessary when the application needs to display a
/// fatal error message and subsequently terminate.
///
/// # Safety
/// This function must be invoked exclusively in failure scenarios
/// where the application is required to display a fatal error
/// message and then shut down. It is safe to call this function
/// only under these specific conditions.
pub unsafe fn unlock_bumps_on_failure() {
    // The application is single-threaded, so we can safely use a
    // static variable as a lock against nested calls.
    unsafe {
        Bumps::force_unlock();
    };
}
