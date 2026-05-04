use crate::time::{Duration, Instant};

use trezor_thp::{channel::retransmit_after_ms, control_byte::ControlByte};

const MAX_LATENCY_MS: Duration = Duration::from_millis(800);

/// Timing data for THP channel.
pub struct ChannelTiming {
    /// Timestamp of last written packet (or last retransmission request), used
    /// for:
    /// - computing when to retransmit,
    /// - updating `ack_latency`,
    /// - deciding whether channel is stale and should be preempted.
    last_write: Instant,
    /// Duration between last packet send and ACK received.
    ack_latency: Duration,
    /// Logical monotonic timestamp, greater means more recent. Used to
    /// determine which channel to evict when new one is opened and the array is
    /// full.
    last_usage: u32,
}

impl ChannelTiming {
    pub fn new(now: Instant) -> Self {
        Self {
            last_write: now,
            ack_latency: Duration::ZERO,
            last_usage: 0,
        }
    }

    /// Update last write timestamp. Ignore ACK messages and allocation
    /// responses
    pub fn update_last_write(&mut self, now: Instant, packet: Option<&[u8]>) {
        // Ignore ACK messages and channel allocation responses.
        if packet
            .and_then(|p| ControlByte::try_from(p[0]).ok())
            .is_some_and(|cb| cb.is_ack() || cb.is_channel_allocation_response())
        {
            return;
        }
        self.last_write = now;
    }

    /// Update `ack_latency` when valid ACK is received.
    pub fn read_ack(&mut self, now: Instant) {
        let new_ack_latency = now.saturating_duration_since(self.last_write);
        self.ack_latency = new_ack_latency.min(MAX_LATENCY_MS);
    }

    fn timeout_ms(&self, attempt: u8) -> Duration {
        let variable_delay = Duration::from_millis(retransmit_after_ms(attempt));
        self.ack_latency
            .checked_add(variable_delay)
            .unwrap_or(variable_delay)
    }

    /// Returns time remaining before n-th retransmission should be requested.
    pub fn timeout_from_now(&self, now: Instant, attempt: u8) -> Duration {
        let Some(since_last_write) = now.checked_duration_since(self.last_write) else {
            return Duration::ZERO; // timeout now if wrapped around
        };
        match self.timeout_ms(attempt).checked_sub(since_last_write) {
            None => Duration::ZERO, // we're past the timeout
            Some(duration) => duration,
        }
    }

    /// Returns time since last write, or None on overflow.
    pub fn last_write_age(&self, now: Instant) -> Option<Duration> {
        now.checked_duration_since(self.last_write)
    }

    /// Returns last usage value.
    pub fn last_usage(&self) -> u32 {
        self.last_usage
    }

    /// Update last usage timestamp to current value of a monotonic counter.
    pub fn update_last_usage(&mut self, counter: u32) {
        self.last_usage = counter;
    }
}
