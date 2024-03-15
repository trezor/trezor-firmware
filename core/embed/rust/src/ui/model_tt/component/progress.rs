use core::mem;

use crate::{
    error::Error,
    strutil::StringType,
    ui::{
        component::{
            base::ComponentExt,
            paginated::Paginate,
            text::paragraphs::{Paragraph, Paragraphs},
            Child, Component, Event, EventCtx, Label, Never, Pad,
        },
        display::{self, Font},
        geometry::{Insets, Offset, Rect},
        model_tt::constant,
        shape,
        shape::Renderer,
        util::animation_disabled,
    },
};

use super::theme;

pub struct Progress<T> {
    title: Child<Label<T>>,
    value: u16,
    loader_y_offset: i16,
    indeterminate: bool,
    description: Child<Paragraphs<Paragraph<T>>>,
    description_pad: Pad,
    update_description: fn(&str) -> Result<T, Error>,
}

impl<T> Progress<T>
where
    T: StringType,
{
    const AREA: Rect = constant::screen().inset(theme::borders());

    pub fn new(
        title: T,
        indeterminate: bool,
        description: T,
        update_description: fn(&str) -> Result<T, Error>,
    ) -> Self {
        Self {
            title: Label::centered(title, theme::label_progress()).into_child(),
            value: 0,
            loader_y_offset: 0,
            indeterminate,
            description: Paragraphs::new(
                Paragraph::new(&theme::TEXT_NORMAL, description).centered(),
            )
            .into_child(),
            description_pad: Pad::with_background(theme::BG),
            update_description,
        }
    }
}

impl<T> Component for Progress<T>
where
    T: StringType,
{
    type Msg = Never;

    fn place(&mut self, _bounds: Rect) -> Rect {
        let description_lines = 1 + self
            .description
            .inner()
            .inner()
            .content()
            .as_ref()
            .chars()
            .filter(|c| *c == '\n')
            .count() as i16;
        let (title, rest) = Self::AREA.split_top(self.title.inner().max_size().y);
        let (loader, description) =
            rest.split_bottom(Font::NORMAL.line_height() * description_lines);
        let loader = loader.inset(Insets::top(theme::CONTENT_BORDER));
        self.title.place(title);
        self.loader_y_offset = loader.center().y - constant::screen().center().y;
        self.description.place(description);
        self.description_pad.place(description);
        Self::AREA
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        if let Event::Progress(new_value, new_description) = event {
            if mem::replace(&mut self.value, new_value) != new_value {
                if !animation_disabled() {
                    ctx.request_paint();
                }
                self.description.mutate(ctx, |ctx, para| {
                    if para.inner_mut().content().as_ref() != new_description {
                        let new_description = unwrap!((self.update_description)(new_description));
                        para.inner_mut().update(new_description);
                        para.change_page(0); // Recompute bounding box.
                        ctx.request_paint();
                        self.description_pad.clear();
                    }
                });
            }
        }
        None
    }

    fn paint(&mut self) {
        self.title.paint();
        if self.indeterminate {
            display::loader_indeterminate(
                self.value,
                self.loader_y_offset,
                theme::FG,
                theme::BG,
                None,
            );
        } else {
            display::loader(self.value, self.loader_y_offset, theme::FG, theme::BG, None);
        }
        self.description_pad.paint();
        self.description.paint();
    }

    fn render<'s>(&'s self, target: &mut impl Renderer<'s>) {
        self.title.render(target);

        let center = constant::screen().center() + Offset::y(self.loader_y_offset);
        let active_color = theme::FG;
        let background_color = theme::BG;
        let inactive_color = background_color.blend(active_color, 85);

        let (start, end) = if self.indeterminate {
            let start = (self.value as i16 - 100) % 1000;
            let end = (self.value as i16 + 100) % 1000;
            let start = ((start as i32 * 8 * shape::PI4 as i32) / 1000) as i16;
            let end = ((end as i32 * 8 * shape::PI4 as i32) / 1000) as i16;
            (start, end)
        } else {
            let end = ((self.value as i32 * 8 * shape::PI4 as i32) / 1000) as i16;
            (0, end)
        };

        shape::Circle::new(center, constant::LOADER_OUTER)
            .with_bg(inactive_color)
            .render(target);

        shape::Circle::new(center, constant::LOADER_OUTER)
            .with_bg(active_color)
            .with_start_angle(start)
            .with_end_angle(end)
            .render(target);

        shape::Circle::new(center, constant::LOADER_INNER + 2)
            .with_bg(active_color)
            .render(target);

        shape::Circle::new(center, constant::LOADER_INNER)
            .with_bg(background_color)
            .render(target);

        self.description_pad.render(target);
        self.description.render(target);
    }

    #[cfg(feature = "ui_bounds")]
    fn bounds(&self, sink: &mut dyn FnMut(Rect)) {
        sink(Self::AREA);
        self.title.bounds(sink);
        self.description.bounds(sink);
    }
}

#[cfg(feature = "ui_debug")]
impl<T> crate::trace::Trace for Progress<T>
where
    T: StringType,
{
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.component("Progress");
    }
}
