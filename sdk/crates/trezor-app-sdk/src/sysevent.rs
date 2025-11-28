use ufmt::derive::uDebug;

use crate::ipc::RemoteSysTask;
use crate::low_level_api::{self, ffi};
use crate::util::Timeout;

trait HasSysHandle: Copy {
    fn syshandle(self) -> ffi::syshandle_t;
}

impl HasSysHandle for RemoteSysTask {
    fn syshandle(self) -> ffi::syshandle_t {
        let remote_id: u8 = self.into();
        ffi::SYSHANDLE_IPC0 + remote_id as u32
    }
}

#[derive(uDebug, Copy, Clone, PartialEq, Eq)]
pub struct HandleSet(u32);

impl HandleSet {
    pub const fn empty() -> Self {
        Self(0)
    }

    pub fn new(handles: &[impl HasSysHandle]) -> Self {
        let mut set = Self::empty();
        for handle in handles {
            set = set.with(*handle);
        }
        set
    }

    pub fn with(self, handle: impl HasSysHandle) -> Self {
        Self(self.0 | 1 << handle.syshandle())
    }

    pub fn contains(self, handle: impl HasSysHandle) -> bool {
        self.0 & (1 << handle.syshandle()) != 0
    }
}

#[derive(uDebug, Copy, Clone, PartialEq, Eq)]
pub struct SysEvents {
    pub read: HandleSet,
    pub write: HandleSet,
}

impl SysEvents {
    pub fn empty() -> Self {
        Self {
            read: HandleSet::empty(),
            write: HandleSet::empty(),
        }
    }

    pub fn new_with_read(handles: &[impl HasSysHandle]) -> Self {
        Self::empty().with_read(handles)
    }

    pub fn new_with_write(handles: &[impl HasSysHandle]) -> Self {
        Self::empty().with_write(handles)
    }

    pub fn with_read(self, handles: &[impl HasSysHandle]) -> Self {
        Self {
            read: HandleSet::new(handles),
            write: self.write,
        }
    }

    pub fn with_write(self, handles: &[impl HasSysHandle]) -> Self {
        Self {
            read: self.read,
            write: HandleSet::new(handles),
        }
    }

    pub fn read_ready(&self, handle: impl HasSysHandle) -> bool {
        self.read.contains(handle)
    }

    pub fn write_ready(&self, handle: impl HasSysHandle) -> bool {
        self.write.contains(handle)
    }

    pub fn poll(self, timeout: Timeout) -> Self {
        let awaited = ffi::sysevents_t {
            read_ready: self.read.0,
            write_ready: self.write.0,
        };
        let mut signalled = ffi::sysevents_t::default();
        low_level_api::sysevents_poll(&awaited, &mut signalled, timeout.as_deadline());
        Self {
            read: HandleSet(awaited.read_ready),
            write: HandleSet(awaited.write_ready),
        }
    }
}
