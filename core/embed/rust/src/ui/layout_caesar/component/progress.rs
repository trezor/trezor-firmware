use core::mem;

use crate::{
    strutil::TString,
    ui::{
        component::{
            paginated::Paginate,
            text::paragraphs::{Paragraph, Paragraphs},
            Child, Component, Event, EventCtx, Label, Never, Pad,
        },
        constant,
        display::{Font, Icon, LOADER_MAX},
        geometry::{Alignment2D, Offset, Rect},
        shape,
        shape::Renderer,
        util::animation_disabled,
    },
};

use super::super::{cshape, theme};

const BOTTOM_DESCRIPTION_MARGIN: i16 = 10;
const LOADER_Y_OFFSET_TITLE: i16 = -10;
const LOADER_Y_OFFSET_NO_TITLE: i16 = -20;

pub struct Progress {
    title: Option<Child<Label<'static>>>,
    value: u16,
    loader_y_offset: i16,
    indeterminate: bool,
    description: Child<Paragraphs<Paragraph<'static>>>,
    description_pad: Pad,
    icon: Icon,
}

impl Progress {
    const AREA: Rect = constant::screen();

    pub fn new(indeterminate: bool, description: TString<'static>) -> Self {
        Self {
            title: None,
            value: 0,
            loader_y_offset: 0,
            indeterminate,
            description: Child::new(Paragraphs::new(
                Paragraph::new(&theme::TEXT_NORMAL, description).centered(),
            )),
            description_pad: Pad::with_background(theme::BG),
            icon: theme::ICON_TICK_FAT,
        }
    }

    pub fn with_title(mut self, title: TString<'static>) -> Self {
        self.title = Some(Child::new(Label::centered(title, theme::TEXT_BOLD_UPPER)));
        self
    }

    pub fn with_icon(mut self, icon: Icon) -> Self {
        self.icon = icon;
        self
    }

    pub fn request_paint(&self, ctx: &mut EventCtx) {
        if !animation_disabled() {
            ctx.request_paint();
        }
    }

    pub fn value(&self) -> u16 {
        self.value
    }

    pub fn reached_max_value(&self) -> bool {
        self.value >= LOADER_MAX
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
            .map(|t| t.chars().filter(|c| *c == '\n').count() as i16);

        let no_title_case = (Rect::zero(), Self::AREA, LOADER_Y_OFFSET_NO_TITLE);
        let (title, rest, loader_y_offset) = if let Some(self_title) = &self.title {
            if !self_title.inner().text().is_empty() {
                let (title, rest) = Self::AREA.split_top(self_title.inner().max_size().y);
                (title, rest, LOADER_Y_OFFSET_TITLE)
            } else {
                no_title_case
            }
        } else {
            no_title_case
        };

        let (_loader, description) = rest.split_bottom(
            BOTTOM_DESCRIPTION_MARGIN + Font::NORMAL.line_height() * description_lines,
        );
        self.title.place(title);
        self.loader_y_offset = loader_y_offset;
        self.description.place(description);
        self.description_pad.place(description);
        Self::AREA
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        self.title.event(ctx, event);
        self.description.event(ctx, event);

        if let Event::Progress(new_value, new_description) = event {
            if mem::replace(&mut self.value, new_value) != new_value {
                self.request_paint(ctx);
            }
            self.description.mutate(ctx, |ctx, para| {
                // NOTE: not doing any change for empty new descriptions
                // (currently, there is no use-case for deleting the description)
                if !new_description.is_empty() && para.inner_mut().content() != &new_description {
                    para.inner_mut().update(new_description);
                    para.change_page(0); // Recompute bounding box.
                    ctx.request_paint();
                    self.description_pad.clear();
                }
            });
        } else {
            self.title.event(ctx, event);
            self.description.event(ctx, event);
        }
        None
    }

    fn render<'s>(&'s self, target: &mut impl Renderer<'s>) {
        self.title.render(target);

        let area = constant::screen();
        let center = area.center() + Offset::y(self.loader_y_offset);

        if self.indeterminate {
            cshape::LoaderStarry::new(center, self.value)
                .with_color(theme::FG)
                .render(target);
        } else {
            cshape::LoaderCircular::new(center, self.value)
                .with_color(theme::FG)
                .render(target);
            shape::ToifImage::new(center, self.icon.toif)
                .with_align(Alignment2D::CENTER)
                .with_fg(theme::FG)
                .render(target);
        }
        self.description_pad.render(target);
        self.description.render(target);
    }
}

// DEBUG-ONLY SECTION BELOW

#[cfg(feature = "ui_debug")]
impl crate::trace::Trace for Progress {
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.component("Progress");
    }
}
