use crate::{
    strutil::StringType,
    ui::{
        component::{
            image::BlendedImage,
            text::{
                paragraphs::{Paragraph, ParagraphSource, ParagraphVecShort, Paragraphs, VecExt},
                TextStyle,
            },
            Child, Component, Event, EventCtx, Never, Paginate,
        },
        geometry::{Insets, Rect},
        util::ResultExt,
    },
};

use super::theme;

pub enum DialogMsg<T, U> {
    Content(T),
    Controls(U),
}

pub struct Dialog<T, U> {
    content: Child<T>,
    controls: Child<U>,
}

impl<T, U> Dialog<T, U>
where
    T: Component,
    U: Component,
{
    pub fn new(content: T, controls: U) -> Self {
        Self {
            content: Child::new(content),
            controls: Child::new(controls),
        }
    }

    pub fn inner(&self) -> &T {
        self.content.inner()
    }
}

impl<T, U> Component for Dialog<T, U>
where
    T: Component,
    U: Component,
{
    type Msg = DialogMsg<T::Msg, U::Msg>;

    fn place(&mut self, bounds: Rect) -> Rect {
        let controls_area = self.controls.place(bounds);
        let content_area = bounds
            .inset(Insets::bottom(controls_area.height()))
            .inset(Insets::bottom(theme::BUTTON_SPACING))
            .inset(Insets::left(theme::CONTENT_BORDER));
        self.content.place(content_area);
        bounds
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        self.content
            .event(ctx, event)
            .map(Self::Msg::Content)
            .or_else(|| self.controls.event(ctx, event).map(Self::Msg::Controls))
    }

    fn paint(&mut self) {
        self.content.paint();
        self.controls.paint();
    }

    #[cfg(feature = "ui_bounds")]
    fn bounds(&self, sink: &mut dyn FnMut(Rect)) {
        self.content.bounds(sink);
        self.controls.bounds(sink);
    }
}

#[cfg(feature = "ui_debug")]
impl<T, U> crate::trace::Trace for Dialog<T, U>
where
    T: crate::trace::Trace,
    U: crate::trace::Trace,
{
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.component("Dialog");
        t.child("content", &self.content);
        t.child("controls", &self.controls);
    }
}

pub struct IconDialog<T, U> {
    image: Child<BlendedImage>,
    paragraphs: Paragraphs<ParagraphVecShort<T>>,
    controls: Child<U>,
}

impl<T, U> IconDialog<T, U>
where
    T: StringType,
    U: Component,
{
    pub const ICON_AREA_PADDING: i16 = 2;
    pub const TEXT_BUTTON_PADDING: i16 = 15;
    pub const TEXT_ICON_PADDING: i16 = 20;

    pub fn new(icon: BlendedImage, title: T, controls: U) -> Self {
        Self {
            image: Child::new(icon),
            paragraphs: Paragraphs::new(ParagraphVecShort::from_iter([Paragraph::new(
                &theme::TEXT_DEMIBOLD,
                title,
            )
            .centered()])),
            controls: Child::new(controls),
        }
    }

    pub fn from_paragraphs(
        icon: BlendedImage,
        paragraphs: Paragraphs<ParagraphVecShort<T>>,
        controls: U,
    ) -> Self {
        Self {
            image: Child::new(icon),
            paragraphs,
            controls: Child::new(controls),
        }
    }

    pub fn with_text(mut self, style: &'static TextStyle, text: T) -> Self {
        if !text.as_ref().is_empty() {
            self.paragraphs
                .inner_mut()
                .add(Paragraph::new(style, text).centered());
        }
        self
    }

    pub fn with_description(self, description: T) -> Self {
        self.with_text(&theme::TEXT_NORMAL, description)
    }

    pub fn new_shares(lines: [T; 4], controls: U) -> Self {
        let [l0, l1, l2, l3] = lines;
        Self {
            image: Child::new(BlendedImage::new(
                theme::IMAGE_BG_CIRCLE,
                theme::IMAGE_FG_SUCCESS,
                theme::SUCCESS_COLOR,
                theme::FG,
                theme::BG,
            )),
            paragraphs: ParagraphVecShort::from_iter([
                Paragraph::new(&theme::TEXT_NORMAL_OFF_WHITE, l0).centered(),
                Paragraph::new(&theme::TEXT_DEMIBOLD, l1).centered(),
                Paragraph::new(&theme::TEXT_NORMAL_OFF_WHITE, l2).centered(),
                Paragraph::new(&theme::TEXT_DEMIBOLD, l3).centered(),
            ])
            .into_paragraphs(),
            controls: Child::new(controls),
        }
    }
}

impl<T, U> Component for IconDialog<T, U>
where
    T: StringType,
    U: Component,
{
    type Msg = DialogMsg<Never, U::Msg>;

    fn place(&mut self, bounds: Rect) -> Rect {
        let bounds = bounds
            .inset(theme::borders())
            .inset(Insets::top(Self::ICON_AREA_PADDING));

        let controls_area = self.controls.place(bounds);
        let content_area = bounds.inset(Insets::bottom(
            controls_area.height() + Self::TEXT_BUTTON_PADDING,
        ));

        // Determining the height of the content and image for placing them correctly.
        // There are always fixes paddings between components.
        self.paragraphs.place(content_area);
        // if self.paragraphs.page_count() > 1 {
        //     Err::<(), ()>(()).assert_if_debugging_ui("Must be single page");
        // }
        let content_height = self.paragraphs.current_height();
        let (image_area, content_area) = content_area.split_bottom(content_height);
        let image_area = image_area.inset(Insets::bottom(Self::TEXT_ICON_PADDING));
        let image_height = self.image.inner().height();
        // if image_height < image_area.height() {
        //     Err::<(), ()>(()).assert_if_debugging_ui("Not enough space for image");
        // }
        let (_, image_area) = image_area.split_bottom(image_height);

        self.image.place(image_area);
        self.paragraphs.place(content_area);
        bounds
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        self.paragraphs.event(ctx, event);
        self.controls.event(ctx, event).map(Self::Msg::Controls)
    }

    fn paint(&mut self) {
        self.image.paint();
        self.paragraphs.paint();
        self.controls.paint();
    }

    #[cfg(feature = "ui_bounds")]
    fn bounds(&self, sink: &mut dyn FnMut(Rect)) {
        self.image.bounds(sink);
        self.paragraphs.bounds(sink);
        self.controls.bounds(sink);
    }
}

#[cfg(feature = "ui_debug")]
impl<T, U> crate::trace::Trace for IconDialog<T, U>
where
    T: StringType,
    U: crate::trace::Trace,
{
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.component("IconDialog");
        t.child("image", &self.image);
        t.child("content", &self.paragraphs);
        t.child("controls", &self.controls);
    }
}
