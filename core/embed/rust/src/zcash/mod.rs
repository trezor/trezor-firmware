pub mod diag;
pub mod orchardlib;

use static_alloc::Bump;

// panics for heap < 64kb
#[global_allocator]
static A: Bump<[u8; 1 << 18]> = Bump::uninit(); // 8kB heap
