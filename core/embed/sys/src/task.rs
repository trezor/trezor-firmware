use crate::ffi;

/// Task identifier.
///
/// Newtype wrapper around `ffi::systask_id_t` for type safety of task
/// identifiers.
#[repr(transparent)]
#[derive(Debug, Copy, Clone, PartialEq, Eq, Hash)]
pub struct TaskId(ffi::systask_id_t);

impl TaskId {
    /// The maximum number of tasks supported by the system.
    pub const MAX: usize = ffi::SYSTASK_MAX_TASKS as usize;

    /// Converts the task identifier to a zero-based index.
    pub const fn into_index(self) -> usize {
        self.0 as usize
    }
}

impl From<ffi::systask_id_t> for TaskId {
    fn from(id: ffi::systask_id_t) -> Self {
        TaskId(id)
    }
}

impl From<TaskId> for ffi::systask_id_t {
    fn from(id: TaskId) -> Self {
        id.0
    }
}
