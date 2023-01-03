use core::mem;

use crate::{
    error::Error,
    micropython::buffer::StrBuffer,
    ui::{
        component::{
            base::ComponentExt,
            paginated::Paginate,
            text::paragraphs::{Paragraph, Paragraphs},
            Child, Component, Event, EventCtx, Label, Never, Pad,
        },
        display::{self, Font},
        geometry::Rect,
        model_tr::constant,
        util::animation_disabled,
    },
};

use super::theme;

pub struct Progress {
    title: Child<Label<StrBuffer>>,
    value: u16,
    loader_y_offset: i16,
    indeterminate: bool,
    description: Child<Paragraphs<Paragraph<StrBuffer>>>,
    description_pad: Pad,
    update_description: fn(&str) -> Result<StrBuffer, Error>,
}

impl Progress {
    const AREA: Rect = constant::screen();

    pub fn new(
        title: StrBuffer,
        indeterminate: bool,
        description: StrBuffer,
        update_description: fn(&str) -> Result<StrBuffer, Error>,
    ) -> Self {
        Self {
            title: Label::centered(title, theme::TEXT_HEADER).into_child(),
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

impl Component for Progress {
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

    fn bounds(&self, sink: &mut dyn FnMut(Rect)) {
        sink(Self::AREA);
        self.title.bounds(sink);
        self.description.bounds(sink);
    }
}

// DEBUG-ONLY SECTION BELOW

#[cfg(feature = "ui_debug")]
impl crate::trace::Trace for Progress {
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.open("Progress");
        t.close();
    }
}
