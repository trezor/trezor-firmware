use crate::{
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
use trezor_app_sdk::ui::{UtilEnum, UTIL_SERVICE_ID};

use super::{constant::SCREEN, theme, ActionBar, ActionBarMsg, Header, Hint};

/// The extapp remote task id whose IPC buffer the coreapp registers once at
/// startup (see `ipc_register(2, ...)` in `main.c`). Hardcoded rather than
/// taken from `self.remote` because that registration is per-coreapp, not
/// per-request: today there is exactly one extapp remote to poll for page
/// replies, regardless of which extapp originated this screen.
const EXTAPP_REMOTE: u8 = 2;

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
    pub fn new(title: TString<'static>, pages: u32, remote: u8) -> Self {
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
        // The next button shouldn't be available at the last page
        debug_assert!(!self.content.pager.is_last());
        self.content.switch_next(ctx);
        let new_pager = self.content.pager();
        self.hint.update(new_pager);
        self.action_bar.update(new_pager);
    }

    fn switch_prev(&mut self, ctx: &mut EventCtx) {
        // The prev button shouldn't be available at the first page
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
        let data = UtilEnum::RequestPage { idx: idx as u32 };

        let mut arena = [MaybeUninit::<u8>::uninit(); 200];
        let mut out = Align([MaybeUninit::<u8>::uninit(); 200]);

        let bytes = to_bytes_in_with_alloc::<_, _, Failure>(
            &data,
            Buffer::from(&mut *out),
            SubAllocator::new(&mut arena),
        )
        .unwrap();

        debug_assert!(sys::ipc::send(
            self.remote,
            UTIL_SERVICE_ID,
            idx as u16,
            &bytes,
        ));
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
            // Load content into cache if needed
            self.request_page(ctx, 0);
        }

        if let Event::Timer(EventCtx::ANIM_FRAME_TIMER) = event {
            if let Some(message) = sys::ipc::try_receive(EXTAPP_REMOTE) {
                // This buffer is shared by every service the extapp talks to
                // Core over (Ui, Crypto, ...) -- make sure we're not about
                // to treat someone else's message as our page reply.
                debug_assert_eq!(message.service(), UTIL_SERVICE_ID);
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
        t.int("current_page", i64::from(self.pager.current()));
        t.int("total_pages", i64::from(self.pager.total()));
        // Debug tooling (e.g. `LayoutContent.text_content()`) reads any
        // "text" string it finds in the trace tree -- `render()` draws this
        // same text directly, bypassing the Paragraphs/FormattedText
        // components that would otherwise carry it.
        if let Some(text) = self.cache.current_data() {
            t.string("text", text);
        }
    }
}

#[derive(Clone, Copy, PartialEq, Eq)]
enum ContentState {
    Uninit,
    Waiting(usize),
    Ready,
}
