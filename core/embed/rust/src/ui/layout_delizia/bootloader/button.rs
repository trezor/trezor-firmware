use super::super::theme::bootloader::BUTTON_FONT;
use crate::ui::component::{Component, Event, EventCtx};
use crate::ui::display::{Color, Icon};
use crate::ui::event::TouchEvent;
use crate::ui::geometry::{Alignment, Alignment2D, Insets, Offset, Point, Rect};
use crate::ui::shape::{self, Renderer};

/// Content of a bootloader button.
pub enum ButtonContent {
    /// Centered text
    Text(&'static str),
    /// Centered icon
    Icon(Icon),
    /// Icon on the left, followed by single-line text
    IconText(&'static str, Icon),
}

pub struct ButtonStyle {
    pub text_color: Color,
    pub button_color: Color,
    pub icon_color: Color,
}

pub struct ButtonStyleSheet {
    pub normal: ButtonStyle,
    pub active: ButtonStyle,
}

/// Touch button sent when clicked. A simplified copy of the firmware `Button`
/// without long press, disabled state, alpha and rounded corners.
pub struct Button {
    area: Rect,
    touch_expand: Insets,
    content: ButtonContent,
    styles: &'static ButtonStyleSheet,
    pressed: bool,
}

impl Button {
    const ICON_SPACE: i16 = 46;
    const ICON_MARGIN: i16 = 4;

    pub const fn new(content: ButtonContent, styles: &'static ButtonStyleSheet) -> Self {
        Self {
            area: Rect::zero(),
            touch_expand: Insets::zero(),
            content,
            styles,
            pressed: false,
        }
    }

    pub const fn with_text(text: &'static str, styles: &'static ButtonStyleSheet) -> Self {
        Self::new(ButtonContent::Text(text), styles)
    }

    pub const fn with_icon(icon: Icon, styles: &'static ButtonStyleSheet) -> Self {
        Self::new(ButtonContent::Icon(icon), styles)
    }

    pub const fn with_expanded_touch_area(mut self, expand: Insets) -> Self {
        self.touch_expand = expand;
        self
    }

    fn set_pressed(&mut self, ctx: &mut EventCtx, pressed: bool) {
        if self.pressed != pressed {
            self.pressed = pressed;
            ctx.request_paint();
        }
    }
}

impl Component for Button {
    /// Sent when the button is clicked
    type Msg = ();

    fn place(&mut self, bounds: Rect) -> Rect {
        self.area = bounds;
        bounds
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        let touch_area = self.area.outset(self.touch_expand);
        match event {
            Event::Touch(TouchEvent::TouchStart(pos)) if touch_area.contains(pos) => {
                self.set_pressed(ctx, true);
            }
            // Leaving the area cancels the press
            Event::Touch(TouchEvent::TouchMove(pos)) if !touch_area.contains(pos) => {
                self.set_pressed(ctx, false);
            }
            Event::Touch(TouchEvent::TouchEnd(pos)) if self.pressed => {
                self.set_pressed(ctx, false);
                if touch_area.contains(pos) {
                    return Some(());
                }
            }
            _ => {}
        }
        None
    }

    fn render<'s>(&'s self, target: &mut impl Renderer<'s>) {
        let style = if self.pressed {
            &self.styles.active
        } else {
            &self.styles.normal
        };

        shape::Bar::new(self.area)
            .with_bg(style.button_color)
            .with_fg(style.button_color)
            .render(target);

        match self.content {
            ButtonContent::Text(text) => {
                let baseline = self.area.center() + Offset::y(BUTTON_FONT.text_height() / 2);
                shape::Text::new(baseline, text, BUTTON_FONT)
                    .with_fg(style.text_color)
                    .with_align(Alignment::Center)
                    .render(target);
            }
            ButtonContent::Icon(icon) => {
                shape::ToifImage::new(self.area.center(), icon.toif)
                    .with_align(Alignment2D::CENTER)
                    .with_fg(style.icon_color)
                    .render(target);
            }
            ButtonContent::IconText(text, icon) => {
                // Vertically centered the same way as a one-line `Label`
                let font = BUTTON_FONT;
                let baseline = Point::new(
                    self.area.x0 + Self::ICON_SPACE,
                    self.area.y0
                        + (self.area.height() - font.text_height()) / 2
                        + font.text_max_height()
                        - font.text_baseline(),
                );
                shape::Text::new(baseline, text, font)
                    .with_fg(style.text_color)
                    .render(target);

                let icon_pos = Point::new(
                    self.area.x0 + (Self::ICON_SPACE + Self::ICON_MARGIN) / 2,
                    self.area.center().y,
                );
                shape::ToifImage::new(icon_pos, icon.toif)
                    .with_align(Alignment2D::CENTER)
                    .with_fg(style.icon_color)
                    .render(target);
            }
        }
    }
}
