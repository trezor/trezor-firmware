use crate::ui::shape::DrawingCache;

use static_alloc::Bump;

/// Memory reserved for `ProgressiveRenderer`s shape storage.
/// ProgressiveRenderer is used if framebuffer is not available.
#[cfg(not(feature = "framebuffer"))]
pub const SHAPE_MEM_SIZE: usize = 5 * 1024;
#[cfg(feature = "framebuffer")]
pub const SHAPE_MEM_SIZE: usize = 0;

/// Maximum number of shapes on a single screen
/// (if you change it, you will probably need to change
/// the memory size above)
#[cfg(not(feature = "framebuffer"))]
pub const SHAPE_MAX_COUNT: usize = 45;
#[cfg(feature = "framebuffer")]
pub const SHAPE_MAX_COUNT: usize = 0;

/// Size of `bump_a` memory that might not be accessible by DMA
pub const BUMP_A_SIZE: usize = DrawingCache::get_bump_a_size() + SHAPE_MEM_SIZE;
/// Size of `bump_b` memory that must be accessible by DMA
pub const BUMP_B_SIZE: usize = DrawingCache::get_bump_b_size();

//
static mut LOCKED: bool = false;

/// Runs a user-defined function with two bump allocators.
///
/// The function is passed two bump allocators, `bump_a` and `bump_b`, which
/// can be used to allocate memory for temporary objects.
///
/// The function calls cannot be nested. The function panics if that happens.
pub fn run_with_bumps<F>(func: F)
where
    F: for<'a> FnOnce(&'a mut Bump<[u8; BUMP_A_SIZE]>, &'a mut Bump<[u8; BUMP_B_SIZE]>),
{
    // SAFETY:
    // The application is single-threaded, so we can safely use a
    // static variable as a lock against nested calls.
    ensure!(unsafe { !LOCKED }, "nested run_with_bumps!");

    unsafe {
        LOCKED = true;
    };

    #[cfg_attr(not(target_os = "macos"), link_section = ".no_dma_buffers")]
    static mut BUMP_A: Bump<[u8; BUMP_A_SIZE]> = Bump::uninit();

    #[cfg_attr(not(target_os = "macos"), link_section = ".buf")]
    static mut BUMP_B: Bump<[u8; BUMP_B_SIZE]> = Bump::uninit();

    // SAFETY:
    // The function cannot be nested, so we can safely
    // use the static bump allocators.
    let bump_a = unsafe { &mut *core::ptr::addr_of_mut!(BUMP_A) };
    let bump_b = unsafe { &mut *core::ptr::addr_of_mut!(BUMP_B) };

    bump_a.reset();
    bump_b.reset();

    func(bump_a, bump_b);

    unsafe {
        LOCKED = false;
    };
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
        LOCKED = false;
    };
}
