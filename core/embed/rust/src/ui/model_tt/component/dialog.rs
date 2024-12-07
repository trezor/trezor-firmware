use crate::{
    strutil::TString,
    ui::{
        component::{
            image::BlendedImage,
            text::{
                paragraphs::{Paragraph, ParagraphSource, ParagraphVecShort, Paragraphs, VecExt},
                TextStyle,
            },
            Child, Component, Event, EventCtx, Never,
        },
        geometry::{Insets, LinearPlacement, Rect},
        shape::Renderer,
    },
};

use super::theme;

#[cfg_attr(feature = "debug", derive(ufmt::derive::uDebug))]
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

    fn render<'s>(&'s self, target: &mut impl Renderer<'s>) {
        self.content.render(target);
        self.controls.render(target);
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

pub struct IconDialog<U> {
    image: Child<BlendedImage>,
    paragraphs: Paragraphs<ParagraphVecShort<'static>>,
    controls: Child<U>,
}

impl<U> IconDialog<U>
where
    U: Component,
{
    pub fn new(icon: BlendedImage, title: impl Into<TString<'static>>, controls: U) -> Self {
        Self {
            image: Child::new(icon),
            paragraphs: Paragraphs::new(ParagraphVecShort::from_iter([Paragraph::new(
                &theme::TEXT_DEMIBOLD,
                title,
            )
            .centered()]))
            .with_placement(
                LinearPlacement::vertical()
                    .align_at_center()
                    .with_spacing(Self::VALUE_SPACE),
            ),
            controls: Child::new(controls),
        }
    }

    pub fn with_paragraph(mut self, para: Paragraph<'static>) -> Self {
        if !para.content().is_empty() {
            self.paragraphs.inner_mut().add(para);
        }
        self
    }

    pub fn with_text(self, style: &'static TextStyle, text: impl Into<TString<'static>>) -> Self {
        self.with_paragraph(Paragraph::new(style, text).centered())
    }

    pub fn with_description(self, description: impl Into<TString<'static>>) -> Self {
        self.with_text(&theme::TEXT_NORMAL_OFF_WHITE, description)
    }

    pub fn with_value(self, value: impl Into<TString<'static>>) -> Self {
        self.with_text(&theme::TEXT_MONO, value)
    }

    pub fn new_shares(lines: [impl Into<TString<'static>>; 4], controls: U) -> Self {
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
            .into_paragraphs()
            .with_placement(LinearPlacement::vertical().align_at_center()),
            controls: Child::new(controls),
        }
    }

    pub const ICON_AREA_PADDING: i16 = 2;
    pub const ICON_AREA_HEIGHT: i16 = 60;
    pub const VALUE_SPACE: i16 = 5;
}

impl<U> Component for IconDialog<U>
where
    U: Component,
{
    type Msg = DialogMsg<Never, U::Msg>;

    fn place(&mut self, bounds: Rect) -> Rect {
        let bounds = bounds
            .inset(theme::borders())
            .inset(Insets::top(Self::ICON_AREA_PADDING));

        let controls_area = self.controls.place(bounds);
        let content_area = bounds.inset(Insets::bottom(controls_area.height()));

        let (image_area, content_area) = content_area.split_top(Self::ICON_AREA_HEIGHT);

        self.image.place(image_area);
        self.paragraphs.place(content_area);
        bounds
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        self.paragraphs.event(ctx, event);
        self.controls.event(ctx, event).map(Self::Msg::Controls)
    }

    fn render<'s>(&'s self, target: &mut impl Renderer<'s>) {
        self.image.render(target);
        self.paragraphs.render(target);
        self.controls.render(target);
    }
}

#[cfg(feature = "ui_debug")]
impl<U> crate::trace::Trace for IconDialog<U>
where
    U: crate::trace::Trace,
{
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.component("IconDialog");
        t.child("image", &self.image);
        t.child("content", &self.paragraphs);
        t.child("controls", &self.controls);
    }
}
