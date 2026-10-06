//! Safe wrapper around the kernel's event-readiness API
//! (`sys/task/inc/sys/sysevent.h`), used to block a task until one of a set
//! of device/IPC handles becomes ready, or a deadline passes.

pub use ffi::syshandle_t as SysHandle;

use crate::ffi;
#[cfg(feature = "ipc")]
use crate::task::TaskId;
use crate::time::{Instant, Timeout};

/// A bitmask of [`SysHandle`]s.
#[derive(Copy, Clone, PartialEq, Eq, Default)]
pub struct HandleSet(ffi::syshandle_mask_t);

impl HandleSet {
    pub const fn empty() -> Self {
        Self(0)
    }

    pub const fn new(handles: &[SysHandle]) -> Self {
        let mut set = Self::empty();
        let mut idx = 0;
        while idx < handles.len() {
            set = set.with(handles[idx]);
            idx += 1;
        }
        set
    }

    pub const fn with(self, handle: SysHandle) -> Self {
        Self(self.0 | 1 << (handle as u32))
    }

    pub const fn contains(self, handle: SysHandle) -> bool {
        self.0 & (1 << (handle as u32)) != 0
    }
}

/// The read/write readiness of a set of [`SysHandle`]s, as awaited by or
/// returned from [`poll`].
#[derive(Copy, Clone, PartialEq, Eq, Default)]
pub struct SysEvents {
    pub read: HandleSet,
    pub write: HandleSet,
}

impl SysEvents {
    pub const fn empty() -> Self {
        Self {
            read: HandleSet::empty(),
            write: HandleSet::empty(),
        }
    }

    pub const fn reading(handles: &[SysHandle]) -> Self {
        Self {
            read: HandleSet::new(handles),
            write: HandleSet::empty(),
        }
    }

    pub const fn writing(handles: &[SysHandle]) -> Self {
        Self {
            read: HandleSet::empty(),
            write: HandleSet::new(handles),
        }
    }

    pub fn with_read(self, handles: &[SysHandle]) -> Self {
        Self {
            read: HandleSet::new(handles),
            write: self.write,
        }
    }

    pub fn with_write(self, handles: &[SysHandle]) -> Self {
        Self {
            read: self.read,
            write: HandleSet::new(handles),
        }
    }
}

/// Blocks until at least one of the events in `awaited` is signalled, or
/// `deadline` passes.
///
/// Returns the events that were actually signalled — empty if the deadline
/// expired first.
pub fn poll(awaited: SysEvents, deadline: Instant) -> SysEvents {
    let awaited = ffi::sysevents_t {
        read_ready: awaited.read.0,
        write_ready: awaited.write.0,
    };
    let mut signalled = ffi::sysevents_t {
        read_ready: 0,
        write_ready: 0,
    };
    // SAFETY: both pointers are valid for the duration of the call.
    unsafe { ffi::sysevents_poll(&awaited, &mut signalled, deadline.to_millis()) };
    SysEvents {
        read: HandleSet(signalled.read_ready),
        write: HandleSet(signalled.write_ready),
    }
}

/// Yields the current task until `timeout` expires, without waiting on any
/// device/IPC readiness.
pub fn yield_sleep(timeout: Timeout) {
    poll(SysEvents::empty(), timeout.to_deadline());
}

/// The [`SysHandle`] that signals readiness of `remote`'s IPC channel.
#[cfg(feature = "ipc")]
pub fn ipc_handle(remote: TaskId) -> SysHandle {
    ffi::syshandle_t_SYSHANDLE_IPC0 as SysHandle + remote.into_index() as SysHandle
}
