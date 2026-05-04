use crate::time::{Duration, Instant};

use trezor_thp::channel::retransmit_after_ms;

const MAX_LATENCY_MS: Duration = Duration::from_millis(800);

/// Timing data for THP channel.
#[cfg_attr(test, derive(Debug))]
pub struct ChannelTiming {
    /// Timestamp of last sent message (only first attempt), used for:
    /// - computing when to retransmit,
    /// - updating `ack_latency`,
    /// - deciding whether channel is stale and should be preempted.
    last_write: Instant,
    /// Duration between last message sent and ACK received.
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

    /// Update last write timestamp. Called before first attempt of each
    /// outgoing message.
    pub fn update_last_write(&mut self, now: Instant) {
        self.last_write = now;
    }

    /// Update `ack_latency` when valid ACK is received.
    pub fn read_ack(&mut self, now: Instant) {
        let new_ack_latency = now.saturating_duration_since(self.last_write);
        self.ack_latency = new_ack_latency.min(MAX_LATENCY_MS);
    }

    /// How long to wait for n-th retry after outgoing message is submitted.
    fn timeout_ms(&self, attempt: u8) -> Duration {
        // Total duration since writing a message is the sum of the durations between
        // retries. Each duration between retries is variable delay plus ACK latency.
        (0..=attempt)
            .map(retransmit_after_ms)
            .map(Duration::from_millis)
            .fold(Duration::ZERO, |acc, variable_delay| {
                acc.saturating_add(variable_delay)
                    .saturating_add(self.ack_latency)
            })
    }

    /// Returns time remaining before n-th retransmission should be requested.
    pub fn timeout_from_now(&self, now: Instant, attempt: u8) -> Duration {
        let Some(since_last_write) = self.last_write_age(now) else {
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

/// Returns ID of the least recently used channel in the `channels` iterator.
pub fn least_recently_used(
    channels: &mut dyn Iterator<Item = (u16, &ChannelTiming)>,
) -> Option<u16> {
    let mut oldest = None;
    for (idx, timing) in channels {
        let last_used = timing.last_usage();
        match oldest {
            None => {
                oldest = Some((idx, last_used));
            }
            Some((_oldest_idx, oldest_val)) if last_used < oldest_val => {
                oldest = Some((idx, last_used));
            }
            _ => {}
        }
    }
    oldest.map(|(idx, _)| idx)
}

#[cfg(test)]
mod tests {
    use super::*;
    use heapless::Vec;
    use trezor_thp::channel::MAX_RETRANSMISSION_COUNT;

    fn make_map(channels: &[(u16, u32)]) -> Vec<(u16, ChannelTiming), 16> {
        let mut chans = Vec::new();
        for (ch, last_used) in channels {
            let mut t = ChannelTiming::new(Instant::now());
            t.update_last_usage(*last_used);
            chans.push((*ch, t)).unwrap();
        }
        chans
    }

    fn it(chans: &[(u16, ChannelTiming)]) -> impl Iterator<Item = (u16, &ChannelTiming)> {
        chans.iter().map(|(cid, timing)| (*cid, timing))
    }

    #[test]
    fn test_lru_no_channels() {
        assert_eq!(least_recently_used(&mut it(&[])), None);
    }

    #[test]
    fn test_lru_simple() {
        let chans = make_map(&[(7, 7)]);
        assert_eq!(least_recently_used(&mut it(&chans)), Some(7));

        let chans = make_map(&[(1, 2), (3, 4), (5, 1)]);
        assert_eq!(least_recently_used(&mut it(&chans)), Some(5));

        let chans = make_map(&[(5, 100), (3, 400), (1, 200), (6, 50), (8, 600)]);
        assert_eq!(least_recently_used(&mut it(&chans)), Some(6));
    }

    #[test]
    fn test_timeout_ms_monotonic() {
        let now = Instant::now();
        let high_latency = MAX_LATENCY_MS.checked_add(MAX_LATENCY_MS).unwrap();
        let mut timing = ChannelTiming::new(now);
        assert_eq!(timing.ack_latency, Duration::ZERO);

        for i in 0..(2 * MAX_RETRANSMISSION_COUNT) {
            assert!(timing.timeout_ms(i) < timing.timeout_ms(i + 1));
        }

        timing.update_last_write(now);
        timing.read_ack(now.checked_add(high_latency).unwrap());
        assert_eq!(timing.ack_latency, MAX_LATENCY_MS);

        for i in 0..(2 * MAX_RETRANSMISSION_COUNT) {
            assert!(timing.timeout_ms(i) < timing.timeout_ms(i + 1));
        }
    }

    #[test]
    fn test_timeout_ms_limits() {
        let now = Instant::now();
        let high_latency = MAX_LATENCY_MS.checked_add(MAX_LATENCY_MS).unwrap();
        let mut timing = ChannelTiming::new(now);
        assert_eq!(timing.ack_latency, Duration::ZERO);

        // at least 200ms before first retry
        assert_eq!(timing.timeout_ms(0).to_millis(), 200);
        assert_eq!(timing.timeout_ms(1).to_millis(), 500);
        assert_eq!(
            timing.timeout_ms(MAX_RETRANSMISSION_COUNT - 1).to_secs(),
            103
        );

        timing.update_last_write(now);
        timing.read_ack(now.checked_add(high_latency).unwrap());
        assert_eq!(timing.ack_latency, MAX_LATENCY_MS);

        assert_eq!(timing.timeout_ms(0).to_millis(), 1000);
        assert_eq!(timing.timeout_ms(1).to_millis(), 2100);
        assert_eq!(
            timing.timeout_ms(MAX_RETRANSMISSION_COUNT - 1).to_secs(),
            143
        );
        // at most 2m23s until reaching the limit
    }
}
