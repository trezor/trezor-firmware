use crate::{
    error::Error,
    io::BinaryData,
    strutil::TString,
    ui::{
        component::{text::TextStyle, Component, Event, EventCtx, Label, Never},
        constant::{HEIGHT, WIDTH},
        display::image::ImageInfo,
        geometry::{Insets, Offset, Point, Rect},
        layout::util::get_user_custom_image,
        shape::{self, render_on_canvas, ImageBuffer, Renderer, Rgba8888Canvas},
    },
};

use super::{
    super::{
        component::{Button, ButtonMsg, ButtonStyleSheet},
        fonts,
    },
    constant,
    theme::{self, firmware::button_homebar_style, BLACK, GREEN_EXTRA_DARK, GREEN_LIME},
    ActionBar,
};

const AREA: Rect = constant::screen();

pub struct Homescreen {
    /// Device name with shadow
    label: HomeLabel,
    /// Home action bar
    homebar: ActionBar,
    /// Background image
    image: Option<BinaryData<'static>>,
    bg_image: ImageBuffer<Rgba8888Canvas<'static>>,
}

pub enum HomescreenMsg {
    Dismissed,
    // Menu,
}

impl Homescreen {
    pub fn new(
        label: TString<'static>,
        notification: Option<(TString<'static>, u8)>,
        hold_to_lock: bool,
    ) -> Result<Self, Error> {
        let image = get_homescreen_image();
        let mut buf = ImageBuffer::new(AREA.size())?;

        // ActionBar button
        let button = if let Some((text, level)) = notification {
            let button_style = button_homebar_style(level);
            Button::with_homebar_content(Some(text)).styled(button_style)
        } else {
            let button_style = button_homebar_style(0);
            Button::with_homebar_content(None).styled(button_style)
        };

        render_on_canvas(buf.canvas(), None, |target| {
            if let Some(image) = image {
                shape::JpegImage::new_image(Point::zero(), image).render(target);
            } else {
                render_default_hs(target);
            }
        });

        Ok(Self {
            label: HomeLabel::new(label),
            homebar: ActionBar::new_single(button),
            image,
            bg_image: buf,
        })
    }

    fn render_label<'s>(&'s self, offset: Offset, target: &mut impl Renderer<'s>) {
        target.with_origin(offset, &|target| {
            self.label.render(target);
        });
    }
}

impl Component for Homescreen {
    type Msg = HomescreenMsg;

    fn place(&mut self, bounds: Rect) -> Rect {
        let (content, bar_area) = AREA.split_bottom(theme::ACTION_BAR_HEIGHT);
        let label_area = content
            .inset(theme::SIDE_INSETS)
            .inset(Insets::top(theme::PADDING));

        self.label.place(label_area);
        self.homebar.place(bar_area);
        bounds
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        // TODO: handle click
        self.homebar.event(ctx, event);
        None
    }

    fn render<'s>(&'s self, target: &mut impl Renderer<'s>) {
        if let Some(image) = self.image {
            if let ImageInfo::Jpeg(_) = ImageInfo::parse(image) {
                shape::JpegImage::new_image(AREA.top_left(), image).render(target);
            }
        } else {
            render_default_hs(target);
        }
        // TODO: label animation offset
        self.render_label(Offset::zero(), target);
        self.homebar.render(target);
    }
}

/// Helper component to render a label with a shadow.
struct HomeLabel {
    label: Label<'static>,
    label_shadow: Label<'static>,
}

impl HomeLabel {
    const LABEL_SHADOW_OFFSET: Offset = Offset::uniform(2);
    const LABEL_TEXT_STYLE: TextStyle = theme::firmware::TEXT_BIG;
    const LABEL_SHADOW_TEXT_STYLE: TextStyle = TextStyle::new(
        fonts::FONT_SATOSHI_EXTRALIGHT_46,
        BLACK,
        BLACK,
        BLACK,
        BLACK,
    );

    fn new(label: TString<'static>) -> Self {
        let label_primary = Label::left_aligned(label, Self::LABEL_TEXT_STYLE).top_aligned();
        let label_shadow = Label::left_aligned(label, Self::LABEL_SHADOW_TEXT_STYLE).top_aligned();
        Self {
            label: label_primary,
            label_shadow,
        }
    }

    fn inner(&self) -> &Label<'static> {
        &self.label
    }
}

impl Component for HomeLabel {
    type Msg = Never;
    fn place(&mut self, bounds: Rect) -> Rect {
        self.label.place(bounds);
        self.label_shadow
            .place(bounds.translate(Self::LABEL_SHADOW_OFFSET));
        bounds
    }
    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        None
    }
    fn render<'s>(&'s self, target: &mut impl Renderer<'s>) {
        self.label_shadow.render(target);
        self.label.render(target);
    }
}

pub fn check_homescreen_format(image: BinaryData) -> bool {
    match ImageInfo::parse(image) {
        ImageInfo::Jpeg(info) => {
            info.width() == WIDTH && info.height() == HEIGHT && info.mcu_height() <= 16
        }
        _ => false,
    }
}

fn render_default_hs<'a>(target: &mut impl Renderer<'a>) {
    shape::Bar::new(AREA)
        .with_fg(theme::BG)
        .with_bg(theme::GREEN)
        .render(target);

    shape::Circle::new(AREA.center(), 48)
        .with_fg(GREEN_LIME)
        .with_thickness(4)
        .render(target);
    shape::Circle::new(AREA.center(), 42)
        .with_fg(GREEN_EXTRA_DARK)
        .with_thickness(4)
        .render(target);
}

fn get_homescreen_image() -> Option<BinaryData<'static>> {
    if let Ok(image) = get_user_custom_image() {
        if check_homescreen_format(image) {
            return Some(image);
        }
    }
    None
}

#[cfg(feature = "ui_debug")]
impl crate::trace::Trace for Homescreen {
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.component("Homescreen");
        t.child("label", self.label.inner());
    }
}
