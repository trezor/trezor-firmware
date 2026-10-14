//! Per-app state of the API implementation.
//!
//! The API runs on the calling app's own task, under that app's MPU regions:
//! it may use the app's memory (data, stack and heap) and Core's code, but not
//! Core's `.data`/`.bss`. So this crate keeps no writable statics of its own.
//! Each app's state is an [`AppState`] on the app's own stack (in
//! [`crate::coreapp_app_entry`], which outlives `applet_main`), reached
//! through one per-task pointer in Core's TLS area: the region the MPU maps
//! writable for app tasks, and which the scheduler saves and restores on
//! every task switch.
//!
//! When an app is stopped, its task, stack and heap go away together with its
//! state, so Core is left holding nothing that points into the stopped app.

use core::ptr::null_mut;
use core::sync::atomic::{AtomicPtr, Ordering};

use rtl::fatal_error;
use spin::{Mutex, Once};
use sys::ipc::IpcInbox;
use talc::DefaultBinning;
use talc::base::Talc;
use talc::source::Manual;

pub(crate) struct AppState {
    /// Allocator over the app's heap. Also Core's `#[global_allocator]`
    /// backend (see [`crate::allocator`]).
    pub allocator: Mutex<Talc<Manual, DefaultBinning>>,
    /// The app's IPC inbox, registered by [`crate::wire::register_inbox`].
    pub inbox: Once<IpcInbox<&'static mut [usize]>>,
}

impl AppState {
    /// Creates the state of an app whose heap is `heap_size` bytes at
    /// `heap_base`.
    ///
    /// # Safety
    ///
    /// The heap must be valid, unused memory owned by the app for as long as
    /// the returned state is in use.
    pub unsafe fn new(heap_base: *mut u8, heap_size: usize) -> Self {
        let mut talc = Talc::new(Manual);
        // SAFETY: guaranteed by the caller
        if unsafe { talc.claim(heap_base, heap_size) }.is_none() {
            fatal_error!("failed to claim heap for the app allocator");
        }
        Self {
            allocator: Mutex::new(talc),
            inbox: Once::new(),
        }
    }
}

// The state of the app running on the current task, or null on a task
// without an app (Core's own task). On the emulator every task is its own
// thread, so a thread-local works; on hardware, `.tls` is swapped per task.
#[cfg_attr(target_os = "none", unsafe(link_section = ".tls"))]
#[cfg_attr(not(target_os = "none"), thread_local)]
static APP_STATE: AtomicPtr<AppState> = AtomicPtr::new(null_mut());

/// Runs `f` with `state` installed as the current task's app state.
pub(crate) fn with_app_state<R>(state: &AppState, f: impl FnOnce() -> R) -> R {
    APP_STATE.store(state as *const _ as *mut _, Ordering::Relaxed);
    let result = f();
    APP_STATE.store(null_mut(), Ordering::Relaxed);
    result
}

/// The state of the app running on the current task, if any.
pub(crate) fn try_get() -> Option<&'static AppState> {
    // SAFETY: the pointer is only set by `with_app_state`, for as long as the
    // state it points to is alive; it is never shared with another task.
    unsafe { APP_STATE.load(Ordering::Relaxed).as_ref() }
}

/// The state of the app running on the current task.
pub(crate) fn get() -> &'static AppState {
    match try_get() {
        Some(state) => state,
        None => fatal_error!("API used outside of an app"),
    }
}
