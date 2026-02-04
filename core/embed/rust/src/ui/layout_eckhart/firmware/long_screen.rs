use crate::{
    ipc::{CoreIpcService, IpcMessage, RemoteSysTask},
    strutil::TString,
    ui::{
        cache::PageCache,
        component::{
            base::AttachType,
            text::{layout::LayoutFit, LineBreaking},
            Component, Event, EventCtx, Never, TextLayout,
        },
        geometry::Rect,
        shape::Renderer,
        util::Pager,
    },
};

use core::mem::MaybeUninit;
use rkyv::{
    api::low::to_bytes_in_with_alloc,
    rancor::Failure,
    ser::{allocator::SubAllocator, writer::Buffer},
    util::Align,
};
use trezor_structs::UtilEnum;

use super::{constant::SCREEN, theme, ActionBar, ActionBarMsg, Header, Hint};

pub enum LongContentScreenMsg {
    Confirmed,
    Cancelled,
}

pub struct LongContentScreen<'a> {
    header: Header,
    content: LongContent,
    hint: Hint<'a>,
    action_bar: ActionBar,
}

impl<'a> LongContentScreen<'a> {
    pub fn new(title: TString<'static>, pages: usize, remote: u8) -> Self {
        let content = LongContent::new(pages as u16, remote);
        let mut action_bar = ActionBar::new_cancel_confirm();
        action_bar.update(content.pager);

        let mut hint = Hint::new_page_counter();
        hint.update(content.pager);

        Self {
            header: Header::new(title),
            content,
            hint,
            action_bar,
        }
    }

    fn switch_next(&mut self, ctx: &mut EventCtx) {
        // The next button shoudn't be available at the last page
        debug_assert!(!self.content.pager.is_last());
        self.content.switch_next(ctx);
        let new_pager = self.content.pager();
        self.hint.update(new_pager);
        self.action_bar.update(new_pager);
    }

    fn switch_prev(&mut self, ctx: &mut EventCtx) {
        // The prev button shoudn't be available at the first page
        debug_assert!(!self.content.pager.is_first());
        self.content.switch_prev(ctx);
        let new_pager = self.content.pager();
        self.hint.update(new_pager);
        self.action_bar.update(new_pager);
    }
}

impl<'a> Component for LongContentScreen<'a> {
    type Msg = LongContentScreenMsg;
    fn place(&mut self, bounds: Rect) -> Rect {
        // assert full screen
        debug_assert_eq!(bounds.height(), SCREEN.height());
        debug_assert_eq!(bounds.width(), SCREEN.width());

        let (header_area, rest) = bounds.split_top(Header::HEADER_HEIGHT);
        let (rest, action_bar_area) = rest.split_bottom(ActionBar::ACTION_BAR_HEIGHT);
        let (content_area, hint_area) = rest.split_bottom(self.hint.height());

        self.header.place(header_area);
        self.content.place(content_area);
        self.hint.place(hint_area);
        self.action_bar.place(action_bar_area);

        bounds
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        self.content.event(ctx, event);

        if let Some(msg) = self.action_bar.event(ctx, event) {
            match msg {
                ActionBarMsg::Confirmed => return Some(LongContentScreenMsg::Confirmed),
                ActionBarMsg::Cancelled => return Some(LongContentScreenMsg::Cancelled),
                ActionBarMsg::Next => {
                    debug_assert!(!self.content.pager.is_last());
                    self.switch_next(ctx);
                    return None;
                }
                ActionBarMsg::Prev => {
                    debug_assert!(!self.content.pager.is_first());
                    self.switch_prev(ctx);
                    return None;
                }
            }
        };

        None
    }

    fn render<'s>(&'s self, target: &mut impl Renderer<'s>) {
        self.header.render(target);
        self.content.render(target);
        self.hint.render(target);
        self.action_bar.render(target);
    }
}

#[cfg(feature = "ui_debug")]
impl<'a> crate::trace::Trace for LongContentScreen<'a> {
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.component("LongContentScreen");
        t.child("Header", &self.header);
        t.child("Content", &self.content);
        t.child("Hint", &self.hint);
        t.child("ActionBar", &self.action_bar);
    }
}

struct LongContent {
    pager: Pager,
    cache: PageCache,
    area: Rect,
    state: ContentState,
    remote: u8,
}

