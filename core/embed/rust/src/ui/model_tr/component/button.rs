use crate::ui::{
    component::{Component, Event, EventCtx},
    display::{self, Color, Font},
    event::{ButtonEvent, PhysicalButton},
    geometry::{Offset, Point, Rect},
};
use crate::time::Duration;

use heapless::String;

use super::theme;

#[derive(Eq, PartialEq)]
pub enum ButtonMsg {
    Clicked,
    LongPressed,
}

#[derive(Copy, Clone)]
pub enum ButtonPos {
    Left,
    Middle,
    Right,
}

impl ButtonPos {
    pub fn hit(&self, b: &PhysicalButton) -> bool {
        matches!(
            (self, b),
            (Self::Left, PhysicalButton::Left)
                | (Self::Middle, PhysicalButton::Both)
                | (Self::Right, PhysicalButton::Right)
        )
    }
}

pub struct Button<T> {
    bounds: Rect,
    pos: ButtonPos,
    content: ButtonContent<T>,
    styles: ButtonStyleSheet,
    state: State,
}

impl<T: AsRef<str>> Button<T> {
    pub fn new(pos: ButtonPos, content: ButtonContent<T>, styles: ButtonStyleSheet) -> Self {
        Self {
            pos,
            content,
            styles,
            bounds: Rect::zero(),
            state: State::Released,
        }
    }

    pub fn with_text(pos: ButtonPos, text: T, styles: ButtonStyleSheet) -> Self {
        Self::new(pos, ButtonContent::Text(text), styles)
    }

    pub fn with_icon(pos: ButtonPos, image: &'static [u8], styles: ButtonStyleSheet) -> Self {
        Self::new(pos, ButtonContent::Icon(image), styles)
    }

    pub fn content(&self) -> &ButtonContent<T> {
        &self.content
    }

    fn style(&self) -> ButtonStyle {
        match self.state {
            State::Released => self.styles.normal,
            State::Pressed => self.styles.active,
        }
    }

    /// Changing the icon content of the button.
    pub fn set_icon(&mut self, image: &'static [u8]) {
        self.content = ButtonContent::Icon(image);
    }

    /// Changing the text content of the button.
    pub fn set_text(&mut self, text: T) {
        self.content = ButtonContent::Text(text);
    }

    /// Changing the style of the button.
    pub fn set_style(&mut self, styles: ButtonStyleSheet) {
        self.styles = styles;
    }

    // Setting the visual state of the button.
    fn set(&mut self, ctx: &mut EventCtx, state: State) {
        if self.state != state {
            self.state = state;
            ctx.request_paint();
        }
    }

    // Setting the visual state of the button.
    pub fn set_pressed(&mut self, ctx: &mut EventCtx, is_pressed: bool) {
        let new_state = if is_pressed {
            State::Pressed
        } else {
            State::Released
        };
        self.set(ctx, new_state);
    }

    /// Return the full area of the button according
    /// to its current style, content and position.
    fn get_current_area(&self) -> Rect {
        let style = self.style();
        // Button width may be forced. Otherwise calculate it.
        let button_width = if let Some(width) = style.force_width {
            width
        } else {
            let outline = if style.with_outline {
                theme::BUTTON_OUTLINE
            } else {
                0
            };
            let content_width = match &self.content {
                ButtonContent::Text(text) => style.font.text_width(text.as_ref()) - 1,
                ButtonContent::Icon(icon) => display::toif_dimensions(icon, true).0 as i32 - 1,
            };
            content_width + 2 * outline
        };

        match self.pos {
            ButtonPos::Left => self.bounds.split_left(button_width).0,
            ButtonPos::Right => self.bounds.split_right(button_width).1,
            ButtonPos::Middle => self.bounds.split_center(button_width),
        }
    }

    /// Determine baseline point for the text.
    fn get_baseline(&self, style: &ButtonStyle) -> Point {
        // Arms and outline require the text to be elevated.
        if style.with_arms || style.with_outline {
            let offset = theme::BUTTON_OUTLINE;
            self.get_current_area().bottom_left() + Offset::new(offset, -offset)
        } else {
            self.get_current_area().bottom_left()
        }
    }
}

