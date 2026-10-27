use super::theme;
use crate::strutil::TString;
use crate::ui::component::image::BlendedImage;
use crate::ui::component::text::paragraphs::{
    Paragraph, ParagraphSource, ParagraphVecShort, Paragraphs, VecExt,
};
use crate::ui::component::text::{PageBreaking, TextStyle};
use crate::ui::component::{Child, Component, Empty, Event, EventCtx, Never, Paginate};
use crate::ui::geometry::{Insets, LinearPlacement, Rect};
use crate::ui::shape::Renderer;
use crate::ui::util::Pager;

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

// Text styles of a paginated `IconDialog`, see `IconDialog::style`.
const TEXT_DEMIBOLD_CUT: TextStyle = theme::TEXT_DEMIBOLD.with_page_breaking(PageBreaking::Cut);
const TEXT_NORMAL_OFF_WHITE_CUT: TextStyle =
    theme::TEXT_NORMAL_OFF_WHITE.with_page_breaking(PageBreaking::Cut);
const TEXT_MONO_DATA_CUT: TextStyle = theme::TEXT_MONO_DATA.with_page_breaking(PageBreaking::Cut);

pub struct IconDialog<U> {
    image: Option<Child<BlendedImage>>,
    paragraphs: Paragraphs<ParagraphVecShort<'static>>,
    controls: Child<U>,
    allow_pagination: bool,
}

impl<U> IconDialog<U>
where
    U: Component,
{
    pub fn new(
        icon: BlendedImage,
        title: Option<impl Into<TString<'static>>>,
        controls: U,
    ) -> Self {
        Self::new_inner(icon, title, controls, false)
    }

    fn new_inner(
        icon: BlendedImage,
        title: Option<impl Into<TString<'static>>>,
        controls: U,
        allow_pagination: bool,
    ) -> Self {
        let (image, paragraphs) = if let Some(title) = title {
            let style = Self::style(allow_pagination, &theme::TEXT_DEMIBOLD, &TEXT_DEMIBOLD_CUT);
            let title = Paragraph::new(style, title).centered();
            let para = ParagraphVecShort::from_iter([title]);
            (Some(Child::new(icon)), para)
        } else {
            (None, ParagraphVecShort::new())
        };
        Self {
            image,
            paragraphs: Paragraphs::new(paragraphs).with_placement(
                LinearPlacement::vertical()
                    .align_at_center()
                    .with_spacing(Self::VALUE_SPACE),
            ),
            controls: Child::new(controls),
            allow_pagination,
        }
    }

    /// When paginating, the container signals that the content continues
    /// (scrollbar, "next page" button), so the text doesn't need to mark the
    /// page breaks.
    fn style(
        allow_pagination: bool,
        style: &'static TextStyle,
        paginated_style: &'static TextStyle,
    ) -> &'static TextStyle {
        if allow_pagination {
            paginated_style
        } else {
            style
        }
    }

    pub fn with_paragraph(mut self, para: Paragraph<'static>) -> Self {
        if !para.content().is_empty() {
            self.paragraphs.mutate(|p| {
                p.add(para);
            });
        }
        self
    }

    pub fn with_text(self, style: &'static TextStyle, text: impl Into<TString<'static>>) -> Self {
        self.with_paragraph(Paragraph::new(style, text).centered())
    }

    pub fn with_description(self, description: impl Into<TString<'static>>) -> Self {
        let style = Self::style(
            self.allow_pagination,
            &theme::TEXT_NORMAL_OFF_WHITE,
            &TEXT_NORMAL_OFF_WHITE_CUT,
        );
        self.with_text(style, description)
    }

    pub fn with_value(self, value: impl Into<TString<'static>>) -> Self {
        let style = Self::style(
            self.allow_pagination,
            &theme::TEXT_MONO_DATA,
            &TEXT_MONO_DATA_CUT,
        );
        self.with_text(style, value)
    }

    pub fn new_shares(lines: [impl Into<TString<'static>>; 4], controls: U) -> Self {
        let [l0, l1, l2, l3] = lines;
        Self {
            image: Some(Child::new(BlendedImage::new(
                theme::IMAGE_BG_CIRCLE,
                theme::IMAGE_FG_SUCCESS,
                theme::SUCCESS_COLOR,
                theme::FG,
                theme::BG,
            ))),
            paragraphs: ParagraphVecShort::from_iter([
                Paragraph::new(&theme::TEXT_NORMAL_OFF_WHITE, l0).centered(),
                Paragraph::new(&theme::TEXT_DEMIBOLD, l1).centered(),
                Paragraph::new(&theme::TEXT_NORMAL_OFF_WHITE, l2).centered(),
                Paragraph::new(&theme::TEXT_DEMIBOLD, l3).centered(),
            ])
            .into_paragraphs()
            .with_placement(LinearPlacement::vertical().align_at_center()),
            controls: Child::new(controls),
            allow_pagination: false,
        }
    }

    pub const ICON_AREA_PADDING: i16 = 2;
    pub const ICON_AREA_HEIGHT: i16 = 60;
    pub const VALUE_SPACE: i16 = 5;
}

impl IconDialog<Empty> {
    /// Dialog whose content can paginate. To be placed inside a paginating
    /// container such as `ButtonPage`, which then supplies the controls and the
    /// border insets.
    pub fn new_paginated(icon: BlendedImage, title: Option<impl Into<TString<'static>>>) -> Self {
        Self::new_inner(icon, title, Empty, true)
    }
}

impl<U> Component for IconDialog<U>
where
    U: Component,
{
    type Msg = DialogMsg<Never, U::Msg>;

    fn place(&mut self, bounds: Rect) -> Rect {
        // When paginating inside a container (e.g. `ButtonPage`), the border
        // insets are supplied by the container.
        let bounds = if self.allow_pagination {
            bounds
        } else {
            bounds.inset(theme::borders())
        };
        let bounds = bounds.inset(Insets::top(Self::ICON_AREA_PADDING));

        let controls_area = self.controls.place(bounds);
        let content_area = bounds.inset(Insets::bottom(controls_area.height()));

        let content_area = if let Some(image) = &mut self.image {
            let (image_area, content_area) = content_area.split_top(Self::ICON_AREA_HEIGHT);
            image.place(image_area);
            content_area
        } else {
            content_area
        };

        self.paragraphs.place(content_area);
        bounds
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        self.paragraphs.event(ctx, event);
        self.controls.event(ctx, event).map(Self::Msg::Controls)
    }

    fn render<'s>(&'s self, target: &mut impl Renderer<'s>) {
        if let Some(image) = &self.image {
            image.render(target);
        }
        self.paragraphs.render(target);
        self.controls.render(target);
    }
}

/// `IconDialog` can paginate its content when placed inside a paginating
/// container such as `ButtonPage` (see `IconDialog::new_paginated`). The
/// icon stays visible on all pages, only the text is paginated.
impl<U> Paginate for IconDialog<U>
where
    U: Component,
{
    fn pager(&self) -> Pager {
        self.paragraphs.pager()
    }

    fn change_page(&mut self, active_page: u16) {
        self.paragraphs.change_page(active_page);
    }
}

#[cfg(feature = "ui_debug")]
impl<U> crate::trace::Trace for IconDialog<U>
where
    U: crate::trace::Trace,
{
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.component("IconDialog");
        if let Some(image) = &self.image {
            t.child("image", image);
        }
        t.child("content", &self.paragraphs);
        t.child("controls", &self.controls);
    }
}
