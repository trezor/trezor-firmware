use core::mem;

use crate::{
    maybe_trace::MaybeTrace,
    ui::{
        component::{
            base::Never, painter, Child, Component, ComponentExt, Empty, Event, EventCtx, Label,
            Split,
        },
        display::loader::{loader_circular_uncompress, LoaderDimensions},
        geometry::{Insets, Rect},
        util::animation_disabled,
    },
};

use super::{theme, Frame};

const RECTANGLE_HEIGHT: i16 = 56;
const LABEL_TOP: i16 = 135;
const LOADER_OUTER: i16 = 39;
const LOADER_INNER: i16 = 28;
const LOADER_OFFSET: i16 = -34;
const LOADER_SPEED: u16 = 5;

pub struct CoinJoinProgress<T, U> {
    value: u16,
    indeterminate: bool,
    content: Child<Frame<Split<Empty, U>, &'static str>>,
    // Label is not a child since circular loader paints large black rectangle which overlaps it.
    // To work around this, draw label every time loader is drawn.
    label: Label<T>,
}

impl<T, U> CoinJoinProgress<T, U>
where
    T: AsRef<str>,
{
    pub fn new(
        text: T,
        indeterminate: bool,
    ) -> CoinJoinProgress<T, impl Component<Msg = Never> + MaybeTrace>
    where
        T: AsRef<str>,
    {
        let style = theme::label_coinjoin_progress();
        let label = Label::centered("DO NOT DISCONNECT YOUR TREZOR!", style).vertically_centered();
        let bg = painter::rect_painter(style.background_color, theme::BG);
        let inner = (bg, label);
        CoinJoinProgress::with_background(text, inner, indeterminate)
    }
}

impl<T, U> CoinJoinProgress<T, U>
where
    T: AsRef<str>,
    U: Component<Msg = Never>,
{
    pub fn with_background(text: T, inner: U, indeterminate: bool) -> Self {
        Self {
            value: 0,
            indeterminate,
            content: Frame::centered(
                theme::label_title(),
                "COINJOIN IN PROGRESS",
                Split::bottom(RECTANGLE_HEIGHT, 0, Empty, inner),
            )
            .into_child(),
            label: Label::centered(text, theme::TEXT_NORMAL),
        }
    }
}

impl<T, U> Component for CoinJoinProgress<T, U>
where
    T: AsRef<str>,
    U: Component<Msg = Never>,
{
    type Msg = Never;

    fn place(&mut self, bounds: Rect) -> Rect {
        self.content.place(bounds);
        let label_bounds = bounds.inset(Insets::top(LABEL_TOP));
        self.label.place(label_bounds);
        bounds
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        self.content.event(ctx, event);
        self.label.event(ctx, event);
        match event {
            _ if animation_disabled() => {
                return None;
            }
            Event::Attach if self.indeterminate => {
                ctx.request_anim_frame();
            }
            Event::Timer(EventCtx::ANIM_FRAME_TIMER) => {
                self.value = (self.value + LOADER_SPEED) % 1000;
                ctx.request_anim_frame();
                ctx.request_paint();
            }
            Event::Progress(new_value, _new_description) => {
                if mem::replace(&mut self.value, new_value) != new_value {
                    ctx.request_paint();
                }
            }
            _ => {}
        }
        None
    }

    fn paint(&mut self) {
        self.content.paint();
        loader_circular_uncompress(
            LoaderDimensions::new(LOADER_OUTER, LOADER_INNER),
            LOADER_OFFSET,
            theme::FG,
            theme::BG,
            self.value,
            self.indeterminate,
            None,
        );
        self.label.paint();
    }
}

#[cfg(feature = "ui_debug")]
impl<T, U> crate::trace::Trace for CoinJoinProgress<T, U>
where
    T: AsRef<str>,
    U: Component + crate::trace::Trace,
{
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.component("CoinJoinProgress");
        t.child("label", &self.label);
        t.child("content", &self.content);
    }
}
