use core::alloc::Layout;

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
pub unsafe trait GlobalAllocatorV1: Send + Sync {
    unsafe extern "C" fn alloc(&self, layout: FfiLayout) -> *mut u8;
    unsafe extern "C" fn dealloc(&self, ptr: *mut u8, layout: FfiLayout);
    unsafe extern "C" fn alloc_zeroed(&self, layout: FfiLayout) -> *mut u8;
    unsafe extern "C" fn realloc(
        &self,
        ptr: *mut u8,
        layout: FfiLayout,
        new_size: usize,
    ) -> *mut u8;
}

pub type GlobalAllocatorV1Vtable = stabby::vtable!(GlobalAllocatorV1 + Send + Sync);
pub type GlobalAllocatorV1Ref<'a> = stabby::DynRef<'a, GlobalAllocatorV1Vtable>;
