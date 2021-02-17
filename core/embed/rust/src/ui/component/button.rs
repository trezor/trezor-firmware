use crate::ui::math::{Offset, Point, Rect};
use crate::ui::{display, math::Color};

use super::component::{Component, Event, EventCtx, Widget};

pub enum ButtonMsg {
    Clicked,
}

pub struct Button {
    widget: Widget,
    content: ButtonContent,
    styles: ButtonStyleSheet,
    state: State,
}

impl Button {
    pub fn new(area: Rect, content: ButtonContent, styles: ButtonStyleSheet) -> Self {
        Self {
            widget: Widget::new(area),
            content,
            styles,
            state: State::Initial,
        }
    }

    pub fn with_text(area: Rect, text: &'static [u8], styles: ButtonStyleSheet) -> Self {
        Self::new(area, ButtonContent::Text(text), styles)
    }

    pub fn with_image(area: Rect, image: &'static [u8], styles: ButtonStyleSheet) -> Self {
        Self::new(area, ButtonContent::Image(image), styles)
    }

    pub fn enable(&mut self) {
        self.set(State::Initial);
    }

    pub fn disable(&mut self) {
        self.set(State::Disabled);
    }

    pub fn is_disabled(&self) -> bool {
        matches!(self.state, State::Disabled)
    }

    pub fn content(&self) -> &ButtonContent {
        &self.content
    }

    fn style(&self) -> &ButtonStyle {
        match self.state {
            State::Initial | State::Released => &self.styles.normal,
            State::Pressed => &self.styles.active,
            State::Disabled => &self.styles.disabled,
        }
    }

    fn set(&mut self, state: State) {
        if self.state != state {
            self.state = state;
            self.request_paint();
        }
    }
}

impl Component for Button {
    type Msg = ButtonMsg;

    fn widget(&mut self) -> &mut Widget {
        &mut self.widget
    }

    fn event(&mut self, _ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        match event {
            Event::TouchStart(pos) => {
                match self.state {
                    State::Disabled => {
                        // Do nothing.
                    }
                    _ => {
                        if self.area().contains(pos) {
                            self.set(State::Pressed);
                        }
                    }
                }
            }
            Event::TouchMove(pos) => {
                let area = self.area();
                match self.state {
                    State::Released if area.contains(pos) => {
                        // Touch entered our area, transform to `Pressed` state.
                        self.set(State::Pressed);
                    }
                    State::Pressed if !area.contains(pos) => {
                        // Touch is leaving our area, transform to `Released` state.
                        self.set(State::Released);
                    }
                    _ => {
                        // Do nothing.
                    }
                }
            }
            Event::TouchEnd(pos) => {
                let area = self.area();
                match self.state {
                    State::Initial | State::Disabled => {
                        // Do nothing.
                    }
                    State::Pressed if area.contains(pos) => {
                        // Touch finished in our area, we got clicked.
                        self.set(State::Initial);
                        return Some(ButtonMsg::Clicked);
                    }
                    _ => {
                        // Touch finished outside our area.
                        self.set(State::Initial);
                    }
                }
            }
            _ => {}
        };
        None
    }

    fn paint(&mut self) {
        let area = self.area();
        let style = self.style();

        if style.border_width > 0 {
            // Paint the border and a smaller background on top of it.
            display::rounded_rect(
                area,
                style.border_color,
                style.background_color,
                style.border_radius,
            );
            display::rounded_rect(
                area.inset(style.border_width),
                style.button_color,
                style.border_color,
                style.border_radius,
            );
        } else {
            // We do not need to draw an explicit border in this case, just a
            // bigger background.
            display::rounded_rect(
                area,
                style.button_color,
                style.background_color,
                style.border_radius,
            );
        }

        match &self.content {
            ButtonContent::Text(text) => {
                let width = display::text_width(text, style.font);
                let height = display::text_height();
                let start_of_baseline = area.midpoint() + Offset::new(-width / 2, height / 2);
                display::text(
                    start_of_baseline,
                    text,
                    style.font,
                    style.text_color,
                    style.button_color,
                );
            }
            ButtonContent::Image(image) => {
                todo!();
            }
        }
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
    Image(&'static [u8]),
}

pub struct ButtonStyleSheet {
    pub normal: &'static ButtonStyle,
    pub active: &'static ButtonStyle,
    pub disabled: &'static ButtonStyle,
}

pub struct ButtonStyle {
    pub font: i32,
    pub text_color: Color,
    pub button_color: Color,
    pub background_color: Color,
    pub border_color: Color,
    pub border_radius: u8,
    pub border_width: i32,
}