impl LongContent {
    fn new(pages: u16, remote: u8) -> Self {
        Self {
            pager: Pager::new(pages),
            cache: PageCache::new(),
            area: Rect::zero(),
            state: ContentState::Uninit,
            remote,
        }
    }

    fn pager(&self) -> Pager {
        self.pager
    }

    fn switch_next(&mut self, ctx: &mut EventCtx) {
        debug_assert!(!self.pager.is_last());
        debug_assert!(matches!(self.state, ContentState::Ready));
        self.pager.goto_next();
        self.cache.go_next();

        // Request prefetch if there's another page after
        if self.pager.has_next() && self.cache.is_at_head() {
            let next = self.pager.next() as usize;
            self.request_page(ctx, next);
            self.state = ContentState::Waiting(next);
        }
    }

    fn switch_prev(&mut self, ctx: &mut EventCtx) {
        debug_assert!(!self.pager.is_first());
        debug_assert!(matches!(self.state, ContentState::Ready));
        self.pager.goto_prev();
        self.cache.go_prev();

        // Request prefetch if there's another page before
        if self.pager.has_prev() && self.cache.is_at_tail() {
            let prev = self.pager.prev() as usize;
            self.request_page(ctx, prev);
            self.state = ContentState::Waiting(prev);
        }
    }

    fn request_page(&mut self, ctx: &mut EventCtx, idx: usize) {
        let data = UtilEnum::RequestPage { idx };

        let mut arena = [MaybeUninit::<u8>::uninit(); 200];
        let mut out = Align([MaybeUninit::<u8>::uninit(); 200]);

        let bytes = to_bytes_in_with_alloc::<_, _, Failure>(
            &data,
            Buffer::from(&mut *out),
            SubAllocator::new(&mut arena),
        )
        .unwrap();

        let msg = IpcMessage::new(idx as u16, &bytes);
        unwrap!(msg.send(RemoteSysTask::Unknown(self.remote), CoreIpcService::Util.into()));
        ctx.request_anim_frame();
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
            if let Some(message) = IpcMessage::try_receive(RemoteSysTask::Unknown(2)) {
                debug_assert!(matches!(
                    self.state,
                    ContentState::Uninit | ContentState::Waiting(_)
                ));
                self.state = match self.state {
                    ContentState::Uninit => {
                        debug_assert!(message.id() == 0);
                        self.cache.init(message.data());
                        ctx.request_paint();
                        if self.pager.has_next() {
                            let idx = self.pager.next() as usize;
                            self.request_page(ctx, idx);
                            ContentState::Waiting(idx)
                        } else {
                            ContentState::Ready
                        }
                    }
                    ContentState::Waiting(next_page)
                        if self.pager.current() + 1 == next_page as u16 =>
                    {
                        debug_assert!(message.id() == next_page as u16);
                        debug_assert!(self.cache.is_at_head());
                        self.cache.push_head(message.data());
                        ContentState::Ready
                    }
                    ContentState::Waiting(prev_page)
                        if self.pager.current() == prev_page as u16 + 1 =>
                    {
                        debug_assert!(message.id() == prev_page as u16);
                        debug_assert!(self.cache.is_at_tail());
                        self.cache.push_tail(message.data());
                        ContentState::Ready
                    }
                    _ => {
                        unimplemented!("Unexpected page received");
                    }
                }
            } else {
                ctx.request_anim_frame();
            }
        }

        None
    }

    fn render<'s>(&'s self, target: &mut impl Renderer<'s>) {
        let current_page = self.cache.current_data().unwrap_or(TString::empty());

        current_page.map(|text| {
            let layout = TextLayout::new(
                theme::TEXT_MONO_MEDIUM.with_line_breaking(LineBreaking::BreakWordsNoHyphen),
            )
            .with_bounds(self.area);

            // must fit parameter doesn't have effect here
            debug_assert!(matches!(layout.fit_text(text), LayoutFit::Fitting { .. }));

            layout.render_text(text, target, true)
        });
    }
}

#[cfg(feature = "ui_debug")]
impl crate::trace::Trace for LongContent {
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.component("LongContent");
        t.int("current_page", self.pager.current() as i64);
        t.int("total_pages", self.pager.total() as i64);
    }
}

#[derive(Clone, Copy, PartialEq, Eq)]
enum ContentState {
    Uninit,
    Waiting(usize),
    Ready,
}