impl<T> Component for Button<T>
where
    T: AsRef<str>,
{
    type Msg = ButtonMsg;

    fn place(&mut self, bounds: Rect) -> Rect {
        self.bounds = bounds;
        self.get_current_area()
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        // Everything should be handled by `ButtonController`
        // TODO: could be completely deleted, but `ResultPopup` is using Button.event()
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
        let text_color = style.text_color;
        let background_color = text_color.negate();
        let area = self.get_current_area();

        // TODO: support another combinations of text and icons
        // - text with OK icon on left

        // Optionally display "arms" at both sides of content, or create
        // a nice rounded outline around it.
        // By default just fill the content background.
        if style.with_arms {
            // Prepare space for both the arms and content with BG color.
            // Arms are icons 10*6 pixels.
            let area_to_fill = area.extend_left(10).extend_right(15);
            display::rect_fill(area_to_fill, background_color);

            // Paint both arms.
            // TODO: for "CONFIRM" there is one space at the right, but for "SELECT" there are two
            let left_arm_center = area.left_center() - Offset::x(3) + Offset::y(3);
            let right_arm_center = area.right_center() + Offset::x(9) + Offset::y(3);
            display::icon(
                left_arm_center,
                theme::ICON_ARM_LEFT,
                text_color,
                background_color,
            );
            display::icon(
                right_arm_center,
                theme::ICON_ARM_RIGHT,
                text_color,
                background_color,
            );
        } else if style.with_outline {
            display::rect_outline_rounded2(area, text_color, background_color);
        } else {
            display::rect_fill(area, background_color)
        }

        match &self.content {
            ButtonContent::Text(text) => {
                display::text(
                    self.get_baseline(&style),
                    text.as_ref(),
                    style.font,
                    text_color,
                    background_color,
                );
            }
            ButtonContent::Icon(icon) => {
                // Accounting for the 8*8 icon with empty left column and bottom row.
                let icon_center = area.center() + Offset::uniform(1);
                display::icon(icon_center, icon, text_color, background_color);
            }
        }
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
    pub normal: ButtonStyle,
    pub active: ButtonStyle,
}

#[derive(Clone, Copy)]
pub struct ButtonStyle {
    pub font: Font,
    pub text_color: Color,
    pub with_outline: bool,
    pub with_arms: bool,
    pub force_width: Option<i32>,
}

// TODO: currently `button_default` and `button_cancel`
// are the same - decide whether to differentiate them.
// In Figma, they are not differentiated.

impl ButtonStyleSheet {
    pub fn new(
        normal_color: Color,
        active_color: Color,
        with_outline: bool,
        with_arms: bool,
        force_width: Option<i32>,
    ) -> Self {
        Self {
            normal: ButtonStyle {
                font: theme::FONT_BUTTON,
                text_color: normal_color,
                with_outline,
                with_arms,
                force_width,
            },
            active: ButtonStyle {
                font: theme::FONT_BUTTON,
                text_color: active_color,
                with_outline,
                with_arms,
                force_width,
            },
        }
    }

    // White text in normal mode.
    pub fn default(with_outline: bool, with_arms: bool, force_width: Option<i32>) -> Self {
        Self::new(theme::FG, theme::BG, with_outline, with_arms, force_width)
    }

    // Black text in normal mode.
    pub fn cancel(with_outline: bool, with_arms: bool, force_width: Option<i32>) -> Self {
        Self::new(theme::FG, theme::BG, with_outline, with_arms, force_width)
        // Self::new(theme::BG, theme::FG, with_outline, with_arms)
    }
}

/// Describing the button in the choice item.
#[derive(Debug, Clone, Copy)]
pub struct ButtonDetails<T> {
    pub text: Option<T>,
    pub icon: Option<&'static [u8]>,
    // TODO: `icon_text` is just hack so that we can instantiate
    // HoldToConfirm element when text is None.
    pub icon_text: Option<T>,
    pub duration: Option<Duration>,
    pub is_cancel: bool,
    pub with_outline: bool,
    pub with_arms: bool,
    pub force_width: Option<i32>,
}

impl<T: Clone + AsRef<str>> ButtonDetails<T> {
    /// Text button.
    pub fn new(text: T) -> Self {
        Self {
            text: Some(text),
            icon: None,
            icon_text: None,
            duration: None,
            is_cancel: false,
            with_outline: true,
            with_arms: false,
            force_width: None,
        }
    }

    /// Icon button.
    /// NOTE: `icon_text` needs to be specified, any text is enough.
    pub fn icon(icon: &'static [u8], icon_text: T) -> Self {
        Self {
            text: None,
            icon: Some(icon),
            icon_text: Some(icon_text),
            duration: None,
            is_cancel: false,
            with_outline: true,
            with_arms: false,
            force_width: None,
        }
    }

    /// Cancel style button.
    pub fn with_cancel(mut self) -> Self {
        self.is_cancel = true;
        self
    }

    /// No outline around the button.
    pub fn with_no_outline(mut self) -> Self {
        self.with_outline = false;
        self
    }

    /// Left and right "arms" around the button.
    /// Automatically disabling the outline.
    pub fn with_arms(mut self) -> Self {
        self.with_arms = true;
        self.with_outline = false;
        self
    }

    /// Duration of the hold-to-confirm.
    pub fn with_duration(mut self, duration: Duration) -> Self {
        self.duration = Some(duration);
        self
    }

    /// Width of the button.
    pub fn force_width(mut self, width: i32) -> Self {
        self.force_width = Some(width);
        self
    }

    /// Print attributes for debugging purposes.
    pub fn print(&self) {
        let text = if let Some(text) = self.text.clone() {
            String::<20>::from(text.as_ref())
        } else {
            String::<20>::from("None")
        };
        let icon_text = if let Some(icon_text) = self.icon_text.clone() {
            String::<20>::from(icon_text.as_ref())
        } else {
            String::<20>::from("None")
        };
        let force_width = if let Some(force_width) = self.force_width {
            String::<20>::from(inttostr!(force_width))
        } else {
            String::<20>::from("None")
        };
        println!(
            "ButtonDetails:: text: ",
            text.as_ref(),
            ", icon_text: ",
            icon_text.as_ref(),
            ", with_outline: ",
            booltostr!(self.with_outline),
            ", with_arms: ",
            booltostr!(self.with_arms),
            ", force_width: ",
            force_width.as_ref()
        );
    }

    /// Button style that should be applied.
    pub fn style(&self) -> ButtonStyleSheet {
        if self.is_cancel {
            ButtonStyleSheet::cancel(self.with_outline, self.with_arms, self.force_width)
        } else {
            ButtonStyleSheet::default(self.with_outline, self.with_arms, self.force_width)
        }
    }

    /// Identifier of this button configuration.
    /// To quickly compare two buttons and see if there was a change.
    pub fn id(&self) -> String<60> {
        // TODO: we could maybe use `Eq` or `PartialEq` for comparison,
        // but that wold require some generic Trait changes (T: PartialEq),
        // which was not possible for AsRef<str>?
        let text = if let Some(text) = self.text.clone() {
            String::<20>::from(text.as_ref())
        } else {
            String::<20>::from("")
        };
        // TODO: the icon should be hashed, icon size is not really good but works for now
        let icon_size = if let Some(icon) = self.icon {
            icon.len()
        } else {
            0
        };
        let duration_ms = self.duration.unwrap_or(Duration::ZERO).to_millis();
        build_string!(
            60,
            text.as_ref(),
            "--",
            String::<10>::from(icon_size as u32).as_ref(),
            "--",
            String::<20>::from(duration_ms).as_ref()
        )
    }
}

/// Holding the button details for all three possible buttons.
#[derive(Debug, Clone)]
pub struct ButtonLayout<T> {
    pub btn_left: Option<ButtonDetails<T>>,
    pub btn_middle: Option<ButtonDetails<T>>,
    pub btn_right: Option<ButtonDetails<T>>,
}

impl<T: AsRef<str>> ButtonLayout<T> {
    pub fn new(
        btn_left: Option<ButtonDetails<T>>,
        btn_middle: Option<ButtonDetails<T>>,
        btn_right: Option<ButtonDetails<T>>,
    ) -> Self {
        Self {
            btn_left,
            btn_middle,
            btn_right,
        }
    }

    /// Empty layout for when we cannot yet tell which buttons
    /// should be on the screen.
    pub fn empty() -> Self {
        Self::new(None, None, None)
    }
}

impl ButtonLayout<&'static str> {
    /// Custom texts for all three buttons.
    pub fn custom(left: &'static str, middle: &'static str, right: &'static str) -> Self {
        Self::new(
            Some(ButtonDetails::new(left)),
            Some(ButtonDetails::new(middle)),
            Some(ButtonDetails::new(right)),
        )
    }

    /// Default button layout for all three buttons.
    pub fn default_three() -> Self {
        Self::custom("<", "SELECT", ">")
    }

    /// Default button layout for all three buttons - icons.
    pub fn default_three_icons() -> Self {
        Self::three_icons_middle_text("SELECT")
    }

    /// Special middle text for default icon layout.
    pub fn three_icons_middle_text(middle_text: &'static str) -> Self {
        Self::new(
            Some(
                ButtonDetails::icon(Icon::new(theme::ICON_ARROW_LEFT, "arr_left"))
                    .with_no_outline(),
            ),
            Some(ButtonDetails::new(middle_text).with_arms()),
            Some(
                ButtonDetails::icon(Icon::new(theme::ICON_ARROW_RIGHT, "arr_right"))
                    .with_no_outline(),
            ),
        )
    }

    /// Just right and left, no middle.
    pub fn default_left_right() -> Self {
        Self::new(
            Some(ButtonDetails::new("<")),
            None,
            Some(ButtonDetails::new(">")),
        )
    }

    /// Setting a special middle text.
    pub fn special_middle(middle: &'static str) -> Self {
        Self::custom("<", middle, ">")
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_btn_details_id() {
        let btn = ButtonDetails::new("Test");
        assert_eq!(btn.id(), String::<50>::from("Test--0--0"));
        let btn = ButtonDetails::new("Duration").with_duration(Duration::from_secs(1));
        assert_eq!(btn.id(), String::<50>::from("Duration--0--1000"));
    }
}
