struct SingleThreadedCriticalSection;

/// # Safety
///
/// The app lives in a single threaded environment.
unsafe impl critical_section::Impl for SingleThreadedCriticalSection {
    unsafe fn acquire() -> () {}
    unsafe fn release(_token: ()) {}
}

critical_section::set_impl!(SingleThreadedCriticalSection);
