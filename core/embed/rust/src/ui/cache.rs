use crate::{
    debug,
    micropython::buffer::StrBuffer,
    strutil::TString,
    ui::{cache, component::text::op::Op},
};

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
            content: [0; T],
            content_len: 0,
            prev: None,
            next: None,
        }
    }

    fn is_empty(&self) -> bool {
        self.valid == false
    }

    // fn clear(&mut self) {
    //     self.valid = false;
    //     self.content = [0; T];
    //     self.content_len = 0;
    // }
}

#[derive(Clone, Copy, PartialEq, Eq)]
pub enum CacheState {
    Uninit,
    Waiting(usize),
    Ready,
}

/// LRU-style linked list cache with N slots.
///
/// Uses a doubly-linked list to track usage order.
/// Head is most recently used, tail is least recently used.
pub struct Cache<const T: usize, const N: usize> {
    state: CacheState,
    nodes: [CacheNode<T>; N],
    head: Option<usize>,
    tail: Option<usize>,
    current_node: usize,
    current_page: u16,
    total_pages: u16,
    cap: usize,
}

impl<const T: usize, const N: usize> Cache<T, N> {
    const EMPTY_NODE: CacheNode<T> = CacheNode::empty();

    pub const fn new(total_pages: u16) -> Self {
        Self {
            state: CacheState::Uninit,
            nodes: [Self::EMPTY_NODE; N],
            head: None,
            tail: None,
            current_node: 0,
            total_pages,
            current_page: 0,
            cap: 0,
        }
    }

    pub fn init(&mut self, data: &[u8]) {
        debug_assert!(self.state == CacheState::Uninit);
        self.state = CacheState::Ready;

        self.current_node = 0;
        self.nodes[0].valid = true;
        self.nodes[0].content[..data.len()].copy_from_slice(data);
        self.nodes[0].content_len = data.len();
        self.nodes[0].prev = None;
        self.nodes[0].next = None;
        self.head = Some(0);
        self.tail = Some(0);
        self.cap = 1;
    }

    pub fn has_next(&self) -> bool {
        self.current_page + 1 < self.total_pages
    }

    pub fn has_prev(&self) -> bool {
        self.current_page > 0
    }

    pub fn total_pages(&self) -> u16 {
        self.total_pages
    }

    pub fn current_page(&self) -> u16 {
        self.current_page
    }

    pub fn find_free_node(&mut self) -> Option<usize> {
        if self.cap >= N {
            return None;
        }
        for (idx, node) in self.nodes.iter_mut().enumerate() {
            if node.is_empty() {
                return Some(idx);
            }
        }
        None
    }

    pub fn set_next(&mut self, data: &[u8]) {
        debug_assert!(self.has_next() && matches!(self.state, CacheState::Waiting(_)));

        if self.cap < N {
            self.cap += 1;

            let new_head_idx = self.find_free_node().unwrap();
            let old_head_node = &mut self.nodes[self.head.unwrap()];
            old_head_node.next = Some(new_head_idx);
            let new_head_node = &mut self.nodes[new_head_idx];
            new_head_node.valid = true;
            new_head_node.content[..data.len()].copy_from_slice(data);
            new_head_node.content_len = data.len();
            new_head_node.prev = Some(self.current_node);
            new_head_node.next = None;

            self.head = Some(new_head_idx);
        } else {
            let old_tail_idx = self.tail.unwrap();
            let old_tail_node = &mut self.nodes[old_tail_idx];

            let new_tail_idx = old_tail_node.next.unwrap();
            let new_tail_node = &mut self.nodes[new_tail_idx];
            self.tail = Some(new_tail_idx);

            let new_head_idx = old_tail_idx;
            let old_head = &mut self.nodes[self.head.unwrap()];
            old_head.next = Some(new_head_idx);
            self.head = Some(new_head_idx);
            let new_head_node = &mut self.nodes[new_head_idx];
            new_head_node.valid = true;
            new_head_node.content[..data.len()].copy_from_slice(data);
            new_head_node.content_len = data.len();
            new_head_node.prev = Some(self.current_node);
            new_head_node.next = None;
        }

        self.state = CacheState::Ready;
    }

    pub fn set_prev(&mut self, data: &[u8]) {
        debug_assert!(self.has_prev() && matches!(self.state, CacheState::Waiting(_)));

        if self.cap < N {
            self.cap += 1;

            let new_tail_idx = self.find_free_node().unwrap();

            let old_tail_node = &mut self.nodes[self.tail.unwrap()];
            old_tail_node.prev = Some(new_tail_idx);

            let new_tail_node = &mut self.nodes[new_tail_idx];

            new_tail_node.valid = true;
            new_tail_node.content[..data.len()].copy_from_slice(data);
            new_tail_node.content_len = data.len();
            new_tail_node.prev = None;
            new_tail_node.next = Some(self.current_node);

            self.tail = Some(new_tail_idx);
        } else {
            let old_head_idx = self.head.unwrap();
            let old_head_node = &mut self.nodes[old_head_idx];

            let new_head_idx = old_head_node.prev.unwrap();
            let new_head_node = &mut self.nodes[new_head_idx];
            self.head = Some(new_head_idx);

            let new_tail_idx = old_head_idx;
            let old_tail = &mut self.nodes[self.tail.unwrap()];
            old_tail.prev = Some(new_tail_idx);
            self.tail = Some(new_tail_idx);
            let new_tail_node = &mut self.nodes[new_tail_idx];
            new_tail_node.valid = true;
            new_tail_node.content[..data.len()].copy_from_slice(data);
            new_tail_node.content_len = data.len();
            new_tail_node.prev = None;
            new_tail_node.next = Some(self.current_node);
        }

        self.state = CacheState::Ready;
    }

    pub fn set_state(&mut self, state: CacheState) {
        self.state = state;
    }

    pub fn switch_next(&mut self) -> CacheState {
        debug_assert!(self.has_next() && self.state == CacheState::Ready);
        let old_current_node = &self.nodes[self.current_node];
        debug_assert!(old_current_node.next.is_some());
        self.current_node = old_current_node.next.unwrap();
        self.current_page += 1;

        if self.has_next() {
            self.state = CacheState::Waiting(self.current_page as usize + 1);
        }
        self.state
    }

    pub fn switch_prev(&mut self) -> CacheState {
        debug_assert!(self.has_prev() && self.state == CacheState::Ready);
        let old_current_node = &self.nodes[self.current_node];
        debug_assert!(old_current_node.prev.is_some());
        self.current_node = old_current_node.prev.unwrap();
        self.current_page -= 1;

        if self.has_prev() {
            self.state = CacheState::Waiting(self.current_page as usize - 1);
        }
        self.state
    }

    pub fn current_page_data(&self) -> TString<'static> {
        if self.state == CacheState::Uninit {
            return TString::empty();
        }

        debug_assert!(self.state != CacheState::Uninit);
        let node: &CacheNode<T> = &self.nodes[self.current_node];
        debug_assert!(node.valid);

        unsafe { StrBuffer::from_ptr_and_len(node.content.as_ptr(), node.content_len as usize) }
            .into()
    }

    pub fn state(&self) -> CacheState {
        self.state
    }
}

/// Type alias for the default cache configuration
pub type PageCache = Cache<20, 3>;
