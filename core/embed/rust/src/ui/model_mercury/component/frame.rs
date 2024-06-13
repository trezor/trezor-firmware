use crate::{
    strutil::TString,
    ui::{
        component::{
            label::Label,
            swipe_detect::{SwipeConfig, SwipeSettings},
            text::TextStyle,
            Component, Event,
            Event::Swipe,
            EventCtx, SwipeDetect, SwipeDirection,
        },
        display::Icon,
        event::SwipeEvent,
        geometry::{Alignment, Insets, Point, Rect},
        lerp::Lerp,
        model_mercury::theme::TITLE_HEIGHT,
        shape,
        shape::Renderer,
    },
};

use super::{theme, Button, ButtonMsg, ButtonStyleSheet, CancelInfoConfirmMsg, Footer};

const BUTTON_EXPAND_BORDER: i16 = 32;

#[derive(Clone)]
pub struct Frame<T> {
    border: Insets,
    bounds: Rect,
    title: Label<'static>,
    subtitle: Option<Label<'static>>,
    button: Option<Button>,
    button_msg: CancelInfoConfirmMsg,
    content: T,
    footer: Option<Footer<'static>>,
    swipe: SwipeConfig,
    internal_page_cnt: usize,
    progress: i16,
    dir: SwipeDirection,
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
            title: Label::new(title, alignment, theme::label_title_main()).vertically_centered(),
            bounds: Rect::zero(),
            subtitle: None,
            border: theme::borders(),
            button: None,
            button_msg: CancelInfoConfirmMsg::Cancelled,
            content,
            footer: None,
            swipe: SwipeConfig::new(),
            internal_page_cnt: 1,
            progress: 0,
            dir: SwipeDirection::Up,
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
        let style = theme::TEXT_SUB_GREY;
        self.title = self.title.top_aligned();
        self.subtitle = Some(Label::new(subtitle, self.title.alignment(), style));
        self
    }

    #[inline(never)]
    fn with_button(mut self, icon: Icon, msg: CancelInfoConfirmMsg, enabled: bool) -> Self {
        let touch_area = Insets::uniform(BUTTON_EXPAND_BORDER);
        self.button = Some(
            Button::with_icon(icon)
                .with_expanded_touch_area(touch_area)
                .initially_enabled(enabled)
                .styled(theme::button_default()),
        );
        self.button_msg = msg;
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
        self.title = self.title.styled(style);
        self
    }

    pub fn subtitle_styled(mut self, style: TextStyle) -> Self {
        if let Some(subtitle) = self.subtitle.take() {
            self.subtitle = Some(subtitle.styled(style))
        }
        self
    }

    pub fn button_styled(mut self, style: ButtonStyleSheet) -> Self {
        if self.button.is_some() {
            self.button = Some(self.button.unwrap().styled(style));
        }
        self
    }

    #[inline(never)]
    pub fn with_footer(
        mut self,
        instruction: TString<'static>,
        description: Option<TString<'static>>,
    ) -> Self {
        let mut footer = Footer::new(instruction);
        if let Some(description_text) = description {
            footer = footer.with_description(description_text);
        }
        self.footer = Some(footer);
        self
    }

    #[inline(never)]
    pub fn with_footer_counter(mut self, instruction: TString<'static>, max_value: u8) -> Self {
        self.footer = Some(Footer::new(instruction).with_page_counter(max_value));
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
        self.title.set_text(new_title);
        ctx.request_paint();
    }

    pub fn update_subtitle(
        &mut self,
        ctx: &mut EventCtx,
        new_subtitle: TString<'static>,
        new_style: Option<TextStyle>,
    ) {
        let style = new_style.unwrap_or(theme::TEXT_SUB_GREY);
        match &mut self.subtitle {
            Some(subtitle) => {
                subtitle.set_style(style);
                subtitle.set_text(new_subtitle);
            }
            None => {
                self.subtitle = Some(Label::new(new_subtitle, self.title.alignment(), style));
            }
        }
        ctx.request_paint();
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
        self.footer = self.footer.map(|f| match dir {
            SwipeDirection::Up => f.with_swipe_up(),
            SwipeDirection::Down => f.with_swipe_down(),
            _ => f,
        });
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

        let (mut header_area, mut content_area) = bounds.split_top(TITLE_HEIGHT);
        content_area = content_area.inset(Insets::top(theme::SPACING));
        header_area = header_area.inset(Insets::sides(theme::SPACING));

        if let Some(b) = &mut self.button {
            let (rest, button_area) = header_area.split_right(TITLE_HEIGHT);
            header_area = rest;
            b.place(button_area);
        }

        if self.subtitle.is_some() {
            let title_area = self.title.place(header_area);
            let remaining = header_area.inset(Insets::top(title_area.height()));
            let _subtitle_area = self.subtitle.place(remaining);
        } else {
            self.title.place(header_area);
        }

        if let Some(footer) = &mut self.footer {
            // FIXME: spacer at the bottom might be applied also for usage without footer
            // but not for VerticalMenu
            content_area = content_area.inset(Insets::bottom(theme::SPACING));
            let (remaining, footer_area) = content_area.split_bottom(footer.height());
            footer.place(footer_area);
            content_area = remaining;
        }

        self.content.place(content_area);

        bounds
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        if let Event::Attach(_) = event {
            self.progress = 0;
        }

        if let Swipe(SwipeEvent::Move(dir, progress)) = event {
            if self.swipe.is_allowed(dir) {
                match dir {
                    SwipeDirection::Left | SwipeDirection::Right => {
                        self.progress = progress;
                        self.dir = dir;
                    }
                    _ => {}
                }
            }
        }

        self.title.event(ctx, event);
        self.subtitle.event(ctx, event);
        self.footer.event(ctx, event);
        let msg = self.content.event(ctx, event).map(FrameMsg::Content);
        if let Some(count) = ctx.page_count() {
            self.internal_page_cnt = count;
        }

        if msg.is_some() {
            return msg;
        }
        if let Some(ButtonMsg::Clicked) = self.button.event(ctx, event) {
            return Some(FrameMsg::Button(self.button_msg));
        }
        None
    }

    fn paint(&mut self) {
        self.title.paint();
        self.subtitle.paint();
        self.button.paint();
        self.footer.paint();
        self.content.paint();
    }
    fn render<'s>(&'s self, target: &mut impl Renderer<'s>) {
        self.title.render(target);
        self.subtitle.render(target);
        self.button.render(target);
        self.footer.render(target);
        self.content.render(target);

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
                        self.bounds.top_right(),
                        self.bounds.top_left(),
                        shift.eval(self.progress as f32 / SwipeDetect::PROGRESS_MAX as f32),
                    );

                    shape::Bar::new(Rect::new(p, self.bounds.bottom_right()))
                        .with_fg(theme::BLACK)
                        .with_bg(theme::BLACK)
                        .render(target);
                }
                SwipeDirection::Right => {}
                _ => {}
            }
        }
    }

    #[cfg(feature = "ui_bounds")]
    fn bounds(&self, sink: &mut dyn FnMut(Rect)) {
        self.title.bounds(sink);
        self.subtitle.bounds(sink);
        self.button.bounds(sink);
        self.footer.bounds(sink);
        self.content.bounds(sink);
    }
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
        t.child("title", &self.title);
        t.child("content", &self.content);
        if let Some(subtitle) = &self.subtitle {
            t.child("subtitle", subtitle);
        }
        if let Some(button) = &self.button {
            t.child("button", button);
        }
        if let Some(footer) = &self.footer {
            t.child("footer", footer);
        }
    }
}
