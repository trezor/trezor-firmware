use crate::{
    strutil::StringType,
    time::Duration,
    ui::{
        component::{Component, Event, EventCtx, Never},
        constant,
        display::{self, Color, Font, Icon},
        geometry::{Alignment2D, Insets, Offset, Point, Rect},
    },
};

use super::{loader::DEFAULT_DURATION_MS, theme};

const HALF_SCREEN_BUTTON_WIDTH: i16 = constant::WIDTH / 2 - 1;

#[derive(Copy, Clone)]
pub enum ButtonPos {
    Left,
    Middle,
    Right,
}

pub struct Button<T>
where
    T: StringType,
{
    bounds: Rect,
    pos: ButtonPos,
    content: ButtonContent<T>,
    styles: ButtonStyleSheet,
    state: State,
}

impl<T> Button<T>
where
    T: StringType,
{
    pub fn new(pos: ButtonPos, content: ButtonContent<T>, styles: ButtonStyleSheet) -> Self {
        Self {
            pos,
            content,
            styles,
            bounds: Rect::zero(),
            state: State::Released,
        }
    }

    pub fn from_button_details(pos: ButtonPos, btn_details: ButtonDetails<T>) -> Self {
        // Deciding between text and icon
        let style = btn_details.style();
        match btn_details.content {
            ButtonContent::Text(text) => Self::with_text(pos, text, style),
            ButtonContent::Icon(icon) => Self::with_icon(pos, icon, style),
        }
    }

    pub fn with_text(pos: ButtonPos, text: T, styles: ButtonStyleSheet) -> Self {
        Self::new(pos, ButtonContent::Text(text), styles)
    }

    pub fn with_icon(pos: ButtonPos, image: Icon, styles: ButtonStyleSheet) -> Self {
        Self::new(pos, ButtonContent::Icon(image), styles)
    }

    pub fn content(&self) -> &ButtonContent<T> {
        &self.content
    }

    fn style(&self) -> &ButtonStyle {
        match self.state {
            State::Released => &self.styles.normal,
            State::Pressed => &self.styles.active,
        }
    }

    /// Changing the icon content of the button.
    pub fn set_icon(&mut self, image: Icon) {
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
        let button_width = if let Some(width) = style.fixed_width {
            width
        } else {
            let outline = if style.with_outline {
                theme::BUTTON_OUTLINE
            } else {
                0
            };
            let content_width = match &self.content {
                ButtonContent::Text(text) => style.font.visible_text_width(text.as_ref()),
                ButtonContent::Icon(icon) => icon.toif.width(),
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
                    icon.toif.height()
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
        area.translate(style.offset)
    }

    /// Determine baseline point for the text.
    fn get_text_baseline(&self, style: &ButtonStyle) -> Point {
        // Arms and outline require the text to be elevated.
        let offset_y = if style.with_arms {
            theme::BUTTON_ARMS
        } else if style.with_outline {
            theme::BUTTON_OUTLINE
        } else {
            0
        };

        let offset_x = if style.with_outline {
            theme::BUTTON_OUTLINE
        } else {
            0
        };

        self.get_current_area().bottom_left() + Offset::new(offset_x, -offset_y)
    }
}

impl<T> Component for Button<T>
where
    T: StringType,
{
    type Msg = Never;

    fn place(&mut self, bounds: Rect) -> Rect {
        self.bounds = bounds;
        self.get_current_area()
    }

    fn event(&mut self, _ctx: &mut EventCtx, _event: Event) -> Option<Self::Msg> {
        // Events are handled by `ButtonController`
        None
    }

    fn paint(&mut self) {
        let style = self.style();
        let text_color = style.text_color;
        let background_color = text_color.negate();
        let mut area = self.get_current_area();

        // Optionally display "arms" at both sides of content, or create
        // a nice rounded outline around it.
        // By default just fill the content background.
        if style.with_arms {
            const ARM_WIDTH: i16 = 15;
            area = area.translate(Offset::y(1));

            // Prepare space for both the arms and content with BG color.
            // Arms are icons 10*6 pixels.
            let area_to_fill = area.outset(Insets::sides(ARM_WIDTH));
            display::rect_fill(area_to_fill, background_color);
            display::rect_fill_corners(area_to_fill, theme::BG);

            // Paint both arms.
            // Baselines are adjusted to give space between text and icon.
            // 2 px because 1px might lead to odd coordinate which can't be render
            theme::ICON_ARM_LEFT.draw(
                area.left_center() - Offset::x(2),
                Alignment2D::TOP_RIGHT,
                text_color,
                background_color,
            );
            theme::ICON_ARM_RIGHT.draw(
                area.right_center() + Offset::x(2),
                Alignment2D::TOP_LEFT,
                text_color,
                background_color,
            );
        } else if style.with_outline {
            if background_color == theme::BG {
                display::rect_outline_rounded(area, text_color, background_color, 2);
            } else {
                // With inverse colors having just radius of one, `rect_outline_rounded`
                // is not suitable for inverse colors.
                display::rect_fill(area, background_color);
                display::rect_fill_corners(area, theme::BG);
            }
        } else {
            display::rect_fill(area, background_color);
        }

        match &self.content {
            ButtonContent::Text(text) => {
                display::text_left(
                    self.get_text_baseline(style)
                        - Offset::x(style.font.start_x_bearing(text.as_ref())),
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
                    icon.draw(center, Alignment2D::CENTER, text_color, background_color);
                } else {
                    // Positioning the icon in the corresponding corner/center
                    match self.pos {
                        ButtonPos::Left => icon.draw(
                            area.bottom_left(),
                            Alignment2D::BOTTOM_LEFT,
                            text_color,
                            background_color,
                        ),
                        ButtonPos::Right => icon.draw(
                            area.bottom_right(),
                            Alignment2D::BOTTOM_RIGHT,
                            text_color,
                            background_color,
                        ),
                        ButtonPos::Middle => icon.draw(
                            area.center(),
                            Alignment2D::CENTER,
                            text_color,
                            background_color,
                        ),
                    }
                }
            }
        }
    }
}

#[derive(PartialEq, Eq)]
enum State {
    Released,
    Pressed,
}

#[derive(Clone)]
pub enum ButtonContent<T> {
    Text(T),
    Icon(Icon),
}

pub struct ButtonStyleSheet {
    pub normal: ButtonStyle,
    pub active: ButtonStyle,
}

pub struct ButtonStyle {
    pub font: Font,
    pub text_color: Color,
    pub with_outline: bool,
    pub with_arms: bool,
    pub fixed_width: Option<i16>,
    pub offset: Offset,
}

impl ButtonStyleSheet {
    pub fn new(
        normal_color: Color,
        active_color: Color,
        with_outline: bool,
        with_arms: bool,
        fixed_width: Option<i16>,
        offset: Offset,
    ) -> Self {
        Self {
            normal: ButtonStyle {
                font: theme::FONT_BUTTON,
                text_color: normal_color,
                with_outline,
                with_arms,
                fixed_width,
                offset,
            },
            active: ButtonStyle {
                font: theme::FONT_BUTTON,
                text_color: active_color,
                with_outline,
                with_arms,
                fixed_width,
                offset,
            },
        }
    }

    // White text in normal mode.
    pub fn default(
        with_outline: bool,
        with_arms: bool,
        fixed_width: Option<i16>,
        offset: Offset,
    ) -> Self {
        Self::new(
            theme::FG,
            theme::BG,
            with_outline,
            with_arms,
            fixed_width,
            offset,
        )
    }
}

/// Describing the button on the screen - only visuals.
#[derive(Clone)]
pub struct ButtonDetails<T> {
    pub content: ButtonContent<T>,
    pub duration: Option<Duration>,
    with_outline: bool,
    with_arms: bool,
    fixed_width: Option<i16>,
    offset: Offset,
}

impl<T> ButtonDetails<T> {
    /// Text button.
    pub fn text(text: T) -> Self {
        Self {
            content: ButtonContent::Text(text),
            duration: None,
            with_outline: true,
            with_arms: false,
            fixed_width: None,
            offset: Offset::zero(),
        }
    }

    /// Icon button.
    pub fn icon(icon: Icon) -> Self {
        Self {
            content: ButtonContent::Icon(icon),
            duration: None,
            with_outline: true,
            with_arms: false,
            fixed_width: None,
            offset: Offset::zero(),
        }
    }

    /// Text with arms signalling double press.
    pub fn armed_text(text: T) -> Self {
        Self::text(text).with_arms()
    }

    /// Cross-style-icon cancel button with no outline.
    pub fn cancel_icon() -> Self {
        Self::icon(theme::ICON_CANCEL)
            .with_no_outline()
            .with_offset(Offset::new(2, -2))
    }

    /// Left arrow to signal going back. No outline.
    pub fn left_arrow_icon() -> Self {
        Self::icon(theme::ICON_ARROW_LEFT)
            .with_no_outline()
            .with_offset(Offset::new(1, -1))
    }

    /// Right arrow to signal going forward. No outline.
    pub fn right_arrow_icon() -> Self {
        Self::icon(theme::ICON_ARROW_RIGHT)
            .with_no_outline()
            .with_offset(Offset::new(-1, -1))
    }

    /// Up arrow to signal paginating back. No outline. Offsetted little right
    /// to not be on the boundary.
    pub fn up_arrow_icon() -> Self {
        Self::icon(theme::ICON_ARROW_UP)
            .with_no_outline()
            .with_offset(Offset::new(2, -3))
    }

    /// Down arrow to signal paginating forward. Takes half the screen's width
    pub fn down_arrow_icon_wide() -> Self {
        Self::icon(theme::ICON_ARROW_DOWN).with_fixed_width(HALF_SCREEN_BUTTON_WIDTH)
    }

    /// Up arrow to signal paginating back. Takes half the screen's width
    pub fn up_arrow_icon_wide() -> Self {
        Self::icon(theme::ICON_ARROW_UP).with_fixed_width(HALF_SCREEN_BUTTON_WIDTH)
    }

    /// Icon of a bin to signal deleting.
    pub fn bin_icon() -> Self {
        Self::icon(theme::ICON_BIN).with_no_outline()
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
        self.offset = offset;
        self
    }

    /// Left and right "arms" around the button.
    /// Automatically disabling the outline.
    pub fn with_arms(mut self) -> Self {
        self.with_arms = true;
        self.with_outline = false;
        self
    }

    /// Default duration of the hold-to-confirm - 1 second.
    pub fn with_default_duration(mut self) -> Self {
        self.duration = Some(Duration::from_millis(DEFAULT_DURATION_MS));
        self
    }

    /// Specific duration of the hold-to-confirm.
    pub fn with_duration(mut self, duration: Duration) -> Self {
        self.duration = Some(duration);
        self
    }

    /// Specifying the width of the button.
    pub fn with_fixed_width(mut self, width: i16) -> Self {
        self.fixed_width = Some(width);
        self
    }

    /// Button style that should be applied.
    pub fn style(&self) -> ButtonStyleSheet {
        ButtonStyleSheet::default(
            self.with_outline,
            self.with_arms,
            self.fixed_width,
            self.offset,
        )
    }
}

/// Holding the button details for all three possible buttons.
#[derive(Clone)]
pub struct ButtonLayout<T> {
    pub btn_left: Option<ButtonDetails<T>>,
    pub btn_middle: Option<ButtonDetails<T>>,
    pub btn_right: Option<ButtonDetails<T>>,
}

impl<T> ButtonLayout<T>
where
    T: StringType,
{
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

    /// Default button layout for all three buttons - icons.
    pub fn default_three_icons() -> Self {
        Self::arrow_armed_arrow("SELECT".into())
    }

    /// Special middle text for default icon layout.
    pub fn arrow_armed_arrow(text: T) -> Self {
        Self::new(
            Some(ButtonDetails::left_arrow_icon()),
            Some(ButtonDetails::armed_text(text)),
            Some(ButtonDetails::right_arrow_icon()),
        )
    }

    /// Left cancel, armed text and next right arrow.
    pub fn cancel_armed_arrow(text: T) -> Self {
        Self::new(
            Some(ButtonDetails::cancel_icon()),
            Some(ButtonDetails::armed_text(text)),
            Some(ButtonDetails::right_arrow_icon()),
        )
    }

    /// Middle armed text and next right arrow.
    pub fn none_armed_arrow(text: T) -> Self {
        Self::new(
            None,
            Some(ButtonDetails::armed_text(text)),
            Some(ButtonDetails::right_arrow_icon()),
        )
    }

    /// Left cancel, armed text and right text.
    pub fn cancel_armed_text(middle: T, right: T) -> Self {
        Self::new(
            Some(ButtonDetails::cancel_icon()),
            Some(ButtonDetails::armed_text(middle)),
            Some(ButtonDetails::text(right)),
        )
    }

    /// Left back arrow and middle armed text.
    pub fn arrow_armed_none(text: T) -> Self {
        Self::new(
            Some(ButtonDetails::left_arrow_icon()),
            Some(ButtonDetails::armed_text(text)),
            None,
        )
    }

    /// Left and right texts.
    pub fn text_none_text(left: T, right: T) -> Self {
        Self::new(
            Some(ButtonDetails::text(left)),
            None,
            Some(ButtonDetails::text(right)),
        )
    }

    /// Left text and right arrow.
    pub fn text_none_arrow(text: T) -> Self {
        Self::new(
            Some(ButtonDetails::text(text)),
            None,
            Some(ButtonDetails::right_arrow_icon()),
        )
    }

    /// Only right text.
    pub fn none_none_text(text: T) -> Self {
        Self::new(None, None, Some(ButtonDetails::text(text)))
    }

    /// Left and right arrow icons for navigation.
    pub fn arrow_none_arrow() -> Self {
        Self::new(
            Some(ButtonDetails::left_arrow_icon()),
            None,
            Some(ButtonDetails::right_arrow_icon()),
        )
    }

    /// Left arrow and right text.
    pub fn arrow_none_text(text: T) -> Self {
        Self::new(
            Some(ButtonDetails::left_arrow_icon()),
            None,
            Some(ButtonDetails::text(text)),
        )
    }

    /// Up arrow left and right text.
    pub fn up_arrow_none_text(text: T) -> Self {
        Self::new(
            Some(ButtonDetails::up_arrow_icon()),
            None,
            Some(ButtonDetails::text(text)),
        )
    }

    /// Cancel cross on left and right arrow.
    pub fn cancel_none_arrow() -> Self {
        Self::new(
            Some(ButtonDetails::cancel_icon()),
            None,
            Some(ButtonDetails::right_arrow_icon()),
        )
    }

    /// Cancel cross on left and right arrow facing down.
    pub fn cancel_none_arrow_wide() -> Self {
        Self::new(
            Some(ButtonDetails::cancel_icon()),
            None,
            Some(ButtonDetails::down_arrow_icon_wide()),
        )
    }

    /// Cancel cross on left and right arrow facing down.
    pub fn cancel_none_arrow_down() -> Self {
        Self::new(
            Some(ButtonDetails::cancel_icon()),
            None,
            Some(ButtonDetails::down_arrow_icon_wide()),
        )
    }

    /// Cancel cross on left and text on the right.
    pub fn cancel_none_text(text: T) -> Self {
        Self::new(
            Some(ButtonDetails::cancel_icon()),
            None,
            Some(ButtonDetails::text(text)),
        )
    }

    /// Cancel cross on left and hold-to-confirm text on the right.
    pub fn cancel_none_htc(text: T) -> Self {
        Self::new(
            Some(ButtonDetails::cancel_icon()),
            None,
            Some(ButtonDetails::text(text).with_default_duration()),
        )
    }

    /// Arrow back on left and hold-to-confirm text on the right.
    pub fn arrow_none_htc(text: T) -> Self {
        Self::new(
            Some(ButtonDetails::left_arrow_icon()),
            None,
            Some(ButtonDetails::text(text).with_default_duration()),
        )
    }

    /// Only armed text in the middle.
    pub fn none_armed_none(text: T) -> Self {
        Self::new(None, Some(ButtonDetails::armed_text(text)), None)
    }

    /// HTC on both sides.
    pub fn htc_none_htc(left: T, right: T) -> Self {
        Self::new(
            Some(ButtonDetails::text(left).with_default_duration()),
            None,
            Some(ButtonDetails::text(right).with_default_duration()),
        )
    }

    /// Only left arrow.
    pub fn arrow_none_none() -> Self {
        Self::new(Some(ButtonDetails::left_arrow_icon()), None, None)
    }

    /// Only right arrow facing down.
    pub fn none_none_arrow_wide() -> Self {
        Self::new(None, None, Some(ButtonDetails::down_arrow_icon_wide()))
    }
}

/// What happens when a button is triggered.
/// Theoretically any action can be connected
/// with any button.
#[derive(Clone, PartialEq, Eq, Copy)]
pub enum ButtonAction {
    /// Go to the next page of this flow
    NextPage,
    /// Go to the previous page of this flow
    PrevPage,
    /// Go to the first page of this flow
    FirstPage,
    /// Go to the last page of this flow
    LastPage,
    /// Cancel the whole layout - send Msg::Cancelled
    Cancel,
    /// Confirm the whole layout - send Msg::Confirmed
    Confirm,
    /// Send INFO message from layout - send Msg::Info
    Info,
}

/// Storing actions for all three possible buttons.
#[derive(Clone, Copy)]
pub struct ButtonActions {
    pub left: Option<ButtonAction>,
    pub middle: Option<ButtonAction>,
    pub right: Option<ButtonAction>,
}

impl ButtonActions {
    pub const fn new(
        left: Option<ButtonAction>,
        middle: Option<ButtonAction>,
        right: Option<ButtonAction>,
    ) -> Self {
        Self {
            left,
            middle,
            right,
        }
    }

    /// Going back with left, going further with right
    pub fn prev_none_next() -> Self {
        Self::new(
            Some(ButtonAction::PrevPage),
            None,
            Some(ButtonAction::NextPage),
        )
    }

    /// Going back with left, going further with middle
    pub fn prev_next_none() -> Self {
        Self::new(
            Some(ButtonAction::PrevPage),
            Some(ButtonAction::NextPage),
            None,
        )
    }

    /// Previous with left, confirming with right
    pub fn prev_none_confirm() -> Self {
        Self::new(
            Some(ButtonAction::PrevPage),
            None,
            Some(ButtonAction::Confirm),
        )
    }

    /// Previous with left, confirming with middle
    pub fn prev_confirm_none() -> Self {
        Self::new(
            Some(ButtonAction::PrevPage),
            Some(ButtonAction::Confirm),
            None,
        )
    }

    /// Going to last page with left, to the next page with right
    pub fn last_none_next() -> Self {
        Self::new(
            Some(ButtonAction::LastPage),
            None,
            Some(ButtonAction::NextPage),
        )
    }

    /// Going to last page with left, to the next page with right and confirm
    /// with middle
    pub fn last_confirm_next() -> Self {
        Self::new(
            Some(ButtonAction::LastPage),
            Some(ButtonAction::Confirm),
            Some(ButtonAction::NextPage),
        )
    }

    /// Going to previous page with left, to the next page with right and
    /// confirm with middle
    pub fn prev_confirm_next() -> Self {
        Self::new(
            Some(ButtonAction::PrevPage),
            Some(ButtonAction::Confirm),
            Some(ButtonAction::NextPage),
        )
    }

    /// Cancelling with left, going to the next page with right
    pub fn cancel_none_next() -> Self {
        Self::new(
            Some(ButtonAction::Cancel),
            None,
            Some(ButtonAction::NextPage),
        )
    }

    /// Only going to the next page with right
    pub fn none_none_next() -> Self {
        Self::new(None, None, Some(ButtonAction::NextPage))
    }

    /// Only going to the prev page with left
    pub fn prev_none_none() -> Self {
        Self::new(Some(ButtonAction::PrevPage), None, None)
    }

    /// Cancelling with left, confirming with right
    pub fn cancel_none_confirm() -> Self {
        Self::new(
            Some(ButtonAction::Cancel),
            None,
            Some(ButtonAction::Confirm),
        )
    }

    /// Cancelling with left, confirming with middle and next with right
    pub fn cancel_confirm_next() -> Self {
        Self::new(
            Some(ButtonAction::Cancel),
            Some(ButtonAction::Confirm),
            Some(ButtonAction::NextPage),
        )
    }

    /// Cancelling with left, confirming with middle and info with right
    pub fn cancel_confirm_info() -> Self {
        Self::new(
            Some(ButtonAction::Cancel),
            Some(ButtonAction::Confirm),
            Some(ButtonAction::Info),
        )
    }

    /// Going to the beginning with left, confirming with right
    pub fn beginning_none_confirm() -> Self {
        Self::new(
            Some(ButtonAction::FirstPage),
            None,
            Some(ButtonAction::Confirm),
        )
    }

    /// Going to the beginning with left, cancelling with right
    pub fn beginning_none_cancel() -> Self {
        Self::new(
            Some(ButtonAction::FirstPage),
            None,
            Some(ButtonAction::Cancel),
        )
    }

    /// Having access to appropriate action based on the `ButtonPos`
    pub fn get_action(&self, pos: ButtonPos) -> Option<ButtonAction> {
        match pos {
            ButtonPos::Left => self.left,
            ButtonPos::Middle => self.middle,
            ButtonPos::Right => self.right,
        }
    }
}

// DEBUG-ONLY SECTION BELOW

#[cfg(feature = "ui_debug")]
use crate::strutil::ShortString;

#[cfg(feature = "ui_debug")]
impl<T: StringType> crate::trace::Trace for Button<T> {
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.component("Button");
        match &self.content {
            ButtonContent::Text(text) => t.string("text", text.as_ref()),
            ButtonContent::Icon(icon) => {
                t.null("text");
                t.string("icon", icon.name);
            }
        }
    }
}

#[cfg(feature = "ui_debug")]
impl<T: StringType> crate::trace::Trace for ButtonDetails<T> {
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.component("ButtonDetails");
        match &self.content {
            ButtonContent::Text(text) => {
                t.string("text", text.as_ref());
            }
            ButtonContent::Icon(icon) => {
                t.null("text");
                t.string("icon", icon.name);
            }
        }
        if let Some(duration) = &self.duration {
            t.int("hold_to_confirm", duration.to_millis() as i64);
        }
    }
}

#[cfg(feature = "ui_debug")]
impl ButtonAction {
    /// Describing the action as a string. Debug-only.
    pub fn string(&self) -> ShortString {
        match self {
            ButtonAction::NextPage => "Next".into(),
            ButtonAction::PrevPage => "Prev".into(),
            ButtonAction::FirstPage => "First".into(),
            ButtonAction::LastPage => "Last".into(),
            ButtonAction::Cancel => "Cancel".into(),
            ButtonAction::Confirm => "Confirm".into(),
            ButtonAction::Info => "Info".into(),
        }
    }
}
