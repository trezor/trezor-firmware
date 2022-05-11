//! Tiny last-recently-used (LRU) cache.
//!
//! Heavily inspired by [uluru](https://github.com/servo/uluru) crate, with
//! minor changes (using the `heapless` crate for the backing vector, and
//! `u8` index type).

use core::mem;
use heapless::Vec;

pub struct LruCache<T, const N: usize> {
    /// Values are stored together with indices of a doubly-linked list.
    entries: Vec<Entry<T>, N>,
    /// Points to the most-recently-used entry in `entries`.
    head: u8,
    /// Points to the least-recently-used entry in `entries`.
    tail: u8,
}

struct Entry<T> {
    val: Option<T>,
    /// Index of previous (more recently used) entry in the linked-list.
    prev: u8,
    /// Index of next (less recently used) entry in the linked-list.
    next: u8,
}

impl<T, const N: usize> LruCache<T, N> {
    pub const fn new() -> Self {
        debug_assert!(N < u8::MAX as usize, "Capacity overflow");
        Self {
            entries: Vec::new(),
            head: 0,
            tail: 0,
        }
    }

    /// Reset the cache to an empty state.
    pub fn reset(&mut self) {
        self.entries = (0..N)
            .map(|i| Entry {
                val: None,
                prev: (i - 1).max(0) as u8,
                next: (i + 1).min(N - 1) as u8,
            })
            .collect();
        self.head = 0;
        self.tail = (N - 1) as u8;
    }

    fn initialized(&self) -> bool {
        self.entries.len() == N
    }

    pub fn insert(&mut self, val: T) -> Option<T> {
        if !self.initialized() {
            self.reset();
        }

        let tail = self.tail;
        let entry = &mut self.entries[tail as usize];
        let prev_val = mem::replace(&mut entry.val, Some(val));
        self.push_head(tail);
        prev_val
    }

    pub fn find_first(&mut self, pred: &impl Fn(&T) -> bool) -> Option<&mut T> {
        for (i, entry) in self.entries.iter().enumerate() {
            if entry.val.as_ref().map_or(false, pred) {
                self.touch_index(i as u8);
                return self.front_mut();
            }
        }
        None
    }

    pub fn drop_first(&mut self, pred: &impl Fn(&T) -> bool) -> bool {
        for (i, entry) in self.entries.iter().enumerate() {
            if entry.val.as_ref().map_or(false, pred) {
                self.push_tail(i as u8);
                return true;
            }
        }
        false
    }

    pub fn front(&self) -> Option<&T> {
        if !self.initialized() {
            return None;
        }
        self.entries
            .get(self.head as usize)
            .and_then(|e| e.val.as_ref())
    }

    pub fn front_mut(&mut self) -> Option<&mut T> {
        if !self.initialized() {
            return None;
        }
        self.entries
            .get_mut(self.head as usize)
            .and_then(|e| e.val.as_mut())
    }

    // pub fn len(&self) -> usize {
    //     self.entries.iter().filter(|v| v.val.is_some()).count()
    // }

    // pub fn is_empty(&self) -> bool {
    //     self.len() == 0
    // }

    // pub fn is_full(&self) -> bool {
    //     self.len() >= N
    // }

    fn touch_index(&mut self, i: u8) {
        debug_assert!(self.initialized());
        if i != self.head {
            self.push_head(i);
        }
    }

    fn remove(&mut self, i: u8) {
        debug_assert!(self.initialized());
        let prev = self.entries[i as usize].prev;
        let next = self.entries[i as usize].next;
        if i == self.head {
            self.head = next;
        } else {
            self.entries[prev as usize].next = next;
        }
        if i == self.tail {
            self.tail = prev;
        } else {
            self.entries[next as usize].prev = prev;
        }
    }

    fn push_head(&mut self, i: u8) {
        debug_assert!(self.initialized());
        self.remove(i);
        self.entries[i as usize].next = self.head;
        self.entries[self.head as usize].prev = i;
        self.head = i;
    }

    fn push_tail(&mut self, i: u8) {
        debug_assert!(self.initialized());
        self.remove(i);
        self.entries[i as usize].prev = self.tail;
        self.entries[self.tail as usize].next = i;
        self.tail = i;
    }
}
