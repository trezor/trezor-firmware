use sys::time::{Duration, Instant};

/// A stopwatch is a utility designed for measuring the amount of time
/// that elapses between its start and stop points. It can be used in various
/// situations - animation timing, event timing, testing and debugging.
#[derive(Clone)]
pub enum Stopwatch {
    Stopped(Duration),
    Running(Instant),
}

impl Default for Stopwatch {
    /// Returns a new stopped stopwatch by default.
    fn default() -> Self {
        Self::new_stopped()
    }
}

impl Stopwatch {
    /// Creates a new stopped stopwatch with duration of zero
    pub fn new_stopped() -> Self {
        Self::Stopped(Duration::ZERO)
    }

    /// Creates a new started stopwatch that starts
    /// at the current instant.
    pub fn new_started() -> Self {
        Self::Running(Instant::now())
    }

    /// Starts or restarts the stopwatch.
    ///
    /// If the stopwatch is already running, it restarts, setting
    /// the elapsed time to zero.
    pub fn start(&mut self) {
        *self = Self::Running(Instant::now());
    }

    /// Stops the stopwatch.
    ///
    /// When stopped, the `elapsed()` method will return the total
    /// duration for which the stopwatch was running.
    pub fn stop(&mut self) {
        *self = Self::Stopped(self.elapsed());
    }

    /// Returns the elapsed duration since the stopwatch was last started.
    ///
    /// If the stopwatch is running, it calculates the time from the last
    /// start instant to the current instant.
    pub fn elapsed(&self) -> Duration {
        match *self {
            Self::Stopped(duration) => duration,
            Self::Running(time) => unwrap!(Instant::now().checked_duration_since(time)),
        }
    }

    /// Returns `true` if the stopwatch is currently running.
    pub fn is_running(&self) -> bool {
        matches!(*self, Self::Running(_))
    }

    /// Checks if the stopwatch is running and whether the elapsed
    /// time since the last start is less than or equal to a specified limit.
    pub fn is_running_within(&self, limit: Duration) -> bool {
        match *self {
            Self::Stopped(_) => false,
            Self::Running(_) => self.elapsed() <= limit,
        }
    }
}

#[cfg(test)]
mod tests {
    use sys::time::{Duration, Instant};

    use super::*;

    #[test]
    fn stopwatch_builds_correctly() {
        let sw = Stopwatch::new_started();
        assert!(sw.is_running());

        let sw = Stopwatch::new_stopped();
        assert!(!sw.is_running());

        let sw: Stopwatch = Default::default();
        assert!(!sw.is_running());
    }

    fn wait(duration: Duration) {
        let origin = Instant::now();
        while Instant::now().checked_duration_since(origin).unwrap() < duration {}
    }

    #[test]
    fn stopwatch_starts_correcly() {
        let mut sw = Stopwatch::new_stopped();
        assert!(!sw.is_running());

        sw.start();
        assert!(sw.is_running());

        wait(Duration::from_millis(10));
        assert!(sw.elapsed() >= Duration::from_millis(10));
        assert!(!sw.is_running_within(Duration::from_millis(5)));
        assert!(sw.is_running_within(Duration::from_millis(10000)));
    }

    #[test]
    fn stopwatch_stops_correctly() {
        let mut sw = Stopwatch::new_started();
        assert!(sw.is_running());

        wait(Duration::from_millis(10));

        sw.stop();
        assert!(!sw.is_running());

        let elapsed = sw.elapsed();
        assert!(elapsed >= Duration::from_millis(10));

        wait(Duration::from_millis(10));
        assert!(sw.elapsed() == elapsed);
        assert!(!sw.is_running_within(Duration::from_millis(5)));
        assert!(!sw.is_running_within(Duration::from_millis(10000)));
    }
}
