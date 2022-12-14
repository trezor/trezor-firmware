use crate::{
    time::Duration,
    ui::{
        component::{Component, Event, EventCtx},
        constant,
        display::{self, Color, Font, Icon},
        event::{ButtonEvent, PhysicalButton},
        geometry::{Offset, Point, Rect},
    },
};

use heapless::String;

use super::theme;

const HALF_SCREEN_BUTTON_WIDTH: i16 = constant::WIDTH / 2 - 1;

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

    pub fn with_icon(pos: ButtonPos, image: Icon, styles: ButtonStyleSheet) -> Self {
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
        let offset_y = if style.with_arms || style.with_outline {
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
            let area_to_fill = area.extend_left(15).extend_right(15);
            display::rect_fill(area_to_fill, background_color);

            // Paint both arms.
            // Baselines are adjusted to give space between text and icon.
            // 2 px because 1px might lead to odd coordinate which can't be render
            Icon::new(theme::ICON_ARM_LEFT).draw_top_right(
                area.left_center() + Offset::x(-2),
                text_color,
                background_color,
            );
            Icon::new(theme::ICON_ARM_RIGHT).draw_top_left(
                area.right_center() + Offset::x(2),
                text_color,
                background_color,
            );
            display::rect_fill_corners(area_to_fill, theme::BG);
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
            ButtonContent::Icon(icon) => t.field("icon", icon),
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
    Icon(Icon),
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
    pub force_width: Option<i16>,
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
        force_width: Option<i16>,
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
        force_width: Option<i16>,
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
        force_width: Option<i16>,
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
}

/// Describing the button on the screen - only visuals.
#[derive(Clone, Copy)]
pub struct ButtonDetails<T> {
    pub text: Option<T>,
    pub icon: Option<Icon>,
    pub duration: Option<Duration>,
    pub is_cancel: bool,
    pub with_outline: bool,
    pub with_arms: bool,
    pub force_width: Option<i16>,
    pub offset: Option<Offset>,
}

impl<T: Clone + AsRef<str>> ButtonDetails<T> {
    /// Text button.
    pub fn text(text: T) -> Self {
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
    pub fn icon(icon: Icon) -> Self {
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

    /// Text with arms signalling double press.
    pub fn armed_text(text: T) -> Self {
        Self::text(text).with_arms()
    }

    /// Cross-style-icon cancel button with no outline.
    pub fn cancel_icon() -> Self {
        Self::icon(Icon::new(theme::ICON_CANCEL))
            .with_no_outline()
            .with_offset(Offset::new(2, -2))
    }

    /// Left arrow to signal going back. No outline.
    pub fn left_arrow_icon() -> Self {
        Self::icon(Icon::new(theme::ICON_ARROW_LEFT)).with_no_outline()
    }

    /// Right arrow to signal going forward. No outline.
    pub fn right_arrow_icon() -> Self {
        Self::icon(Icon::new(theme::ICON_ARROW_RIGHT)).with_no_outline()
    }

    /// Up arrow to signal paginating back. No outline. Offsetted little right
    /// to not be on the boundary.
    pub fn up_arrow_icon() -> Self {
        Self::icon(Icon::new(theme::ICON_ARROW_UP))
            .with_no_outline()
            .with_offset(Offset::new(2, -3))
    }

    /// Down arrow to signal paginating forward. Takes half the screen's width
    pub fn down_arrow_icon_wide() -> Self {
        Self::icon(Icon::new(theme::ICON_ARROW_DOWN)).force_width(HALF_SCREEN_BUTTON_WIDTH)
    }

    /// Up arrow to signal paginating back. Takes half the screen's width
    pub fn up_arrow_icon_wide() -> Self {
        Self::icon(Icon::new(theme::ICON_ARROW_UP)).force_width(HALF_SCREEN_BUTTON_WIDTH)
    }

    /// Icon of a bin to signal deleting.
    pub fn bin_icon() -> Self {
        Self::icon(Icon::new(theme::ICON_BIN)).with_no_outline()
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

    /// Default duration of the hold-to-confirm.
    pub fn with_default_duration(mut self) -> Self {
        self.duration = Some(Duration::from_millis(1000));
        self
    }

    /// Specific duration of the hold-to-confirm.
    pub fn with_duration(mut self, duration: Duration) -> Self {
        self.duration = Some(duration);
        self
    }

    /// Width of the button.
    pub fn force_width(mut self, width: i16) -> Self {
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
}

/// Holding the button details for all three possible buttons.
#[derive(Clone)]
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
    /// Default button layout for all three buttons - icons.
    pub fn default_three_icons() -> Self {
        Self::three_icons_middle_text("SELECT")
    }

    /// Special middle text for default icon layout.
    pub fn three_icons_middle_text(middle_text: &'static str) -> Self {
        Self::new(
            Some(ButtonDetails::left_arrow_icon()),
            Some(ButtonDetails::armed_text(middle_text)),
            Some(ButtonDetails::right_arrow_icon()),
        )
    }

    /// Left and right texts.
    pub fn left_right_text(text_left: &'static str, text_right: &'static str) -> Self {
        Self::new(
            Some(ButtonDetails::text(text_left)),
            None,
            Some(ButtonDetails::text(text_right)),
        )
    }

    /// Left and right arrow icons for navigation.
    pub fn left_right_arrows() -> Self {
        Self::new(
            Some(ButtonDetails::left_arrow_icon()),
            None,
            Some(ButtonDetails::right_arrow_icon()),
        )
    }

    /// Cancel cross on left and right arrow.
    pub fn cancel_and_arrow() -> Self {
        Self::new(
            Some(ButtonDetails::cancel_icon()),
            None,
            Some(ButtonDetails::right_arrow_icon()),
        )
    }

    /// Cancel cross on left and right arrow facing down.
    pub fn cancel_and_arrow_down() -> Self {
        Self::new(
            Some(ButtonDetails::cancel_icon()),
            None,
            Some(ButtonDetails::down_arrow_icon_wide()),
        )
    }

    /// Cancel cross on left and text on the right.
    pub fn cancel_and_text(text: &'static str) -> Self {
        Self::new(
            Some(ButtonDetails::cancel_icon()),
            None,
            Some(ButtonDetails::text(text)),
        )
    }

    /// Cancel cross on left and hold-to-confirm text on the right.
    pub fn cancel_and_htc_text(text: &'static str, duration: Duration) -> Self {
        Self::new(
            Some(ButtonDetails::cancel_icon()),
            None,
            Some(ButtonDetails::text(text).with_duration(duration)),
        )
    }

    /// Arrow back on left and hold-to-confirm text on the right.
    pub fn back_and_htc_text(text: &'static str, duration: Duration) -> Self {
        Self::new(
            Some(ButtonDetails::left_arrow_icon()),
            None,
            Some(ButtonDetails::text(text).with_duration(duration)),
        )
    }

    /// Arrow back on left and text on the right.
    pub fn back_and_text(text: &'static str) -> Self {
        Self::new(
            Some(ButtonDetails::left_arrow_icon()),
            None,
            Some(ButtonDetails::text(text)),
        )
    }

    /// Only armed text in the middle.
    pub fn middle_armed_text(text: &'static str) -> Self {
        Self::new(None, Some(ButtonDetails::armed_text(text)), None)
    }

    /// Only hold-to-confirm with text on the right.
    pub fn htc_only(text: &'static str, duration: Duration) -> Self {
        Self::new(
            None,
            None,
            Some(ButtonDetails::text(text).with_duration(duration)),
        )
    }

    /// Only right arrow facing down.
    pub fn only_arrow_down() -> Self {
        Self::new(None, None, Some(ButtonDetails::down_arrow_icon_wide()))
    }
}

/// What happens when a button is triggered.
/// Theoretically any action can be connected
/// with any button.
#[derive(Clone, PartialEq, Eq)]
pub enum ButtonAction {
    /// Go to the next page of this flow
    NextPage,
    /// Go to the previous page of this flow
    PrevPage,
    /// Go to a page of this flow specified by an index.
    /// Negative numbers can be used to count from the end.
    /// (0 ~ GoToFirstPage, -1 ~ GoToLastPage etc.)
    GoToIndex(i16),
    /// Go forwards/backwards a specified number of pages.
    /// Negative numbers mean going back.
    MovePageRelative(i16),
    /// Cancel the whole layout - send Msg::Cancelled
    Cancel,
    /// Confirm the whole layout - send Msg::Confirmed
    Confirm,
    /// Select current choice value
    Select,
    /// Some custom specific action
    Action(&'static str),
}

#[cfg(feature = "ui_debug")]
impl ButtonAction {
    /// Describing the action as a string. Debug-only.
    pub fn string(&self) -> String<25> {
        match self {
            ButtonAction::NextPage => "Next".into(),
            ButtonAction::PrevPage => "Prev".into(),
            ButtonAction::GoToIndex(index) => {
                build_string!(25, "Index(", inttostr!(*index), ")")
            }
            ButtonAction::MovePageRelative(index) => {
                build_string!(25, "Relative(", inttostr!(*index), ")")
            }
            ButtonAction::Cancel => "Cancel".into(),
            ButtonAction::Confirm => "Confirm".into(),
            ButtonAction::Select => "Select".into(),
            ButtonAction::Action(action) => (*action).into(),
        }
    }

    /// Adding a description to the Select action.
    pub fn select_item<T: AsRef<str>>(item: T) -> String<25> {
        build_string!(25, &Self::Select.string(), "(", item.as_ref(), ")")
    }

    /// When there is no action.
    pub fn empty() -> String<25> {
        "None".into()
    }
}

// TODO: might consider defining ButtonAction::Empty
// and only storing ButtonAction instead of Option<ButtonAction>...

/// Storing actions for all three possible buttons.
#[derive(Clone)]
pub struct ButtonActions {
    pub left: Option<ButtonAction>,
    pub middle: Option<ButtonAction>,
    pub right: Option<ButtonAction>,
}

impl ButtonActions {
    pub fn new(
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
    pub fn prev_next() -> Self {
        Self::new(
            Some(ButtonAction::PrevPage),
            None,
            Some(ButtonAction::NextPage),
        )
    }

    /// Going back with left, going further with middle
    pub fn prev_next_with_middle() -> Self {
        Self::new(
            Some(ButtonAction::PrevPage),
            Some(ButtonAction::NextPage),
            None,
        )
    }

    /// Previous with left, confirming with right
    pub fn prev_confirm() -> Self {
        Self::new(
            Some(ButtonAction::PrevPage),
            None,
            Some(ButtonAction::Confirm),
        )
    }

    /// Going to last page with left, to the next page with right
    pub fn last_next() -> Self {
        Self::new(
            Some(ButtonAction::GoToIndex(-1)),
            None,
            Some(ButtonAction::NextPage),
        )
    }

    /// Cancelling with left, going to the next page with right
    pub fn cancel_next() -> Self {
        Self::new(
            Some(ButtonAction::Cancel),
            None,
            Some(ButtonAction::NextPage),
        )
    }

    /// Only going to the next page with right
    pub fn only_next() -> Self {
        Self::new(None, None, Some(ButtonAction::NextPage))
    }

    /// Cancelling with left, confirming with right
    pub fn cancel_confirm() -> Self {
        Self::new(
            Some(ButtonAction::Cancel),
            None,
            Some(ButtonAction::Confirm),
        )
    }

    /// Going to the beginning with left, confirming with right
    pub fn beginning_confirm() -> Self {
        Self::new(
            Some(ButtonAction::GoToIndex(0)),
            None,
            Some(ButtonAction::Confirm),
        )
    }

    /// Going to the beginning with left, cancelling with right
    pub fn beginning_cancel() -> Self {
        Self::new(
            Some(ButtonAction::GoToIndex(0)),
            None,
            Some(ButtonAction::Cancel),
        )
    }

    /// Having access to appropriate action based on the `ButtonPos`
    pub fn get_action(&self, pos: ButtonPos) -> Option<ButtonAction> {
        match pos {
            ButtonPos::Left => self.left.clone(),
            ButtonPos::Middle => self.middle.clone(),
            ButtonPos::Right => self.right.clone(),
        }
    }
}

#[cfg(feature = "ui_debug")]
impl<T> crate::trace::Trace for ButtonDetails<T>
where
    T: AsRef<str>,
{
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.open("ButtonDetails");
        let mut btn_text: String<30> = String::new();
        if let Some(text) = &self.text {
            btn_text.push_str(text.as_ref()).unwrap();
        } else if let Some(icon) = &self.icon {
            btn_text.push_str("Icon:").unwrap();
            btn_text.push_str(icon.text.as_ref()).unwrap();
        }
        if let Some(duration) = &self.duration {
            btn_text.push_str(" (HTC:").unwrap();
            btn_text.push_str(inttostr!(duration.to_millis())).unwrap();
            btn_text.push_str(")").unwrap();
        }
        t.button(btn_text.as_ref());
        t.close();
    }
}
