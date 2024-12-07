use core::mem;

use crate::{
    error::Error,
    maybe_trace::MaybeTrace,
    strutil::TString,
    translations::TR,
    ui::{
        component::{
            base::Never, Bar, Child, Component, ComponentExt, Empty, Event, EventCtx, Label, Split,
        },
        constant,
        geometry::{Insets, Offset, Rect},
        shape,
        shape::Renderer,
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

pub struct CoinJoinProgress<U> {
    value: u16,
    indeterminate: bool,
    content: Child<Frame<Split<Empty, U>>>,
    // Label is not a child since circular loader paints large black rectangle which overlaps it.
    // To work around this, draw label every time loader is drawn.
    label: Label<'static>,
}

impl<U> CoinJoinProgress<U> {
    pub fn new(
        text: TString<'static>,
        indeterminate: bool,
    ) -> Result<CoinJoinProgress<impl Component<Msg = Never> + MaybeTrace>, Error> {
        let style = theme::label_coinjoin_progress();
        let label = Label::centered(TR::coinjoin__title_do_not_disconnect.into(), style)
            .vertically_centered();
        let bg = Bar::new(style.background_color, theme::BG, 2);
        let inner = (bg, label);
        CoinJoinProgress::with_background(text, inner, indeterminate)
    }
}

impl<U> CoinJoinProgress<U>
where
    U: Component<Msg = Never>,
{
    pub fn with_background(
        text: TString<'static>,
        inner: U,
        indeterminate: bool,
    ) -> Result<Self, Error> {
        Ok(Self {
            value: 0,
            indeterminate,
            content: Frame::centered(
                theme::label_title(),
                TR::coinjoin__title_progress.into(),
                Split::bottom(RECTANGLE_HEIGHT, 0, Empty, inner),
            )
            .into_child(),
            label: Label::centered(text, theme::TEXT_NORMAL),
        })
    }
}

impl<U> Component for CoinJoinProgress<U>
where
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
            Event::Attach(_) if self.indeterminate => {
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

    fn render<'s>(&'s self, target: &mut impl Renderer<'s>) {
        self.content.render(target);

        let center = constant::screen().center() + Offset::y(LOADER_OFFSET);
        let active_color = theme::FG;
        let background_color = theme::BG;
        let inactive_color = background_color.blend(active_color, 85);

        let start = (self.value as i16 - 100) % 1000;
        let end = (self.value as i16 + 100) % 1000;
        let start = 360.0 * start as f32 / 1000.0;
        let end = 360.0 * end as f32 / 1000.0;

        shape::Circle::new(center, LOADER_OUTER)
            .with_bg(inactive_color)
            .render(target);

        shape::Circle::new(center, LOADER_OUTER)
            .with_bg(active_color)
            .with_start_angle(start)
            .with_end_angle(end)
            .render(target);

        shape::Circle::new(center, LOADER_INNER + 2)
            .with_bg(active_color)
            .render(target);

        shape::Circle::new(center, LOADER_INNER)
            .with_bg(background_color)
            .render(target);

        self.label.render(target);
    }
}

#[cfg(feature = "ui_debug")]
impl<U> crate::trace::Trace for CoinJoinProgress<U>
where
    U: Component + crate::trace::Trace,
{
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.component("CoinJoinProgress");
        t.child("label", &self.label);
        t.child("content", &self.content);
    }
}
