use core::mem::MaybeUninit;
use minicbor::data;
use rkyv::{
    api::low::to_bytes_in_with_alloc,
    rancor::Failure,
    ser::{allocator::SubAllocator, writer::Buffer},
    util::Align,
    Archive, Deserialize, Serialize,
};
use trezor_structs::UtilEnum;

use crate::{
    ipc::{self, IpcMessage, RemoteSysTask},
    strutil::TString,
    ui::{
        cache::{Cache, CacheState, PageCache},
        component::{base::AttachType, Component, Event, EventCtx, Never, TextLayout},
        flow::page,
        geometry::Rect,
        shape::Renderer,
        util::Pager,
    },
};

use super::{constant::SCREEN, theme, ActionBar, ActionBarMsg, Header};

pub const CHARS_PER_PAGE: u16 = 10;

pub enum LongContentScreenMsg {
    Confirmed,
    Cancelled,
}

pub struct LongContentScreen {
    header: Header,
    content: LongContent,
    action_bar: ActionBar,
}

impl LongContentScreen {
    pub fn new(title: TString<'static>, text_length: u32) -> Self {
        let content = LongContent::new(text_length);
        let mut action_bar = ActionBar::new_cancel_confirm();
        action_bar.update(content.pager);

        Self {
            header: Header::new(title),
            content,
            action_bar,
        }
    }

    fn switch_next(&mut self) {
        debug_assert!(!self.content.pager.is_last());
        self.content.switch_next();
        let new_pager = self.content.pager();
        self.action_bar.update(new_pager);
    }

    fn switch_prev(&mut self) {
        debug_assert!(!self.content.pager.is_first());
        self.content.switch_prev();
        let new_pager = self.content.pager();
        self.action_bar.update(new_pager);
    }
}

impl Component for LongContentScreen {
    type Msg = LongContentScreenMsg;
    fn place(&mut self, bounds: Rect) -> Rect {
        // assert full screen
        debug_assert_eq!(bounds.height(), SCREEN.height());
        debug_assert_eq!(bounds.width(), SCREEN.width());

        let (header_area, rest) = bounds.split_top(Header::HEADER_HEIGHT);
        let (content_area, action_bar_area) = rest.split_bottom(ActionBar::ACTION_BAR_HEIGHT);

        self.header.place(header_area);
        self.content.place(content_area);
        self.action_bar.place(action_bar_area);

        bounds
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        // Update page count of the screen
        // ctx.set_page_count(self.content.pager().total());

        self.content.event(ctx, event);

        if let Some(msg) = self.action_bar.event(ctx, event) {
            match msg {
                ActionBarMsg::Confirmed => return Some(LongContentScreenMsg::Confirmed),
                ActionBarMsg::Cancelled => return Some(LongContentScreenMsg::Cancelled),
                ActionBarMsg::Next => {
                    debug_assert!(!self.content.pager.is_last());
                    self.switch_next();
                    return None;
                }
                ActionBarMsg::Prev => {
                    debug_assert!(!self.content.pager.is_first());
                    self.switch_prev();
                    return None;
                }
            }
        };

        None
    }

    fn render<'s>(&'s self, target: &mut impl Renderer<'s>) {
        self.header.render(target);
        self.content.render(target);
        self.action_bar.render(target);
    }
}

#[cfg(feature = "ui_debug")]
impl crate::trace::Trace for LongContentScreen {
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.component("LongContentScreen");
        t.child("Header", &self.header);
        // t.child("Content", &self.content);
        t.child("ActionBar", &self.action_bar);
    }
}

struct LongContent {
    pager: Pager,
    content_length: u32,
    cache: PageCache,
    area: Rect,
}

impl LongContent {
    fn new(content_length: u32) -> Self {
        let total_pages = ((content_length as u16) + CHARS_PER_PAGE - 1) / CHARS_PER_PAGE;
        Self {
            pager: Pager::new(total_pages),
            content_length,
            cache: PageCache::new(total_pages),
            area: Rect::zero(),
        }
    }

    fn pager(&self) -> Pager {
        self.pager
    }

    fn switch_next(&mut self) {
        self.pager.goto_next();
        self.cache.switch_next();
    }

    fn switch_prev(&mut self) {
        self.pager.goto_prev();
        self.cache.switch_prev();
    }

    fn request_page(&mut self, ctx: &mut EventCtx, page_idx: u16) {
        let data = UtilEnum::RequestSlice {
            offset: (page_idx as u32) * (CHARS_PER_PAGE as u32),
            size: CHARS_PER_PAGE as u32,
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

    fn set_page(&mut self, data: &[u8], ctx: &mut EventCtx) {
        match self.cache.state() {
            CacheState::Uninit => {
                self.cache.init(data);

                if self.cache.has_next() {
                    let page_idx = self.pager.next();
                    self.cache.set_state(CacheState::Waiting(page_idx as usize));
                    self.request_page(ctx, page_idx);
                } else {
                    self.cache.set_state(CacheState::Ready);
                }
                ctx.request_paint();
            }
            CacheState::Waiting(next_page) if self.cache.current_page() == next_page as u16 - 1 => {
                self.cache.set_next(data);
                // let current_page = self.pager.current() as usize;
                // if expected_page == current_page + 1 {
                //     self.cache.set_page(data);

                //     if self.cache.has_next() {
                //         let page_idx = self.pager.next();
                //         self.cache.set_state(CacheState::Waiting(page_idx as
                // usize));         self.request_page(ctx,
                // page_idx);     } else {
                //         self.cache.set_state(CacheState::Ready);
                //     }
                // } else {
                //     // Unexpected page received, ignore
                //     ctx.request_anim_frame();
                // }
            }
            CacheState::Waiting(next_page) if self.cache.current_page() == next_page as u16 - 1 => {
                self.cache.set_prev(data);
            }
            CacheState::Waiting(_) => {
                unimplemented!("Unexpected page received, ignore");
            }

            CacheState::Ready => {
                // Already ready, ignore
            }
        }
    }
}

impl Component for LongContent {
    type Msg = Never;

    fn place(&mut self, bounds: Rect) -> Rect {
        self.area = bounds;
        bounds
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        if matches!(event, Event::Attach(AttachType::Initial)) {
            // debug_assert!(self.cache.state == CacheState::Empty);
            // Load content into cache if needed
            self.request_page(ctx, 0);
        }

        if let Event::Timer(EventCtx::ANIM_FRAME_TIMER) = event {
            if let Some(data) = IpcMessage::try_receive(RemoteSysTask::Unknown(2)) {
                self.set_page(&data.data(), ctx);
            } else {
                ctx.request_anim_frame();
            }
        }

        None
    }

    fn render<'s>(&'s self, target: &mut impl Renderer<'s>) {
        let current_page = self.cache.current_page_data();

        current_page.map(|text| {
            TextLayout::new(theme::TEXT_MONO_MEDIUM)
                .with_bounds(self.area)
                .render_text(text, target, true)
        });
    }
}
