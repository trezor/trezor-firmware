use super::event::TouchEvent;
use crate::ui::{
    component::{Component, Event, EventCtx},
    display::{self, Color, Font},
    geometry::{Offset, Rect},
};

pub enum ButtonMsg {
    Clicked,
}

pub struct Button {
    area: Rect,
    content: ButtonContent,
    styles: ButtonStyleSheet,
    state: State,
}

impl Button {
    pub fn new(area: Rect, content: ButtonContent, styles: ButtonStyleSheet) -> Self {
        Self {
            area,
            content,
            styles,
            state: State::Initial,
        }
    }

    pub fn with_text(area: Rect, text: &'static [u8], styles: ButtonStyleSheet) -> Self {
        Self::new(area, ButtonContent::Text(text), styles)
    }

    pub fn with_icon(area: Rect, image: &'static [u8], styles: ButtonStyleSheet) -> Self {
        Self::new(area, ButtonContent::Icon(image), styles)
    }

    pub fn enable(&mut self, ctx: &mut EventCtx) {
        self.set(ctx, State::Initial)
    }

    pub fn disable(&mut self, ctx: &mut EventCtx) {
        self.set(ctx, State::Disabled)
    }

    pub fn is_enabled(&self) -> bool {
        matches!(
            self.state,
            State::Initial | State::Pressed | State::Released
        )
    }

    pub fn is_disabled(&self) -> bool {
        matches!(self.state, State::Disabled)
    }

    pub fn content(&self) -> &ButtonContent {
        &self.content
    }

    fn style(&self) -> &ButtonStyle {
        match self.state {
            State::Initial | State::Released => self.styles.normal,
            State::Pressed => self.styles.active,
            State::Disabled => self.styles.disabled,
        }
    }

    fn set(&mut self, ctx: &mut EventCtx, state: State) {
        if self.state != state {
            self.state = state;
            ctx.request_paint();
        }
    }
}

impl Component for Button {
    type Msg = ButtonMsg;

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        match event {
            Event::Touch(TouchEvent::TouchStart(pos)) => {
                match self.state {
                    State::Disabled => {
                        // Do nothing.
                    }
                    _ => {
                        // Touch started in our area, transform to `Pressed` state.
                        if self.area.contains(pos) {
                            self.set(ctx, State::Pressed);
                        }
                    }
                }
            }
            Event::Touch(TouchEvent::TouchMove(pos)) => {
                match self.state {
                    State::Released if self.area.contains(pos) => {
                        // Touch entered our area, transform to `Pressed` state.
                        self.set(ctx, State::Pressed);
                    }
                    State::Pressed if !self.area.contains(pos) => {
                        // Touch is leaving our area, transform to `Released` state.
                        self.set(ctx, State::Released);
                    }
                    _ => {
                        // Do nothing.
                    }
                }
            }
            Event::Touch(TouchEvent::TouchEnd(pos)) => {
                match self.state {
                    State::Initial | State::Disabled => {
                        // Do nothing.
                    }
                    State::Pressed if self.area.contains(pos) => {
                        // Touch finished in our area, we got clicked.
                        self.set(ctx, State::Initial);

                        return Some(ButtonMsg::Clicked);
                    }
                    _ => {
                        // Touch finished outside our area.
                        self.set(ctx, State::Initial);
                    }
                }
            }
            _ => {}
        };
        None
    }

    fn paint(&mut self) {
        let style = self.style();

        if style.border_width > 0 {
            // Paint the border and a smaller background on top of it.
            display::rounded_rect(
                self.area,
                style.border_color,
                style.background_color,
                style.border_radius,
            );
            display::rounded_rect(
                self.area.inset(style.border_width),
                style.button_color,
                style.border_color,
                style.border_radius,
            );
        } else {
            // We do not need to draw an explicit border in this case, just a
            // bigger background.
            display::rounded_rect(
                self.area,
                style.button_color,
                style.background_color,
                style.border_radius,
            );
        }

        match &self.content {
            ButtonContent::Text(text) => {
                let width = display::text_width(text, style.font);
                let height = display::text_height();
                let start_of_baseline = self.area.center() + Offset::new(-width / 2, height / 2);
                display::text(
                    start_of_baseline,
                    text,
                    style.font,
                    style.text_color,
                    style.button_color,
                );
            }
            ButtonContent::Icon(icon) => {
                display::icon(
                    self.area.center(),
                    icon,
                    style.text_color,
                    style.button_color,
                );
            }
        }
    }
}

#[cfg(feature = "ui_debug")]
impl crate::trace::Trace for Button {
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.open("Button");
        match self.content {
            ButtonContent::Text(text) => t.field("text", &text),
            ButtonContent::Icon(_) => t.symbol("icon"),
        }
        t.close();
    }
}

#[derive(PartialEq, Eq)]
enum State {
    Initial,
    Pressed,
    Released,
    Disabled,
}

pub enum ButtonContent {
    Text(&'static [u8]),
    Icon(&'static [u8]),
}

pub struct ButtonStyleSheet {
    pub normal: &'static ButtonStyle,
    pub active: &'static ButtonStyle,
    pub disabled: &'static ButtonStyle,
}

pub struct ButtonStyle {
    pub font: Font,
    pub text_color: Color,
    pub button_color: Color,
    pub background_color: Color,
    pub border_color: Color,
    pub border_radius: u8,
    pub border_width: i32,
}
