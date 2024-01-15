use core::mem;

use crate::{
    error::Error,
    strutil::StringType,
    ui::{
        component::{
            paginated::Paginate,
            text::paragraphs::{Paragraph, Paragraphs},
            Child, Component, Event, EventCtx, Label, Never, Pad,
        },
        constant,
        display::{self, Font, Icon, LOADER_MAX},
        geometry::Rect,
        util::animation_disabled,
    },
};

use super::super::theme;

const BOTTOM_DESCRIPTION_MARGIN: i16 = 10;
const LOADER_Y_OFFSET_TITLE: i16 = -10;
const LOADER_Y_OFFSET_NO_TITLE: i16 = -20;

// Clippy was complaining about `very complex type used`
type UpdateDescriptionFn<T, Error> = fn(&str) -> Result<T, Error>;

pub struct Progress<T>
where
    T: StringType,
{
    title: Option<Child<Label<T>>>,
    value: u16,
    loader_y_offset: i16,
    indeterminate: bool,
    description: Child<Paragraphs<Paragraph<T>>>,
    description_pad: Pad,
    update_description: Option<UpdateDescriptionFn<T, Error>>,
    icon: Icon,
}

impl<T> Progress<T>
where
    T: StringType,
{
    const AREA: Rect = constant::screen();

    pub fn new(indeterminate: bool, description: T) -> Self {
        Self {
            title: None,
            value: 0,
            loader_y_offset: 0,
            indeterminate,
            description: Child::new(Paragraphs::new(
                Paragraph::new(&theme::TEXT_NORMAL, description).centered(),
            )),
            description_pad: Pad::with_background(theme::BG),
            update_description: None,
            icon: theme::ICON_TICK_FAT,
        }
    }

    pub fn with_title(mut self, title: T) -> Self {
        self.title = Some(Child::new(Label::centered(title, theme::TEXT_BOLD)));
        self
    }

    pub fn with_update_description(
        mut self,
        update_description: UpdateDescriptionFn<T, Error>,
    ) -> Self {
        self.update_description = Some(update_description);
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

        let no_title_case = (Rect::zero(), Self::AREA, LOADER_Y_OFFSET_NO_TITLE);
        let (title, rest, loader_y_offset) = if let Some(self_title) = &self.title {
            if !self_title.inner().text().as_ref().is_empty() {
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
            if let Some(update_description) = self.update_description {
                self.description.mutate(ctx, |ctx, para| {
                    // NOTE: not doing any change for empty new descriptions
                    // (currently, there is no use-case for deleting the description)
                    if !new_description.is_empty()
                        && para.inner_mut().content().as_ref() != new_description
                    {
                        let new_description = unwrap!((update_description)(new_description));
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
            display::loader(
                self.value,
                self.loader_y_offset,
                theme::FG,
                theme::BG,
                Some((self.icon, theme::FG)),
            );
        }
        self.description_pad.paint();
        self.description.paint();
    }

    #[cfg(feature = "ui_bounds")]
    fn bounds(&self, sink: &mut dyn FnMut(Rect)) {
        sink(Self::AREA);
        self.title.bounds(sink);
        self.description.bounds(sink);
    }
}

// DEBUG-ONLY SECTION BELOW

#[cfg(feature = "ui_debug")]
impl<T> crate::trace::Trace for Progress<T>
where
    T: StringType,
{
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.component("Progress");
    }
}
