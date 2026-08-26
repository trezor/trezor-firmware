//! Safe wrapper around the kernel's event-readiness API
//! (`sys/task/inc/sys/sysevent.h`), used to block a task until one of a set
//! of device/IPC handles becomes ready, or a deadline passes.

pub use ffi::syshandle_t as SysHandle;

use crate::ffi;

/// A bitmask of [`SysHandle`]s.
#[derive(Copy, Clone, PartialEq, Eq, Default)]
pub struct HandleSet(u32);

impl HandleSet {
    pub const fn empty() -> Self {
        Self(0)
    }

    pub fn new(handles: &[SysHandle]) -> Self {
        let mut set = Self::empty();
        for &handle in handles {
            set = set.with(handle);
        }
        set
    }

    pub fn with(self, handle: SysHandle) -> Self {
        Self(self.0 | 1 << (handle as u32))
    }

    pub fn contains(self, handle: SysHandle) -> bool {
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
/// `deadline` (an absolute [`crate::time`] tick count) passes.
///
/// Returns the events that were actually signalled — empty if the deadline
/// expired first.
pub fn poll(awaited: SysEvents, deadline: u32) -> SysEvents {
    let awaited = ffi::sysevents_t {
        read_ready: awaited.read.0,
        write_ready: awaited.write.0,
    };
    let mut signalled = ffi::sysevents_t {
        read_ready: 0,
        write_ready: 0,
    };
    // SAFETY: both pointers are valid for the duration of the call.
    unsafe { ffi::sysevents_poll(&awaited, &mut signalled, deadline) };
    SysEvents {
        read: HandleSet(signalled.read_ready),
        write: HandleSet(signalled.write_ready),
    }
}

/// Blocks until `deadline` (an absolute [`crate::time`] tick count) passes,
/// without waiting on any device/IPC readiness.
pub fn sleep_until(deadline: u32) {
    poll(SysEvents::empty(), deadline);
}

/// The [`SysHandle`] that signals readiness of `remote`'s IPC channel.
#[cfg(feature = "ipc")]
pub fn ipc_handle(remote: u8) -> SysHandle {
    ffi::syshandle_t_SYSHANDLE_IPC0 + remote as u32
}
