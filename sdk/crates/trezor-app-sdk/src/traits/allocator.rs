use core::alloc::Layout;

/// A stable-ABI [`Layout`]: size and alignment of an allocation.
#[stabby::stabby]
#[repr(C)]
pub struct FfiLayout {
    size: usize,
    align: usize,
}

impl From<Layout> for FfiLayout {
    fn from(layout: Layout) -> Self {
        Self {
            size: layout.size(),
            align: layout.align(),
        }
    }
}

impl From<FfiLayout> for Layout {
    fn from(layout: FfiLayout) -> Self {
        unsafe { Layout::from_size_align_unchecked(layout.size, layout.align) }
    }
}

#[stabby::stabby(checked)]
/// Heap allocation for an app, served by Core from the app's heap region.
///
/// # Safety
///
/// Implementations must uphold the [`GlobalAlloc`](core::alloc::GlobalAlloc) contract.
pub unsafe trait GlobalAllocatorV1: Send + Sync {
    /// Allocates memory for `layout`; null on failure.
    unsafe extern "C" fn alloc(&self, layout: FfiLayout) -> *mut u8;

    /// Frees memory previously allocated with `layout`.
    unsafe extern "C" fn dealloc(&self, ptr: *mut u8, layout: FfiLayout);

    /// Like [`Self::alloc`], with the memory zeroed.
    unsafe extern "C" fn alloc_zeroed(&self, layout: FfiLayout) -> *mut u8;

    /// Resizes an allocation to `new_size` bytes; null on failure.
    unsafe extern "C" fn realloc(
        &self,
        ptr: *mut u8,
        layout: FfiLayout,
        new_size: usize,
    ) -> *mut u8;
}

/// The stabby vtable of [`GlobalAllocatorV1`].
pub type GlobalAllocatorV1Vtable = stabby::vtable!(GlobalAllocatorV1 + Send + Sync);
/// A borrowed `dyn GlobalAllocatorV1`.
pub type GlobalAllocatorV1Ref<'a> = stabby::DynRef<'a, GlobalAllocatorV1Vtable>;
