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
    val: T,
    /// Index of previous (more recently used) entry in the linked-list.
    prev: u8,
    /// Index of next (less recently used) entry in the linked-list.
    next: u8,
}

impl<T, const N: usize> Default for LruCache<T, N> {
    fn default() -> Self {
        Self::new()
    }
}

impl<T, const N: usize> LruCache<T, N> {
    /// Create a new, empty, LRU cache.
    pub const fn new() -> Self {
        debug_assert!(N < u8::MAX as usize, "Capacity overflow");

        Self {
            entries: Vec::new(),
            head: 0,
            tail: 0,
        }
    }

    pub fn insert(&mut self, val: T) -> Option<T> {
        let entry = Entry {
            val,
            prev: 0,
            next: 0,
        };
        if self.is_full() {
            let tail = self.pop_tail();
            let prev = mem::replace(&mut self.entries[tail as usize], entry);
            self.push_head(tail);
            Some(prev.val)
        } else {
            let _ = self.entries.push(entry);
            self.push_head((self.len() - 1) as u8);
            None
        }
    }

    pub fn find(&mut self, mut pred: impl FnMut(&T) -> bool) -> Option<&mut T> {
        for (i, entry) in self.entries.iter().enumerate() {
            if pred(&entry.val) {
                self.touch_index(i as u8);
                return self.front_mut();
            }
        }
        None
    }

    pub fn front(&self) -> Option<&T> {
        self.entries.get(self.head as usize).map(|e| &e.val)
    }

    pub fn front_mut(&mut self) -> Option<&mut T> {
        self.entries.get_mut(self.head as usize).map(|e| &mut e.val)
    }

    pub fn len(&self) -> usize {
        self.entries.len()
    }

    pub fn is_empty(&self) -> bool {
        self.entries.is_empty()
    }

    pub fn is_full(&self) -> bool {
        self.entries.is_full()
    }

    fn touch_index(&mut self, i: u8) {
        if i != self.head {
            self.remove(i);
            self.push_head(i);
        }
    }

    fn remove(&mut self, i: u8) {
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
        if self.entries.len() == 1 {
            self.tail = i;
        } else {
            self.entries[i as usize].next = self.head;
            self.entries[self.head as usize].prev = i;
        }
        self.head = i;
    }

    fn pop_tail(&mut self) -> u8 {
        let old_tail = self.tail;
        let new_tail = self.entries[old_tail as usize].prev;
        self.tail = new_tail;
        old_tail
    }
}
