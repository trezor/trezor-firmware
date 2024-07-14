use super::{theme, ButtonStyleSheet, CancelInfoConfirmMsg, Footer, Header};
use crate::{
    strutil::TString,
    ui::{
        component::{
            swipe_detect::{SwipeConfig, SwipeSettings},
            text::TextStyle,
            Component, Event,
            Event::Swipe,
            EventCtx, SwipeDetect, SwipeDirection,
        },
        display::{Color, Icon},
        event::SwipeEvent,
        geometry::{Alignment, Insets, Point, Rect},
        lerp::Lerp,
        model_mercury::theme::TITLE_HEIGHT,
        shape,
        shape::Renderer,
    },
};

#[derive(Clone)]
pub struct HorizontalSwipe {
    progress: i16,
    dir: SwipeDirection,
}

impl HorizontalSwipe {
    const fn new() -> Self {
        Self {
            progress: 0,
            dir: SwipeDirection::Up,
        }
    }

    fn event(&mut self, event: Event, swipe: SwipeConfig) {
        if let Event::Attach(_) = event {
            self.progress = 0;
        }

        if let Swipe(SwipeEvent::Move(dir, progress)) = event {
            if swipe.is_allowed(dir) {
                match dir {
                    SwipeDirection::Left | SwipeDirection::Right => {
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
                SwipeDirection::Left => {
                    let shift = pareen::constant(0.0).seq_ease_out(
                        0.0,
                        easer::functions::Circ,
                        1.0,
                        pareen::constant(1.0),
                    );

                    let p = Point::lerp(
                        bounds.top_right(),
                        bounds.top_left(),
                        shift.eval(self.progress as f32 / SwipeDetect::PROGRESS_MAX as f32),
                    );

                    shape::Bar::new(Rect::new(p, bounds.bottom_right()))
                        .with_fg(theme::BLACK)
                        .with_bg(theme::BLACK)
                        .render(target);
                }
                SwipeDirection::Right => {}
                _ => {}
            }
        }
    }
}

#[derive(Clone)]
pub struct Frame<T> {
    border: Insets,
    bounds: Rect,
    content: T,
    header: Header,
    footer: Option<Footer<'static>>,
    swipe: SwipeConfig,
    internal_page_cnt: usize,
    horizontal_swipe: HorizontalSwipe,
}

pub enum FrameMsg<T> {
    Content(T),
    Button(CancelInfoConfirmMsg),
}

impl<T> Frame<T>
where
    T: Component,
{
    pub const fn new(alignment: Alignment, title: TString<'static>, content: T) -> Self {
        Self {
            bounds: Rect::zero(),
            border: theme::borders(),
            content,
            header: Header::new(alignment, title),
            footer: None,
            swipe: SwipeConfig::new(),
            internal_page_cnt: 1,
            horizontal_swipe: HorizontalSwipe::new(),
        }
    }

    #[inline(never)]
    pub const fn left_aligned(title: TString<'static>, content: T) -> Self {
        Self::new(Alignment::Start, title, content)
    }

    #[inline(never)]
    pub const fn right_aligned(title: TString<'static>, content: T) -> Self {
        Self::new(Alignment::End, title, content)
    }

    #[inline(never)]
    pub const fn centered(title: TString<'static>, content: T) -> Self {
        Self::new(Alignment::Center, title, content)
    }

    #[inline(never)]
    pub const fn with_border(mut self, border: Insets) -> Self {
        self.border = border;
        self
    }

    #[inline(never)]
    pub fn with_subtitle(mut self, subtitle: TString<'static>) -> Self {
        self.header = self.header.with_subtitle(subtitle);
        self
    }

    #[inline(never)]
    fn with_button(mut self, icon: Icon, msg: CancelInfoConfirmMsg, enabled: bool) -> Self {
        self.header = self.header.with_button(icon, enabled, msg);
        self
    }

    pub fn with_cancel_button(self) -> Self {
        self.with_button(theme::ICON_CLOSE, CancelInfoConfirmMsg::Cancelled, true)
    }

    pub fn with_menu_button(self) -> Self {
        self.with_button(theme::ICON_MENU, CancelInfoConfirmMsg::Info, true)
    }

    pub fn with_warning_button(self) -> Self {
        self.with_button(theme::ICON_WARNING, CancelInfoConfirmMsg::Info, false)
            .button_styled(theme::button_danger())
    }

    pub fn title_styled(mut self, style: TextStyle) -> Self {
        self.header = self.header.styled(style);
        self
    }

    pub fn subtitle_styled(mut self, style: TextStyle) -> Self {
        self.header = self.header.subtitle_styled(style);
        self
    }

    pub fn button_styled(mut self, style: ButtonStyleSheet) -> Self {
        self.header = self.header.button_styled(style);
        self
    }

    pub fn with_result_icon(mut self, icon: Icon, color: Color) -> Self {
        self.header = self.header.with_result_icon(icon, color);
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

    #[inline(never)]
    pub fn with_footer_counter(mut self, instruction: TString<'static>, max_value: u8) -> Self {
        self.footer = Some(Footer::new(instruction, None).with_page_counter(max_value));
        self
    }

    pub fn with_danger(self) -> Self {
        self.button_styled(theme::button_danger())
            .title_styled(theme::label_title_danger())
    }

    pub fn inner(&self) -> &T {
        &self.content
    }

    pub fn update_title(&mut self, ctx: &mut EventCtx, new_title: TString<'static>) {
        self.header.update_title(ctx, new_title);
    }

    pub fn update_subtitle(
        &mut self,
        ctx: &mut EventCtx,
        new_subtitle: TString<'static>,
        new_style: Option<TextStyle>,
    ) {
        self.header.update_subtitle(ctx, new_subtitle, new_style);
    }

    pub fn update_content<F, R>(&mut self, ctx: &mut EventCtx, update_fn: F) -> R
    where
        F: Fn(&mut EventCtx, &mut T) -> R,
    {
        let res = update_fn(ctx, &mut self.content);
        ctx.request_paint();
        res
    }

    pub fn update_footer_counter(&mut self, ctx: &mut EventCtx, new_val: u8) {
        if let Some(footer) = &mut self.footer {
            footer.update_page_counter(ctx, new_val);
        }
    }

    #[inline(never)]
    pub fn with_swipe(mut self, dir: SwipeDirection, settings: SwipeSettings) -> Self {
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
}

impl<T> Component for Frame<T>
where
    T: Component,
{
    type Msg = FrameMsg<T::Msg>;

    fn place(&mut self, bounds: Rect) -> Rect {
        self.bounds = bounds;
        let content_area = frame_place(&mut self.header, &mut self.footer, bounds);

        self.content.place(content_area);

        bounds
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        if let Some(value) = frame_event(
            &mut self.horizontal_swipe,
            self.swipe,
            &mut self.header,
            &mut self.footer,
            ctx,
            event,
        ) {
            return Some(FrameMsg::Button(value));
        }

        let msg = self.content.event(ctx, event).map(FrameMsg::Content);
        if let Some(count) = ctx.page_count() {
            self.internal_page_cnt = count;
        }

        if msg.is_some() {
            return msg;
        }

        None
    }

    fn paint(&mut self) {
        self.header.paint();
        self.footer.paint();
        self.content.paint();
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
    header: &mut Header,
    footer: &mut Option<Footer>,
    ctx: &mut EventCtx,
    event: Event,
) -> Option<CancelInfoConfirmMsg> {
    horizontal_swipe.event(event, swipe_config);

    footer.event(ctx, event);

    header.event(ctx, event)
}
fn frame_place(header: &mut Header, footer: &mut Option<Footer>, bounds: Rect) -> Rect {
    let (mut header_area, mut content_area) = bounds.split_top(TITLE_HEIGHT);
    content_area = content_area.inset(Insets::top(theme::SPACING));
    header_area = header_area.inset(Insets::sides(theme::SPACING));

    header.place(header_area);

    if let Some(footer) = footer {
        // FIXME: spacer at the bottom might be applied also for usage without footer
        // but not for VerticalMenu
        content_area = content_area.inset(Insets::bottom(theme::SPACING));
        let (remaining, footer_area) = content_area.split_bottom(footer.height());
        footer.place(footer_area);
        content_area = remaining;
    }
    content_area
}

#[cfg(feature = "micropython")]
impl<T> crate::ui::flow::Swipable for Frame<T> {
    fn get_swipe_config(&self) -> SwipeConfig {
        self.swipe
    }

    fn get_internal_page_count(&self) -> usize {
        self.internal_page_cnt
    }
}

#[cfg(feature = "ui_debug")]
impl<T> crate::trace::Trace for Frame<T>
where
    T: crate::trace::Trace,
{
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.component("Frame");
        t.child("header", &self.header);
        t.child("content", &self.content);

        if let Some(footer) = &self.footer {
            t.child("footer", footer);
        }
    }
}
