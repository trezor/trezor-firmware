#![no_std]
#![cfg_attr(not(target_os = "none"), feature(thread_local))]

use rtl::fatal_error;
use trezor_app_sdk::traits::{ApiGetter, ApiVariant};

extern crate alloc;

pub mod allocator;
mod app_state;
mod crypto;
mod syslog;
mod ui;
mod v1;
mod wire;

// The API getter handed to every loaded app, by `coreapp_app_entry` below.
// Exported under a stable symbol name because it is the entry point of
// Core's whole app-facing ABI surface, even though nothing outside this
// crate references it any more.
#[unsafe(no_mangle)]
pub extern "C" fn coreapp_api_get(version: u32) -> ApiVariant {
    if version != 1 {
        fatal_error!("Unsupported API version");
    }
    ApiVariant::V1(&v1::TREZOR_API_V1)
}

// The entry point a newly loaded app's task is started on, instead of the
// app's own `applet_main`. The loader (`core/embed/io/app_arena/*/
// app_loader.c`, via `coreapp_get_app_entry()`) schedules *this* function
// and passes it the app's launch arguments ([`io::AppArgs`]), including
// `applet_main`, so Core gets to run on the app's task before the app does.
//
// The point of the inversion is the app's [`app_state::AppState`]: it lives
// in this function's frame on the app's own stack, for as long as
// `applet_main` runs, and has to be in place before the app executes a single
// instruction — the app's `#[global_allocator]` forwards every allocation
// over the API vtable to the allocator in that state.
//
// The launch arguments are copied onto the app's stack (or into its data
// area on the emulator), so no syscall is needed to query them.
//
// Same "C only ever takes its address" contract as `coreapp_api_get` above:
// `core/embed/sys/task/*/coreapp.c` declares this as
// `extern int coreapp_app_entry(const void* args)` and never calls it, so
// the declared C parameter type does not need to match the real one below.
#[unsafe(no_mangle)]
pub extern "C" fn coreapp_app_entry(args: &io::AppArgs) -> core::ffi::c_int {
    let args = *args;
    // SAFETY: the loader sets `applet_main` to the app's own entry point
    // (checked non-null), which has exactly this signature.
    let applet_main: extern "C" fn(ApiGetter) -> core::ffi::c_int =
        unsafe { core::mem::transmute(args.applet_main) };
    let heap = core::ptr::slice_from_raw_parts_mut(args.heap_ptr.cast::<u8>(), args.heap_size);
    // SAFETY: the loader hands this app a heap of its own, which lives as
    // long as the app's task; the state created here is its only owner.
    let state = unsafe { app_state::AppState::new(heap.cast(), heap.len()) };
    app_state::with_app_state(&state, || {
        // The inbox is allocated out of the app's heap, so it needs the state.
        wire::register_inbox(args.ipc_buffer_size);
        init_task_zkp_context();
        applet_main(coreapp_api_get)
    })
}

// TEMPORARY: the app task needs its own secp256k1-zkp context to verify and
// recover secp256k1 signatures (see `::crypto::ecdsa::init_task_context`).
// Only a pointer to it fits into the task's TLS, so the context itself goes
// on the app's heap; it is never freed, as it lives as long as the app.
fn init_task_zkp_context() {
    let size = ::crypto::ecdsa::task_context_size();
    if size == 0 {
        return;
    }
    let Ok(layout) =
        core::alloc::Layout::from_size_align(size, ::crypto::ecdsa::TASK_CONTEXT_ALIGN)
    else {
        fatal_error!("invalid secp256k1 context layout");
    };
    // SAFETY: `layout` has a non-zero size.
    let buffer = unsafe { alloc::alloc::alloc(layout) };
    // SAFETY: `buffer` is a fresh, never freed allocation of `layout`.
    if buffer.is_null() || unsafe { ::crypto::ecdsa::init_task_context(buffer, size) }.is_err() {
        fatal_error!("failed to create the app's secp256k1 context");
    }
}
