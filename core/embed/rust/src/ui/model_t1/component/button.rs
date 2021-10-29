use crate::ui::{
    component::{Component, Event, EventCtx},
    display::{self, Color, Font},
    geometry::{Offset, Point, Rect},
};

use super::{
    event::{ButtonEvent, T1Button},
    theme,
};

pub enum ButtonMsg {
    Clicked,
}

#[derive(Copy, Clone)]
pub enum ButtonPos {
    Left,
    Right,
}

impl ButtonPos {
    fn hit(&self, b: &T1Button) -> bool {
        matches!(
            (self, b),
            (Self::Left, T1Button::Left) | (Self::Right, T1Button::Right)
        )
    }
}

pub struct Button<T> {
    area: Rect,
    pos: ButtonPos,
    baseline: Point,
    content: ButtonContent<T>,
    styles: ButtonStyleSheet,
    state: State,
}

impl<T: AsRef<[u8]>> Button<T> {
    pub fn new(
        area: Rect,
        pos: ButtonPos,
        content: ButtonContent<T>,
        styles: ButtonStyleSheet,
    ) -> Self {
        let (area, baseline) = Self::placement(area, pos, &content, &styles);
        Self {
            area,
            pos,
            baseline,
            content,
            styles,
            state: State::Released,
        }
    }

    pub fn with_text(area: Rect, pos: ButtonPos, text: T, styles: ButtonStyleSheet) -> Self {
        Self::new(area, pos, ButtonContent::Text(text), styles)
    }

    pub fn with_icon(
        area: Rect,
        pos: ButtonPos,
        image: &'static [u8],
        styles: ButtonStyleSheet,
    ) -> Self {
        Self::new(area, pos, ButtonContent::Icon(image), styles)
    }

    pub fn content(&self) -> &ButtonContent<T> {
        &self.content
    }

    fn style(&self) -> &ButtonStyle {
        match self.state {
            State::Released => self.styles.normal,
            State::Pressed => self.styles.active,
        }
    }

    fn set(&mut self, ctx: &mut EventCtx, state: State) {
        if self.state != state {
            self.state = state;
            ctx.request_paint();
        }
    }

    fn placement(
        area: Rect,
        pos: ButtonPos,
        content: &ButtonContent<T>,
        styles: &ButtonStyleSheet,
    ) -> (Rect, Point) {
        let border_width = if styles.normal.border_horiz { 2 } else { 0 };
        let content_width = match content {
            ButtonContent::Text(text) => display::text_width(text.as_ref(), styles.normal.font) - 1,
            ButtonContent::Icon(_icon) => todo!(),
        };
        let button_width = content_width + 2 * border_width;
        let area = match pos {
            ButtonPos::Left => area.vsplit(button_width).0,
            ButtonPos::Right => area.vsplit(-button_width).1,
        };

        let start_of_baseline = area.bottom_left() + Offset::new(border_width, -2);

        return (area, start_of_baseline);
    }
}

impl<T: AsRef<[u8]>> Component for Button<T> {
    type Msg = ButtonMsg;

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        match event {
            Event::Button(ButtonEvent::ButtonPressed(which)) if self.pos.hit(&which) => {
                self.set(ctx, State::Pressed);
            }
            Event::Button(ButtonEvent::ButtonReleased(which)) if self.pos.hit(&which) => {
                if matches!(self.state, State::Pressed) {
                    self.set(ctx, State::Released);
                    return Some(ButtonMsg::Clicked);
                }
            }
            _ => {}
        };
        None
    }

    fn paint(&mut self) {
        let style = self.style();

        match &self.content {
            ButtonContent::Text(text) => {
                let background_color = style.text_color.neg();
                if style.border_horiz {
                    display::rounded_rect1(self.area, background_color, theme::BG);
                } else {
                    display::rect(self.area, background_color)
                }

                display::text(
                    self.baseline,
                    text.as_ref(),
                    style.font,
                    style.text_color,
                    background_color,
                );
            }
            ButtonContent::Icon(_image) => {
                todo!();
            }
        }
    }
}

#[cfg(feature = "ui_debug")]
impl<T> crate::trace::Trace for Button<T>
where
    T: AsRef<[u8]> + crate::trace::Trace,
{
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.open("Button");
        match &self.content {
            ButtonContent::Text(text) => t.field("text", text),
            ButtonContent::Icon(_) => t.symbol("icon"),
        }
        t.close();
    }
}

#[derive(PartialEq, Eq)]
enum State {
    Released,
    Pressed,
}

pub enum ButtonContent<T> {
    Text(T),
    Icon(&'static [u8]),
}

pub struct ButtonStyleSheet {
    pub normal: &'static ButtonStyle,
    pub active: &'static ButtonStyle,
}

pub struct ButtonStyle {
    pub font: Font,
    pub text_color: Color,
    pub border_horiz: bool,
}
