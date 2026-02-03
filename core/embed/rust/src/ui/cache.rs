use crate::{micropython::buffer::StrBuffer, strutil::TString};

/// A node in the linked list cache
struct CacheNode<const T: usize> {
    valid: bool,
    content: [u8; T],
    content_len: usize,
    prev: Option<usize>,
    next: Option<usize>,
}

impl<const T: usize> CacheNode<T> {
    const fn empty() -> Self {
        Self {
            valid: false,
            // Utf8 characters might have bigger size, allocate double space
            content: [0; T],
            content_len: 0,
            prev: None,
            next: None,
        }
    }

    fn is_empty(&self) -> bool {
        !self.valid
    }

    fn clear(&mut self) {
        self.valid = false;
        self.content_len = 0;
        self.clear_next();
        self.clear_prev();
    }

    fn set_content(&mut self, data: &[u8]) {
        self.valid = true;
        let len = data.len();
        debug_assert!(len <= T);
        self.content[..len].copy_from_slice(&data);
        self.content_len = len;
    }

    fn set_next(&mut self, next: Option<usize>) {
        self.next = next;
    }

    fn clear_next(&mut self) {
        self.next = None;
    }

    fn set_prev(&mut self, prev: Option<usize>) {
        self.prev = prev;
    }

    fn clear_prev(&mut self) {
        self.prev = None;
    }

    fn has_prev(&self) -> bool {
        self.prev.is_some()
    }

    fn has_next(&self) -> bool {
        self.next.is_some()
    }
}

/// LRU-style linked list cache with N slots.
///
/// head <-> ... <-> tail
/// - Adding next: add after head, evict tail if full
/// - Adding prev: add before tail, evict head if full
pub struct Cache<const T: usize, const N: usize> {
    nodes: [CacheNode<T>; N],
    head: Option<usize>, // newest towards next direction
    tail: Option<usize>, // newest towards prev direction
    current: Option<usize>,
    len: usize,
}

impl<const T: usize, const N: usize> Cache<T, N> {
    const EMPTY_NODE: CacheNode<T> = CacheNode::empty();

    pub const fn new() -> Self {
        Self {
            nodes: [Self::EMPTY_NODE; N],
            head: None,
            tail: None,
            current: None,
            len: 0,
        }
    }

    pub fn initialized(&self) -> bool {
        self.current.is_some()
    }
    pub fn init(&mut self, data: &[u8]) {
        debug_assert!(self.len == 0);

        let current = 0;
        self.nodes[current].set_content(data);
        self.insert_at_head(current);
        self.len = 1;
        self.current = Some(current);
    }

    /// Find a free node slot
    fn find_free_slot(&self) -> Option<usize> {
        if self.len >= N {
            return None;
        }
        self.nodes.iter().position(|n| n.is_empty())
    }

    /// Insert node at head (next direction)
    fn insert_at_head(&mut self, idx: usize) {
        self.nodes[idx].clear_next();
        self.nodes[idx].set_prev(self.head);

        if let Some(h) = self.head {
            self.nodes[h].set_next(Some(idx));
        }
        self.head = Some(idx);

        if self.tail.is_none() {
            self.tail = Some(idx);
        }
    }

    /// Insert node at tail (prev direction)
    fn insert_at_tail(&mut self, idx: usize) {
        self.nodes[idx].clear_prev();
        self.nodes[idx].set_next(self.tail);

        if let Some(t) = self.tail {
            self.nodes[t].set_prev(Some(idx));
        }
        self.tail = Some(idx);

        if self.head.is_none() {
            self.head = Some(idx);
        }
    }

    /// Evict tail node and return its index
    fn evict_tail(&mut self) -> usize {
        debug_assert!(self.len >= 1);
        debug_assert!(self.tail.is_some());

        let idx = unwrap!(self.tail);
        debug_assert!(!self.nodes[idx].has_prev());
        debug_assert!(self.nodes[idx].has_next());

        let next_idx = unwrap!(self.nodes[idx].next);
        self.nodes[next_idx].clear_prev();
        self.tail = Some(next_idx);

        self.nodes[idx].clear();

        self.len -= 1;
        idx
    }

    /// Evict head node and return its index
    fn evict_head(&mut self) -> usize {
        debug_assert!(self.len >= 1);
        debug_assert!(self.head.is_some());

        let idx = unwrap!(self.head);
        debug_assert!(self.nodes[idx].has_prev());
        debug_assert!(!self.nodes[idx].has_next());

        let prev_idx = unwrap!(self.nodes[idx].prev);
        self.nodes[prev_idx].clear_next();
        self.head = Some(prev_idx);

        self.nodes[idx].clear();
        self.len -= 1;
        idx
    }

    /// Get a slot for a new node, evicting from specified end if needed
    fn get_slot_evict_tail(&mut self) -> usize {
        debug_assert!(self.len >= 1);

        if let Some(idx) = self.find_free_slot() {
            idx
        } else {
            self.evict_tail()
        }
    }

    fn get_slot_evict_head(&mut self) -> usize {
        debug_assert!(self.len >= 1);

        if let Some(idx) = self.find_free_slot() {
            idx
        } else {
            self.evict_head()
        }
    }

    /// Add next page data (adds at head, evicts from tail if full)
    pub fn push_head(&mut self, data: &[u8]) {
        debug_assert!(self.current == self.head);

        let idx = self.get_slot_evict_tail();
        self.nodes[idx].set_content(data);
        self.insert_at_head(idx);
        self.len += 1;
    }

    /// Add prev page data (adds at tail, evicts from head if full)
    pub fn push_tail(&mut self, data: &[u8]) {
        // debug_assert!(self.has_prev() && matches!(self.state,
        // CacheState::Waiting(_)));
        debug_assert!(self.current == self.tail);
        let idx = self.get_slot_evict_head();
        self.nodes[idx].set_content(data);
        self.insert_at_tail(idx);
        self.len += 1;
    }

    pub fn go_next(&mut self) {
        debug_assert!(self.current.is_some());
        debug_assert!(self.nodes[unwrap!(self.current)].has_next());

        self.current = self.nodes[unwrap!(self.current)].next;
    }

    pub fn go_prev(&mut self) {
        debug_assert!(self.current.is_some());
        debug_assert!(self.nodes[unwrap!(self.current)].has_prev());

        self.current = self.nodes[unwrap!(self.current)].prev;
    }

    pub fn is_at_head(&self) -> bool {
        debug_assert!(self.current.is_some());
        self.current == self.head
    }

    pub fn is_at_tail(&self) -> bool {
        debug_assert!(self.current.is_some());
        self.current == self.tail
    }

    pub fn current_data(&self) -> Option<TString<'static>> {
        if let Some(current) = self.current {
            unsafe {
                return Some(
                    StrBuffer::from_ptr_and_len(
                        self.nodes[current].content.as_ptr(),
                        self.nodes[current].content_len,
                    )
                    .into(),
                );
            }
        } else {
            None
        }
    }
}

/// Type alias for the default cache configuration
pub type PageCache = Cache<360, 3>;
