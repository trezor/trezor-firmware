/// A single-threaded mutex lock.
///
/// This is a simple newtype over spin::Mutex that replaces the spinning
/// behavior with a panic. We are in a single-threaded environment, so if a lock
/// is not available, there is no amount of spinning you can do to make it
/// available.
pub struct Lock<T>(spin::Mutex<T>);

impl<T> Lock<T> {
    /// Creates a new Lock instance with the given inner value.
    pub const fn new(value: T) -> Self {
        Self(spin::Mutex::new(value))
    }

    /// Locks the mutex and returns a guard.
    ///
    /// If the lock is already held, this function will panic.
    pub fn lock(&self) -> spin::MutexGuard<T> {
        unwrap!(self.0.try_lock())
    }

    /// Tries to lock the mutex.
    ///
    /// If the lock is already held, this function will return None.
    pub fn try_lock(&self) -> Option<spin::MutexGuard<T>> {
        self.0.try_lock()
    }

    /// Unlocks the mutex unconditionally.
    ///
    /// # Safety
    ///
    /// This **will break things** if someone else intends to use the locked
    /// object afterwards. Use only when you know that nobody will do so --
    /// e.g., when the whole firmware is going to halt.
    pub unsafe fn force_unlock(&self) {
        unsafe { self.0.force_unlock() }
    }
}

//unsafe impl<T> Sync for Lock<T> {}
