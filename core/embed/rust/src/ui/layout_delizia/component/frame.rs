use super::super::theme::TITLE_HEIGHT;
use super::{theme, Footer, Header};
use crate::strutil::TString;
use crate::ui::component::base::AttachType;
use crate::ui::component::paginated::Paginate;
use crate::ui::component::swipe_detect::{SwipeConfig, SwipeSettings};
use crate::ui::component::Event::{self, Swipe};
use crate::ui::component::{Component, EventCtx, FlowMsg, MsgMap, SwipeDetect};
use crate::ui::event::SwipeEvent;
use crate::ui::geometry::{Direction, Insets, Point, Rect};
use crate::ui::lerp::Lerp;
use crate::ui::shape::{self, Renderer};
#[cfg(feature = "micropython")]
use crate::ui::util::Pager;

#[derive(Clone)]
pub struct HorizontalSwipe {
    progress: i16,
    dir: Direction,
}

impl HorizontalSwipe {
    const fn new() -> Self {
        Self {
            progress: 0,
            dir: Direction::Up,
        }
    }

    fn event(&mut self, event: Event, swipe: SwipeConfig) {
        if let Event::Attach(_) = event {
            self.progress = 0;
        }

        if let Swipe(SwipeEvent::Move(dir, progress)) = event {
            if swipe.is_allowed(dir) {
                match dir {
                    Direction::Left | Direction::Right => {
                        self.progress = progress;
                        self.dir = dir;
                    }
                    _ => {}
                }
            }
        }
    }

    fn render_swipe_cover<'s>(&self, target: &mut impl Renderer<'s>, bounds: Rect) {
        if self.progress > 0 {
            match self.dir {
                Direction::Left => {
                    let shift = pareen::constant(0.0).seq_ease_out(
                        0.0,
                        easer::functions::Circ,
                        1.0,
                        pareen::constant(1.0),
                    );

                    let p = Point::lerp(
                        bounds.top_right(),
                        bounds.top_left(),
                        shift.eval(f32::from(self.progress) / f32::from(SwipeDetect::PROGRESS_MAX)),
                    );

                    shape::Bar::new(Rect::new(p, bounds.bottom_right()))
                        .with_fg(theme::BLACK)
                        .with_bg(theme::BLACK)
                        .render(target);
                }
                Direction::Right => {}
                _ => {}
            }
        }
    }
}

