use crate::{
    debug,
    ipc::{IpcMessage, RemoteSysTask},
    micropython::buffer::StrBuffer,
    strutil::TString,
    ui::component::{base::AttachType, Event, EventCtx},
};
use core::mem::MaybeUninit;
use rkyv::{
    api::low::to_bytes_in_with_alloc,
    rancor::Failure,
    ser::{allocator::SubAllocator, writer::Buffer},
    util::Align,
};
use trezor_structs::UtilEnum;

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

#[derive(Clone, Copy, PartialEq, Eq)]
pub enum CacheState {
    Uninit,
    Waiting(usize),
    Ready,
}

/// LRU-style linked list cache with N slots.
///
/// head <-> ... <-> tail
/// - Adding next: add after head, evict tail if full
/// - Adding prev: add before tail, evict head if full
pub struct Cache<const A: usize, const T: usize, const N: usize> {
    state: CacheState,
    nodes: [CacheNode<T>; N],
    head: Option<usize>, // newest towards next direction
    tail: Option<usize>, // newest towards prev direction
    current_node: usize,
    current_page: u16,
    total_pages: u16,
    len: usize,
}

impl<const A: usize, const T: usize, const N: usize> Cache<A, T, N> {
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
            len: 0,
        }
    }

    pub fn event(&mut self, ctx: &mut EventCtx, event: Event) {
        if matches!(event, Event::Attach(AttachType::Initial)) {
            // debug_assert!(self.cache.state == CacheState::Empty);
            // Load content into cache if needed
            self.request_page(ctx, 0);
        }

        if let Event::Timer(EventCtx::ANIM_FRAME_TIMER) = event {
            if let Some(data) = IpcMessage::try_receive(RemoteSysTask::Unknown(2)) {
                self.update(&data.data(), ctx);
            } else {
                ctx.request_anim_frame();
            }
        }
    }

    pub fn init(&mut self, data: &[u8]) {
        debug_assert!(self.state == CacheState::Uninit);

        self.current_node = 0;
        self.nodes[self.current_node].set_content(data);
        self.insert_at_head(self.current_node);
        self.len = 1;
        self.state = CacheState::Ready;
    }

    pub fn has_next(&self) -> bool {
        self.current_page + 1 < self.total_pages
    }

    pub fn has_prev(&self) -> bool {
        self.current_page > 0
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
        if let Some(idx) = self.find_free_slot() {
            idx
        } else {
            self.evict_tail()
        }
    }

    fn get_slot_evict_head(&mut self) -> usize {
        if let Some(idx) = self.find_free_slot() {
            idx
        } else {
            self.evict_head()
        }
    }

    fn request_page(&mut self, ctx: &mut EventCtx, page_idx: u16) {
        let data = UtilEnum::RequestSlice {
            offset: (page_idx as u32) * (A as u32),
            size: A as u32,
        };

        let mut arena = [MaybeUninit::<u8>::uninit(); 200];
        let mut out = Align([MaybeUninit::<u8>::uninit(); 200]);

        let bytes = to_bytes_in_with_alloc::<_, _, Failure>(
            &data,
            Buffer::from(&mut *out),
            SubAllocator::new(&mut arena),
        )
        .unwrap();

        let msg = IpcMessage::new(9, &bytes);
        unwrap!(msg.send(RemoteSysTask::Unknown(2), 6));
        ctx.request_anim_frame();
    }

    pub fn update(&mut self, data: &[u8], ctx: &mut EventCtx) -> u16 {
        debug_assert!(matches!(
            self.state,
            CacheState::Uninit | CacheState::Waiting(_)
        ));

        match self.state {
            CacheState::Uninit => {
                self.init(data);
                if self.has_next() {
                    let idx = self.current_page as usize + 1;
                    self.state = CacheState::Waiting(idx);
                    self.request_page(ctx, idx as u16);
                } else {
                    self.state = CacheState::Ready;
                }
                ctx.request_paint();
            }
            CacheState::Waiting(next_page) if self.current_page + 1 == next_page as u16 => {
                debug_assert!(self.head.is_some());
                debug_assert!(self.current_node == self.head.unwrap());
                self.set_next(data);
            }
            CacheState::Waiting(prev_page) if self.current_page == prev_page as u16 + 1 => {
                debug_assert!(self.tail.is_some());
                debug_assert!(self.current_node == self.tail.unwrap());
                self.set_prev(data);
            }
            _ => {
                unimplemented!("Unexpected page received");
            }
        }
        0
    }

    /// Add next page data (adds at head, evicts from tail if full)
    pub fn set_next(&mut self, data: &[u8]) {
        debug_assert!(self.has_next() && matches!(self.state, CacheState::Waiting(_)));
        debug_assert!(self.current_node == self.head.unwrap());

        let idx = self.get_slot_evict_tail();
        self.nodes[idx].set_content(data);
        self.insert_at_head(idx);
        self.len += 1;
        self.state = CacheState::Ready;
    }

    /// Add prev page data (adds at tail, evicts from head if full)
    pub fn set_prev(&mut self, data: &[u8]) {
        debug_assert!(self.has_prev() && matches!(self.state, CacheState::Waiting(_)));
        debug_assert!(self.current_node == self.tail.unwrap());
        let idx = self.get_slot_evict_head();
        self.nodes[idx].set_content(data);
        self.insert_at_tail(idx);
        self.len += 1;
        self.state = CacheState::Ready;
    }

    /// Switch to next page in cache
    pub fn switch_next(&mut self, ctx: &mut EventCtx) {
        debug_assert!(self.has_next() && self.state == CacheState::Ready);

        let next_node = self.nodes[self.current_node].next;
        debug_assert!(next_node.is_some());
        self.current_node = next_node.unwrap();
        self.current_page += 1;

        // Request prefetch if there's another page after
        if self.has_next() && self.nodes[self.current_node].next.is_none() {
            let next_idx = self.current_page as usize + 1;
            self.state = CacheState::Waiting(next_idx);
            self.request_page(ctx, next_idx as u16);
        }
    }

    /// Switch to prev page in cache
    pub fn switch_prev(&mut self, ctx: &mut EventCtx) {
        debug_assert!(self.has_prev() && self.state == CacheState::Ready);

        let prev_node = self.nodes[self.current_node].prev;
        debug_assert!(prev_node.is_some());
        self.current_node = prev_node.unwrap();
        self.current_page -= 1;

        // Request prefetch if there's another page before
        if self.has_prev() && self.nodes[self.current_node].prev.is_none() {
            let prev_idx = self.current_page as usize - 1;
            self.state = CacheState::Waiting(prev_idx);
            self.request_page(ctx, prev_idx as u16);
        }
    }

    pub fn current_page_data(&self) -> TString<'static> {
        if self.state == CacheState::Uninit {
            return TString::empty();
        }

        let node = &self.nodes[self.current_node];
        debug_assert!(node.valid);

        unsafe { StrBuffer::from_ptr_and_len(node.content.as_ptr(), node.content_len) }.into()
    }
}

/// Type alias for the default cache configuration
pub type PageCache<const A: usize, const T: usize> = Cache<A, T, 3>;
