use crate::ui::{
    component::{Component, Event, EventCtx},
    display::{self, Color, Font, Icon},
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

    pub fn with_icon(pos: ButtonPos, image: Icon<T>, styles: ButtonStyleSheet) -> Self {
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
    pub fn set_icon(&mut self, image: Icon<T>) {
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
                ButtonContent::Icon(icon) => icon.width() - 1,
            };
            content_width + 2 * outline
        };

        // Button height may be adjusted for the icon without outline
        // Done to avoid highlighting bigger area than necessary when
        // drawing the icon in active (black on white) state
        let button_height = match &self.content {
            ButtonContent::Text(_) => theme::BUTTON_HEIGHT,
            ButtonContent::Icon(icon) => {
                if style.with_outline {
                    theme::BUTTON_HEIGHT
                } else {
                    icon.height()
                }
            }
        };

        let button_bounds = self.bounds.split_bottom(button_height).1;
        let area = match self.pos {
            ButtonPos::Left => button_bounds.split_left(button_width).0,
            ButtonPos::Right => button_bounds.split_right(button_width).1,
            ButtonPos::Middle => button_bounds.split_center(button_width).1,
        };

        // Allowing for possible offset of the area from current style
        if let Some(offset) = style.offset {
            area.translate(offset)
        } else {
            area
        }
    }

    /// Determine baseline point for the text.
    fn get_text_baseline(&self, style: &ButtonStyle) -> Point {
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
            // Baselines need to be shifted little bit right to fit properly with the text
            // TODO: for "CONFIRM" there is one space at the right, but for "SELECT" there are two
            Icon::new(theme::ICON_ARM_LEFT, "arm_left").draw_top_right(
                area.left_center() + Offset::x(2),
                text_color,
                background_color,
            );
            Icon::new(theme::ICON_ARM_RIGHT, "arm_right").draw_top_left(
                area.right_center() + Offset::x(4),
                text_color,
                background_color,
            );
        } else if style.with_outline {
            display::rect_outline_rounded(area, text_color, background_color, 2);
        } else {
            display::rect_fill(area, background_color)
        }

        match &self.content {
            ButtonContent::Text(text) => {
                display::text(
                    self.get_text_baseline(&style),
                    text.as_ref(),
                    style.font,
                    text_color,
                    background_color,
                );
            }
            ButtonContent::Icon(icon) => {
                if style.with_outline {
                    // Accounting for the 8*8 icon with empty left column and bottom row
                    // (which fits the outline nicely and symmetrically)
                    let center = area.center() + Offset::uniform(1);
                    icon.draw_center(center, text_color, background_color);
                } else {
                    // Positioning the icon in the corresponding corner/center
                    match self.pos {
                        ButtonPos::Left => {
                            icon.draw_bottom_left(area.bottom_left(), text_color, background_color)
                        }
                        ButtonPos::Right => icon.draw_bottom_right(
                            area.bottom_right(),
                            text_color,
                            background_color,
                        ),
                        ButtonPos::Middle => {
                            icon.draw_center(area.center(), text_color, background_color)
                        }
                    }
                }
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
    Icon(Icon<T>),
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
    pub offset: Option<Offset>,
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
        offset: Option<Offset>,
    ) -> Self {
        Self {
            normal: ButtonStyle {
                font: theme::FONT_BUTTON,
                text_color: normal_color,
                with_outline,
                with_arms,
                force_width,
                offset,
            },
            active: ButtonStyle {
                font: theme::FONT_BUTTON,
                text_color: active_color,
                with_outline,
                with_arms,
                force_width,
                offset,
            },
        }
    }

    // White text in normal mode.
    pub fn default(
        with_outline: bool,
        with_arms: bool,
        force_width: Option<i32>,
        offset: Option<Offset>,
    ) -> Self {
        Self::new(
            theme::FG,
            theme::BG,
            with_outline,
            with_arms,
            force_width,
            offset,
        )
    }

    // Black text in normal mode.
    pub fn cancel(
        with_outline: bool,
        with_arms: bool,
        force_width: Option<i32>,
        offset: Option<Offset>,
    ) -> Self {
        Self::new(
            theme::FG,
            theme::BG,
            with_outline,
            with_arms,
            force_width,
            offset,
        )
        // Self::new(theme::BG, theme::FG, with_outline, with_arms)
    }
}

/// Describing the button in the choice item.
#[derive(Debug, Clone, Copy)]
pub struct ButtonDetails<T> {
    pub text: Option<T>,
    pub icon: Option<Icon<T>>,
    pub duration: Option<Duration>,
    pub is_cancel: bool,
    pub with_outline: bool,
    pub with_arms: bool,
    pub force_width: Option<i32>,
    pub offset: Option<Offset>,
}

impl<T: Clone + AsRef<str>> ButtonDetails<T> {
    /// Text button.
    pub fn new(text: T) -> Self {
        Self {
            text: Some(text),
            icon: None,
            duration: None,
            is_cancel: false,
            with_outline: true,
            with_arms: false,
            force_width: None,
            offset: None,
        }
    }

    /// Icon button.
    pub fn icon(icon: Icon<T>) -> Self {
        Self {
            text: None,
            icon: Some(icon),
            duration: None,
            is_cancel: false,
            with_outline: true,
            with_arms: false,
            force_width: None,
            offset: None,
        }
    }

    /// Cross-style-icon cancel button with no outline.
    pub fn cancel_no_outline(text: T) -> Self {
        Self::icon(Icon::new(theme::ICON_CANCEL, text))
            .with_no_outline()
            .with_offset(Offset::new(2, -2))
    }

    // TODO: might do more constructors for other common buttons like above

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

    /// Positioning the icon precisely where we want.
    /// Buttons are by default placed exactly in the corners (left/right)
    /// or in the center in case of center button. The offset can change it.
    pub fn with_offset(mut self, offset: Offset) -> Self {
        self.offset = Some(offset);
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

    /// Button style that should be applied.
    pub fn style(&self) -> ButtonStyleSheet {
        if self.is_cancel {
            ButtonStyleSheet::cancel(
                self.with_outline,
                self.with_arms,
                self.force_width,
                self.offset,
            )
        } else {
            ButtonStyleSheet::default(
                self.with_outline,
                self.with_arms,
                self.force_width,
                self.offset,
            )
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
        let icon_size: String<10> = if let Some(icon) = &self.icon {
            build_string!(10, inttostr!(icon.width()), "x", inttostr!(icon.height()))
        } else {
            String::from("0x0")
        };
        let duration_ms = self.duration.unwrap_or(Duration::ZERO).to_millis();
        build_string!(
            60,
            text.as_ref(),
            "--",
            icon_size.as_ref(),
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
        assert_eq!(btn.id(), String::<50>::from("Test--0x0--0"));
        let btn = ButtonDetails::new("Duration").with_duration(Duration::from_secs(1));
        assert_eq!(btn.id(), String::<50>::from("Duration--0x0--1000"));
    }
}
