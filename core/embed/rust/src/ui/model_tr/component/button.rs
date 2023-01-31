use crate::{
    micropython::buffer::StrBuffer,
    time::Duration,
    ui::{
        component::{Component, Event, EventCtx},
        constant,
        display::{self, Color, Font, Icon},
        geometry::{Offset, Point, Rect, BOTTOM_LEFT, BOTTOM_RIGHT, CENTER, TOP_LEFT, TOP_RIGHT},
    },
};

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

pub struct Button {
    bounds: Rect,
    pos: ButtonPos,
    content: ButtonContent,
    styles: ButtonStyleSheet,
    state: State,
}

impl Button {
    pub fn new(pos: ButtonPos, content: ButtonContent, styles: ButtonStyleSheet) -> Self {
        Self {
            pos,
            content,
            styles,
            bounds: Rect::zero(),
            state: State::Released,
        }
    }

    pub fn with_text(pos: ButtonPos, text: StrBuffer, styles: ButtonStyleSheet) -> Self {
        Self::new(pos, ButtonContent::Text(text), styles)
    }

    pub fn with_icon(pos: ButtonPos, image: Icon, styles: ButtonStyleSheet) -> Self {
        Self::new(pos, ButtonContent::Icon(image), styles)
    }

    pub fn content(&self) -> &ButtonContent {
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
    pub fn set_text(&mut self, text: StrBuffer) {
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
                ButtonContent::Text(text) => style.font.visible_text_width(text.as_ref()),
                ButtonContent::Icon(icon) => icon.toif.width() - 1,
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

impl Component for Button {
    type Msg = ButtonMsg;

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
        let area = self.get_current_area();

        // Optionally display "arms" at both sides of content, or create
        // a nice rounded outline around it.
        // By default just fill the content background.
        if style.with_arms {
            const ARM_WIDTH: i16 = 15;

            // Prepare space for both the arms and content with BG color.
            // Arms are icons 10*6 pixels.
            let area_to_fill = area.extend_left(ARM_WIDTH).extend_right(ARM_WIDTH);
            display::rect_fill(area_to_fill, background_color);
            display::rect_fill_corners(area_to_fill, theme::BG);

            // Paint both arms.
            // Baselines are adjusted to give space between text and icon.
            // 2 px because 1px might lead to odd coordinate which can't be render
            Icon::new(theme::ICON_ARM_LEFT).draw(
                area.left_center() + Offset::x(-2),
                TOP_RIGHT,
                text_color,
                background_color,
            );
            Icon::new(theme::ICON_ARM_RIGHT).draw(
                area.right_center() + Offset::x(2),
                TOP_LEFT,
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
                    icon.draw(center, CENTER, text_color, background_color);
                } else {
                    // Positioning the icon in the corresponding corner/center
                    match self.pos {
                        ButtonPos::Left => icon.draw(
                            area.bottom_left(),
                            BOTTOM_LEFT,
                            text_color,
                            background_color,
                        ),
                        ButtonPos::Right => icon.draw(
                            area.bottom_right(),
                            BOTTOM_RIGHT,
                            text_color,
                            background_color,
                        ),
                        ButtonPos::Middle => {
                            icon.draw(area.center(), CENTER, text_color, background_color)
                        }
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

pub enum ButtonContent {
    Text(StrBuffer),
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
}

/// Describing the button on the screen - only visuals.
#[derive(Clone)]
pub struct ButtonDetails {
    pub text: Option<StrBuffer>,
    pub icon: Option<Icon>,
    pub duration: Option<Duration>,
    pub with_outline: bool,
    pub with_arms: bool,
    pub force_width: Option<i16>,
    pub offset: Option<Offset>,
}

impl ButtonDetails {
    /// Text button.
    pub fn text(text: StrBuffer) -> Self {
        Self {
            text: Some(text),
            icon: None,
            duration: None,
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
            with_outline: true,
            with_arms: false,
            force_width: None,
            offset: None,
        }
    }

    /// Text with arms signalling double press.
    pub fn armed_text(text: StrBuffer) -> Self {
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

    /// Default duration of the hold-to-confirm - 1 second.
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
        ButtonStyleSheet::default(
            self.with_outline,
            self.with_arms,
            self.force_width,
            self.offset,
        )
    }
}

/// Holding the button details for all three possible buttons.
#[derive(Clone)]
pub struct ButtonLayout {
    pub btn_left: Option<ButtonDetails>,
    pub btn_middle: Option<ButtonDetails>,
    pub btn_right: Option<ButtonDetails>,
}

impl ButtonLayout {
    pub fn new(
        btn_left: Option<ButtonDetails>,
        btn_middle: Option<ButtonDetails>,
        btn_right: Option<ButtonDetails>,
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
    pub fn arrow_armed_arrow(text: StrBuffer) -> Self {
        Self::new(
            Some(ButtonDetails::left_arrow_icon()),
            Some(ButtonDetails::armed_text(text)),
            Some(ButtonDetails::right_arrow_icon()),
        )
    }

    /// Left cancel, armed text and next right arrow.
    pub fn cancel_armed_arrow(text: StrBuffer) -> Self {
        Self::new(
            Some(ButtonDetails::cancel_icon()),
            Some(ButtonDetails::armed_text(text)),
            Some(ButtonDetails::right_arrow_icon()),
        )
    }

    /// Middle armed text and next right arrow.
    pub fn none_armed_arrow(text: StrBuffer) -> Self {
        Self::new(
            None,
            Some(ButtonDetails::armed_text(text)),
            Some(ButtonDetails::right_arrow_icon()),
        )
    }

    /// Left cancel, armed text and right text.
    pub fn cancel_armed_text(middle: StrBuffer, right: StrBuffer) -> Self {
        Self::new(
            Some(ButtonDetails::cancel_icon()),
            Some(ButtonDetails::armed_text(middle)),
            Some(ButtonDetails::text(right)),
        )
    }

    /// Left back arrow and middle armed text.
    pub fn arrow_armed_none(text: StrBuffer) -> Self {
        Self::new(
            Some(ButtonDetails::left_arrow_icon()),
            Some(ButtonDetails::armed_text(text)),
            None,
        )
    }

    /// Left and right texts.
    pub fn text_none_text(left: StrBuffer, right: StrBuffer) -> Self {
        Self::new(
            Some(ButtonDetails::text(left)),
            None,
            Some(ButtonDetails::text(right)),
        )
    }

    /// Left text and right arrow.
    pub fn text_none_arrow(text: StrBuffer) -> Self {
        Self::new(
            Some(ButtonDetails::text(text)),
            None,
            Some(ButtonDetails::right_arrow_icon()),
        )
    }

    /// Only right text.
    pub fn none_none_text(text: StrBuffer) -> Self {
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
    pub fn arrow_none_text(text: StrBuffer) -> Self {
        Self::new(
            Some(ButtonDetails::left_arrow_icon()),
            None,
            Some(ButtonDetails::text(text)),
        )
    }

    /// Up arrow left and right text.
    pub fn up_arrow_none_text(text: StrBuffer) -> Self {
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

    /// Cancel cross on left and text on the right.
    pub fn cancel_none_text(text: StrBuffer) -> Self {
        Self::new(
            Some(ButtonDetails::cancel_icon()),
            None,
            Some(ButtonDetails::text(text)),
        )
    }

    /// Cancel cross on left and hold-to-confirm text on the right.
    pub fn cancel_none_htc(text: StrBuffer) -> Self {
        Self::new(
            Some(ButtonDetails::cancel_icon()),
            None,
            Some(ButtonDetails::text(text).with_default_duration()),
        )
    }

    /// Arrow back on left and hold-to-confirm text on the right.
    pub fn arrow_none_htc(text: StrBuffer) -> Self {
        Self::new(
            Some(ButtonDetails::left_arrow_icon()),
            None,
            Some(ButtonDetails::text(text).with_default_duration()),
        )
    }

    /// Only armed text in the middle.
    pub fn none_armed_none(text: StrBuffer) -> Self {
        Self::new(None, Some(ButtonDetails::armed_text(text)), None)
    }

    /// Only hold-to-confirm with text on the right.
    pub fn none_none_htc(text: StrBuffer, duration: Duration) -> Self {
        Self::new(
            None,
            None,
            Some(ButtonDetails::text(text).with_duration(duration)),
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

/// Storing actions for all three possible buttons.
#[derive(Clone, Copy)]
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
            Some(ButtonAction::GoToIndex(-1)),
            None,
            Some(ButtonAction::NextPage),
        )
    }

    /// Going to last page with left, to the next page with right and confirm
    /// with middle
    pub fn last_confirm_next() -> Self {
        Self::new(
            Some(ButtonAction::GoToIndex(-1)),
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

    /// Going to the beginning with left, confirming with right
    pub fn beginning_none_confirm() -> Self {
        Self::new(
            Some(ButtonAction::GoToIndex(0)),
            None,
            Some(ButtonAction::Confirm),
        )
    }

    /// Going to the beginning with left, cancelling with right
    pub fn beginning_none_cancel() -> Self {
        Self::new(
            Some(ButtonAction::GoToIndex(0)),
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
impl crate::trace::Trace for Button {
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.open("Button");
        match &self.content {
            ButtonContent::Text(text) => t.field("text", text),
            ButtonContent::Icon(icon) => t.field("icon", icon),
        }
        t.close();
    }
}

#[cfg(feature = "ui_debug")]
use heapless::String;

#[cfg(feature = "ui_debug")]
impl crate::trace::Trace for ButtonDetails {
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.open("ButtonDetails");
        let mut btn_text: String<30> = String::new();
        if let Some(text) = &self.text {
            unwrap!(btn_text.push_str(text.as_ref()));
        } else if self.icon.is_some() {
            unwrap!(btn_text.push_str("Icon"));
        }
        if let Some(duration) = &self.duration {
            unwrap!(btn_text.push_str(" (HTC:"));
            unwrap!(btn_text.push_str(inttostr!(duration.to_millis())));
            unwrap!(btn_text.push_str(")"));
        }
        t.button(btn_text.as_ref());
        t.close();
    }
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
