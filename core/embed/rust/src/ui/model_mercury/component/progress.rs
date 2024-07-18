use core::mem;

use crate::{
    strutil::TString,
    ui::{
        component::{
            paginated::Paginate,
            text::paragraphs::{Paragraph, Paragraphs},
            Component, Event, EventCtx, Label, Never, Pad,
        },
        display::{self, Font, LOADER_MAX},
        geometry::{Insets, Offset, Rect},
        model_mercury::{
            constant,
            cshape::{render_loader, LoaderRange},
        },
        shape::Renderer,
        util::animation_disabled,
    },
};

use super::theme;

pub struct Progress {
    title: Label<'static>,
    value: u16,
    loader_y_offset: i16,
    indeterminate: bool,
    description: Paragraphs<Paragraph<'static>>,
    description_pad: Pad,
}

impl Progress {
    const AREA: Rect = constant::screen().inset(theme::borders());

    pub fn new(
        title: TString<'static>,
        indeterminate: bool,
        description: TString<'static>,
    ) -> Self {
        Self {
            title: Label::centered(title, theme::label_progress()),
            value: 0,
            loader_y_offset: 0,
            indeterminate,
            description: Paragraphs::new(
                Paragraph::new(&theme::TEXT_NORMAL, description).centered(),
            ),
            description_pad: Pad::with_background(theme::BG),
        }
    }
}

impl Component for Progress {
    type Msg = Never;

    fn place(&mut self, _bounds: Rect) -> Rect {
        let description_lines = 1 + self
            .description
            .inner()
            .content()
            .map(|t| t.chars().filter(|c| *c == '\n').count() as i16);
        let (title, rest) = Self::AREA.split_top(self.title.max_size().y);
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
                if self.description.inner_mut().content() != &new_description {
                    self.description.inner_mut().update(new_description);
                    self.description.change_page(0); // Recompute bounding box.
                    ctx.request_paint();
                    self.description_pad.clear();
                }
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
        let active_color = theme::GREEN_LIGHT;
        let background_color = theme::BG;
        let inactive_color = theme::GREY_EXTRA_DARK;

        let range = if self.indeterminate {
            let start = (self.value as i16 - 100) % 1000;
            let end = (self.value as i16 + 100) % 1000;
            let start = 360.0 * start as f32 / 1000.0;
            let end = 360.0 * end as f32 / 1000.0;
            LoaderRange::FromTo(start, end)
        } else {
            let end = 360.0 * self.value as f32 / 1000.0;
            if self.value >= LOADER_MAX {
                LoaderRange::Full
            } else {
                LoaderRange::FromTo(0.0, end)
            }
        };

        render_loader(
            center,
            inactive_color,
            active_color,
            background_color,
            range,
            target,
        );

        self.description_pad.render(target);
        self.description.render(target);
    }
}

#[cfg(feature = "ui_debug")]
impl crate::trace::Trace for Progress {
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.component("Progress");
    }
}