pub struct Frame<T> {
    bounds: Rect,
    content: T,
    header: Option<Header>,
    header_update_fn: Option<fn(&T, &mut EventCtx, &mut Header)>,
    footer: Option<Footer<'static>>,
    footer_update_fn: Option<fn(&T, &mut EventCtx, &mut Footer<'static>)>,
    swipe: SwipeConfig,
    horizontal_swipe: HorizontalSwipe,
    margin: u8,
    #[cfg(feature = "ui_debug")]
    has_menu: bool,
    #[cfg(feature = "ui_debug")]
    has_flow_menu: bool,
}

pub enum FrameMsg<T> {
    Content(T),
    Button(FlowMsg),
}

impl<T> Frame<T>
where
    T: Component + Paginate,
{
    pub const fn with_header(header: Header, content: T) -> Self {
        Self::new(Some(header), content)
    }

    pub const fn content(content: T) -> Self {
        Self::new(None, content)
    }

    #[inline(never)]
    const fn new(header: Option<Header>, content: T) -> Self {
        Self {
            bounds: Rect::zero(),
            content,
            header,
            header_update_fn: None,
            footer: None,
            footer_update_fn: None,
            swipe: SwipeConfig::new(),
            horizontal_swipe: HorizontalSwipe::new(),
            margin: 0,
            #[cfg(feature = "ui_debug")]
            has_menu: false,
            #[cfg(feature = "ui_debug")]
            has_flow_menu: false,
        }
    }

    // `has_menu` is used to gradually introduce multi-item menus (#5189).
    // TODO: After the migration, this flag should be set in `self.header`.
    #[cfg(feature = "ui_debug")]
    pub fn with_external_menu(mut self) -> Self {
        // Allow visiting this menu automatically by tests
        self.has_menu = true;
        self
    }
    #[cfg(not(feature = "ui_debug"))]
    pub fn with_external_menu(self) -> Self {
        self
    }

    // `has_flow_menu` is used to traverse old style (aka non-"external" menus)
    // which are implemented as part of swipe flows.
    // TODO: Once we have eventually replaced all these with new style "external
    // menu" we should get rid of this flag and the related debuglink code.
    #[cfg(feature = "ui_debug")]
    pub fn with_flow_menu(mut self) -> Self {
        // Allow visiting this menu automatically by tests
        self.has_flow_menu = true;
        self
    }
    #[cfg(not(feature = "ui_debug"))]
    pub fn with_flow_menu(self) -> Self {
        self
    }

    #[inline(never)]
    pub fn with_footer(
        mut self,
        instruction: TString<'static>,
        description: Option<TString<'static>>,
    ) -> Self {
        self.footer = Some(Footer::new(instruction, description));
        self
    }

    #[cfg(feature = "translations")]
    pub fn with_tap_footer(self, description: Option<TString<'static>>) -> Self {
        use crate::translations::TR;

        self.with_footer(TR::instructions__tap.into(), description)
            .with_swipe(Direction::Up, SwipeSettings::Default)
    }

    #[cfg(feature = "translations")]
    pub fn with_swipeup_footer(self, description: Option<TString<'static>>) -> Self {
        use crate::translations::TR;

        self.with_footer(TR::instructions__tap_to_continue.into(), description)
            .with_swipe(Direction::Up, SwipeSettings::Default)
    }

    #[inline(never)]
    pub fn with_footer_counter(mut self, instruction: TString<'static>) -> Self {
        self.footer = Some(Footer::with_page_counter(instruction));
        self
    }

    #[inline(never)]
    pub fn with_footer_page_hint(
        mut self,
        description: TString<'static>,
        description_last: TString<'static>,
        instruction: TString<'static>,
        instruction_last: TString<'static>,
    ) -> Self {
        self.footer = Some(Footer::with_page_hint(
            description,
            description_last,
            instruction,
            instruction_last,
        ));
        self
    }

    pub fn register_header_update_fn(mut self, f: fn(&T, &mut EventCtx, &mut Header)) -> Self {
        self.header_update_fn = Some(f);
        self
    }

    pub fn register_footer_update_fn(
        mut self,
        f: fn(&T, &mut EventCtx, &mut Footer<'static>),
    ) -> Self {
        self.footer_update_fn = Some(f);
        self
    }

    pub fn inner(&self) -> &T {
        &self.content
    }

    pub fn update_title(&mut self, ctx: &mut EventCtx, new_title: TString<'static>) {
        debug_assert!(self.header.is_some());
        if let Some(header) = &mut self.header {
            header.update_title(ctx, new_title)
        }
    }

    pub fn update_content<F, R>(&mut self, ctx: &mut EventCtx, update_fn: F) -> R
    where
        F: Fn(&mut EventCtx, &mut T) -> R,
    {
        let res = update_fn(ctx, &mut self.content);
        ctx.request_paint();
        res
    }

    #[inline(never)]
    pub fn with_swipe(mut self, dir: Direction, settings: SwipeSettings) -> Self {
        self.footer = self.footer.map(|f| f.with_swipe(dir));
        self.swipe = self.swipe.with_swipe(dir, settings);
        self
    }

    pub fn with_horizontal_pages(self) -> Self {
        Self {
            swipe: self.swipe.with_horizontal_pages(),
            ..self
        }
    }

    pub fn with_vertical_pages(self) -> Self {
        Self {
            swipe: self.swipe.with_vertical_pages(),
            ..self
        }
    }

    pub fn with_margin(mut self, margin: u8) -> Self {
        self.margin = margin;
        self
    }

    #[allow(clippy::type_complexity)]
    pub fn map_to_button_msg(self) -> MsgMap<Self, fn(FrameMsg<T::Msg>) -> Option<FlowMsg>> {
        MsgMap::new(self, |msg| match msg {
            FrameMsg::Button(b) => Some(b),
            _ => None,
        })
    }

    pub fn map(
        self,
        func: impl Fn(T::Msg) -> Option<FlowMsg>,
    ) -> MsgMap<Self, impl Fn(FrameMsg<T::Msg>) -> Option<FlowMsg>> {
        MsgMap::new(self, move |msg| match msg {
            FrameMsg::Content(c) => func(c),
            FrameMsg::Button(b) => Some(b),
        })
    }
}

impl<T> Component for Frame<T>
where
    T: Component + Paginate,
{
    type Msg = FrameMsg<T::Msg>;

    fn place(&mut self, bounds: Rect) -> Rect {
        self.bounds = bounds;
        let content_area = frame_place(&mut self.header, &mut self.footer, bounds, self.margin);

        self.content.place(content_area);

        bounds
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        if let Some(value) = frame_event(
            &mut self.horizontal_swipe,
            self.swipe,
            &mut self.header,
            ctx,
            event,
        ) {
            return Some(FrameMsg::Button(value));
        }

        let msg = self.content.event(ctx, event).map(FrameMsg::Content);
        if msg.is_some() {
            return msg;
        }

        // handle footer click as a swipe-up event for internal pagination
        if let Some(()) = self.footer.event(ctx, event) {
            // if internal pagination is available, send a swipe up event
            if !self.content.pager().is_last() {
                // swipe up
                let none = self
                    .content
                    .event(ctx, Event::Swipe(SwipeEvent::End(Direction::Up)));
                assert!(none.is_none());
                // attach event which triggers the animation
                let none = self
                    .content
                    .event(ctx, Event::Attach(AttachType::Swipe(Direction::Up)));
                assert!(none.is_none());
                return None;
            } else {
                return Some(FrameMsg::Button(FlowMsg::Next));
            }
        };

        if let Some(header_update_fn) = self.header_update_fn {
            if let Some(header) = &mut self.header {
                header_update_fn(&self.content, ctx, header);
            }
        }

        if let Some(footer_update_fn) = self.footer_update_fn {
            if let Some(footer) = &mut self.footer {
                footer_update_fn(&self.content, ctx, footer);
            }
        }

        None
    }

    fn render<'s>(&'s self, target: &mut impl Renderer<'s>) {
        self.header.render(target);
        self.footer.render(target);
        self.content.render(target);

        self.horizontal_swipe
            .render_swipe_cover(target, self.bounds);
    }
}

fn frame_event(
    horizontal_swipe: &mut HorizontalSwipe,
    swipe_config: SwipeConfig,
    header: &mut Option<Header>,
    ctx: &mut EventCtx,
    event: Event,
) -> Option<FlowMsg> {
    // horizontal_swipe does not return any message
    horizontal_swipe.event(event, swipe_config);
    // msg type of header is FlowMsg, which will be the return value
    header.as_mut()?.event(ctx, event)
}

fn frame_place(
    header: &mut Option<Header>,
    footer: &mut Option<Footer>,
    bounds: Rect,
    margin: u8,
) -> Rect {
    let margin: i16 = margin.into();

    let mut content_area = if let Some(header) = header.as_mut() {
        let header_height = header.place(bounds).height().max(TITLE_HEIGHT);
        bounds.inset(Insets::top(header_height + theme::SPACING + margin))
    } else {
        bounds
    };
    if let Some(footer) = footer {
        // FIXME: spacer at the bottom might be applied also for usage without footer
        // but not for VerticalMenu
        content_area = content_area.inset(Insets::bottom(theme::SPACING));
        let (remaining, footer_area) = content_area.split_bottom(footer.height());
        footer.place(footer_area);
        content_area = remaining.inset(Insets::bottom(margin));
    }
    content_area
}

#[cfg(feature = "micropython")]
impl<T: Paginate> crate::ui::flow::Swipable for Frame<T> {
    fn get_swipe_config(&self) -> SwipeConfig {
        self.swipe
    }

    fn get_pager(&self) -> Pager {
        self.content.pager()
    }
}

#[cfg(feature = "ui_debug")]
impl<T> crate::trace::Trace for Frame<T>
where
    T: crate::trace::Trace,
{
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.component("Frame");
        if let Some(header) = &self.header {
            t.child("header", header);
        }
        t.child("content", &self.content);

        if let Some(footer) = &self.footer {
            t.child("footer", footer);
        }

        t.bool("has_menu", self.has_menu);
        t.bool("has_flow_menu", self.has_flow_menu);
    }
}
