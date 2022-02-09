use crate::ui::{
    component::{Component, ComponentExt, Event, EventCtx, GridPlaced, Map},
    display::{self, Color, Font},
    geometry::{Insets, Offset, Rect},
};

use super::{event::TouchEvent, theme};

pub enum ButtonMsg {
    Pressed,
    Released,
    Clicked,
}

pub struct Button<T> {
    area: Rect,
    content: ButtonContent<T>,
    styles: ButtonStyleSheet,
    state: State,
}

impl<T> Button<T> {
    /// Standard height in pixels.
    pub const HEIGHT: i32 = 38;

    /// Offsets the baseline of the button text either up (negative) or down
    /// (positive).
    pub const BASELINE_OFFSET: i32 = -3;

    pub fn new(content: ButtonContent<T>) -> Self {
        Self {
            content,
            area: Rect::zero(),
            styles: theme::button_default(),
            state: State::Initial,
        }
    }

    pub fn with_text(text: T) -> Self {
        Self::new(ButtonContent::Text(text))
    }

    pub fn with_icon(image: &'static [u8]) -> Self {
        Self::new(ButtonContent::Icon(image))
    }

    pub fn empty() -> Self {
        Self::new(ButtonContent::Empty)
    }

    pub fn styled(mut self, styles: ButtonStyleSheet) -> Self {
        self.styles = styles;
        self
    }

    pub fn enable_if(&mut self, ctx: &mut EventCtx, enabled: bool) {
        if enabled {
            self.enable(ctx);
        } else {
            self.disable(ctx);
        }
    }

    pub fn initially_enabled(mut self, enabled: bool) -> Self {
        if !enabled {
            self.state = State::Disabled;
        }
        self
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

    pub fn set_content(&mut self, ctx: &mut EventCtx, content: ButtonContent<T>)
    where
        T: PartialEq,
    {
        if self.content != content {
            self.content = content;
            ctx.request_paint();
        }
    }

    pub fn content(&self) -> &ButtonContent<T> {
        &self.content
    }

    pub fn set_stylesheet(&mut self, ctx: &mut EventCtx, styles: ButtonStyleSheet) {
        if self.styles != styles {
            self.styles = styles;
            ctx.request_paint();
        }
    }

    pub fn style(&self) -> &ButtonStyle {
        match self.state {
            State::Initial | State::Released => self.styles.normal,
            State::Pressed => self.styles.active,
            State::Disabled => self.styles.disabled,
        }
    }

    pub fn area(&self) -> Rect {
        self.area
    }

    fn set(&mut self, ctx: &mut EventCtx, state: State) {
        if self.state != state {
            self.state = state;
            ctx.request_paint();
        }
    }

    pub fn paint_background(&self, style: &ButtonStyle) {
        if style.border_width > 0 {
            // Paint the border and a smaller background on top of it.
            display::rect_fill_rounded(
                self.area,
                style.border_color,
                style.background_color,
                style.border_radius,
            );
            display::rect_fill_rounded(
                self.area.inset(Insets::uniform(style.border_width)),
                style.button_color,
                style.border_color,
                style.border_radius,
            );
        } else {
            // We do not need to draw an explicit border in this case, just a
            // bigger background.
            display::rect_fill_rounded(
                self.area,
                style.button_color,
                style.background_color,
                style.border_radius,
            );
        }
    }

    pub fn paint_content(&self, style: &ButtonStyle)
    where
        T: AsRef<str>,
    {
        match &self.content {
            ButtonContent::Empty => {}
            ButtonContent::Text(text) => {
                let text = text.as_ref();
                let width = style.font.text_width(text);
                let height = style.font.text_height();
                let start_of_baseline = self.area.center()
                    + Offset::new(-width / 2, height / 2)
                    + Offset::y(Self::BASELINE_OFFSET);
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

impl<T> Component for Button<T>
where
    T: AsRef<str>,
{
    type Msg = ButtonMsg;

    fn place(&mut self, bounds: Rect) -> Rect {
        self.area = bounds;
        self.area
    }

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
                            return Some(ButtonMsg::Pressed);
                        }
                    }
                }
            }
            Event::Touch(TouchEvent::TouchMove(pos)) => {
                match self.state {
                    State::Released if self.area.contains(pos) => {
                        // Touch entered our area, transform to `Pressed` state.
                        self.set(ctx, State::Pressed);
                        return Some(ButtonMsg::Pressed);
                    }
                    State::Pressed if !self.area.contains(pos) => {
                        // Touch is leaving our area, transform to `Released` state.
                        self.set(ctx, State::Released);
                        return Some(ButtonMsg::Released);
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
        self.paint_background(&style);
        self.paint_content(&style);
    }

    fn bounds(&self, sink: &mut dyn FnMut(Rect)) {
        sink(self.area);
    }
}

#[cfg(feature = "ui_debug")]
impl<T> crate::trace::Trace for Button<T>
where
    T: AsRef<str> + crate::trace::Trace,
{
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.open("Button");
        match &self.content {
            ButtonContent::Empty => {}
            ButtonContent::Text(text) => t.field("text", text),
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

#[derive(PartialEq, Eq)]
pub enum ButtonContent<T> {
    Empty,
    Text(T),
    Icon(&'static [u8]),
}

#[derive(PartialEq, Eq)]
pub struct ButtonStyleSheet {
    pub normal: &'static ButtonStyle,
    pub active: &'static ButtonStyle,
    pub disabled: &'static ButtonStyle,
}

#[derive(PartialEq, Eq)]
pub struct ButtonStyle {
    pub font: Font,
    pub text_color: Color,
    pub button_color: Color,
    pub background_color: Color,
    pub border_color: Color,
    pub border_radius: u8,
    pub border_width: i32,
}

impl<T> Button<T> {
    pub fn left_right<F0, F1, R>(
        left: Button<T>,
        left_map: F0,
        right: Button<T>,
        right_map: F1,
    ) -> (Map<GridPlaced<Self>, F0>, Map<GridPlaced<Self>, F1>)
    where
        F0: Fn(ButtonMsg) -> Option<R>,
        F1: Fn(ButtonMsg) -> Option<R>,
        T: AsRef<str>,
    {
        const BUTTON_SPACING: i32 = 6;
        (
            GridPlaced::new(left)
                .with_grid(1, 3)
                .with_spacing(BUTTON_SPACING)
                .with_row_col(0, 0)
                .map(left_map),
            GridPlaced::new(right)
                .with_grid(1, 3)
                .with_spacing(BUTTON_SPACING)
                .with_from_to((0, 1), (0, 2))
                .map(right_map),
        )
    }
}
