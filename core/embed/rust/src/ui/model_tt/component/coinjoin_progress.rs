use core::mem;

use crate::{
    error::Error,
    maybe_trace::MaybeTrace,
    micropython::buffer::StrBuffer,
    translations::TR,
    ui::{
        canvas::algo::PI4,
        component::{
            base::Never, Bar, Child, Component, ComponentExt, Empty, Event, EventCtx, Label, Split,
        },
        constant,
        display::loader::{loader_circular_uncompress, LoaderDimensions},
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

pub struct CoinJoinProgress<T, U> {
    value: u16,
    indeterminate: bool,
    content: Child<Frame<Split<Empty, U>, StrBuffer>>,
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
    ) -> Result<CoinJoinProgress<T, impl Component<Msg = Never> + MaybeTrace>, Error>
    where
        T: AsRef<str>,
    {
        let style = theme::label_coinjoin_progress();
        let label = Label::centered(
            TryInto::<StrBuffer>::try_into(TR::coinjoin__title_do_not_disconnect)?,
            style,
        )
        .vertically_centered();
        let bg = Bar::new(style.background_color, theme::BG, 2);
        let inner = (bg, label);
        CoinJoinProgress::with_background(text, inner, indeterminate)
    }
}

impl<T, U> CoinJoinProgress<T, U>
where
    T: AsRef<str>,
    U: Component<Msg = Never>,
{
    pub fn with_background(text: T, inner: U, indeterminate: bool) -> Result<Self, Error> {
        Ok(Self {
            value: 0,
            indeterminate,
            content: Frame::centered(
                theme::label_title(),
                TR::coinjoin__title_progress.try_into()?,
                Split::bottom(RECTANGLE_HEIGHT, 0, Empty, inner),
            )
            .into_child(),
            label: Label::centered(text, theme::TEXT_NORMAL),
        })
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

    fn render<'s>(&'s self, target: &mut impl Renderer<'s>) {
        self.content.render(target);

        let center = constant::screen().center() + Offset::y(LOADER_OFFSET);
        let active_color = theme::FG;
        let background_color = theme::BG;
        let inactive_color = background_color.blend(active_color, 85);

        let start = (self.value as i16 - 100) % 1000;
        let end = (self.value as i16 + 100) % 1000;
        let start = ((start as i32 * 8 * PI4 as i32) / 1000) as i16;
        let end = ((end as i32 * 8 * PI4 as i32) / 1000) as i16;

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
