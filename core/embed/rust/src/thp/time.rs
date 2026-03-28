use crate::time::{Duration, Instant};

use trezor_thp::channel::retransmit_after_ms;

const MAX_LATENCY_MS: Duration = Duration::from_millis(800);

pub struct ChannelTiming {
    // for computing ack_latency and deciding whether channel preemption should happen
    last_write: Instant,
    ack_latency: Duration,
    // for replacing old channels with new channels
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

    pub fn update_last_write(&mut self, now: Instant, packet: Option<&[u8]>) {
        // Ignore ACKs and broadcast channel.
        if let Some(packet) = packet {
            if packet.len() < 3 || packet[0] & 0xF7 == 0x20 || packet[1..3] == [0xFF, 0xFF] {
                return;
            }
        }
        self.last_write = now;
    }

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

    pub fn timeout_from_now(&self, now: Instant, attempt: u8) -> Duration {
        let Some(since_last_write) = now.checked_duration_since(self.last_write) else {
            return Duration::ZERO; // timeout now if wrapped around
        };
        match self.timeout_ms(attempt).checked_sub(since_last_write) {
            None => Duration::ZERO, // we're past the timeout
            Some(duration) => duration,
        }
    }

    pub fn last_write_age(&self, now: Instant) -> Option<u32> {
        now.checked_duration_since(self.last_write)
            .map(|dur| dur.to_millis())
    }

    pub fn last_usage(&self) -> u32 {
        self.last_usage
    }

    pub fn update_last_usage(&mut self, counter: u32) {
        self.last_usage = counter;
    }
}
