use crate::{
    strutil::TString,
    time::Duration,
    ui::{
        component::{Component, Event, EventCtx, Never},
        constant,
        display::{Color, Font, Icon},
        event::PhysicalButton,
        geometry::{Alignment2D, Offset, Point, Rect},
        shape,
        shape::Renderer,
    },
};

use super::{super::fonts, loader::DEFAULT_DURATION_MS, theme};

const HALF_SCREEN_BUTTON_WIDTH: i16 = constant::WIDTH / 2 - 1;

#[derive(Copy, Clone, Eq, PartialEq)]
pub enum ButtonPos {
    Left,
    Middle,
    Right,
}

impl From<PhysicalButton> for ButtonPos {
    fn from(btn: PhysicalButton) -> Self {
        match btn {
            PhysicalButton::Left => ButtonPos::Left,
            PhysicalButton::Right => ButtonPos::Right,
            _ => fatal_error!("unsupported button"),
        }
    }
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

    pub fn from_button_details(pos: ButtonPos, btn_details: ButtonDetails) -> Self {
        // Deciding between text and icon
        let style = btn_details.style();
        match btn_details.content {
            ButtonContent::Text(text) => Self::with_text(pos, text, style),
            ButtonContent::Icon(icon) => Self::with_icon(pos, icon, style),
        }
    }

    pub fn with_text(pos: ButtonPos, text: TString<'static>, styles: ButtonStyleSheet) -> Self {
        Self::new(pos, ButtonContent::Text(text), styles)
    }

    pub fn with_icon(pos: ButtonPos, image: Icon, styles: ButtonStyleSheet) -> Self {
        Self::new(pos, ButtonContent::Icon(image), styles)
    }

    pub fn content(&self) -> &ButtonContent {
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
    pub fn set_text(&mut self, text: TString<'static>) {
        self.content = ButtonContent::Text(text);
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
            match &self.content {
                ButtonContent::Text(text) => {
                    let text_width = text.map(|t| style.font.visible_text_width(t));
                    if style.with_outline {
                        text_width + 2 * theme::BUTTON_OUTLINE
                    } else if style.with_arms {
                        text_width + 2 * theme::ARMS_MARGIN
                    } else {
                        text_width
                    }
                }
                ButtonContent::Icon(icon) => {
                    // When Icon does not have outline, hardcode its width
                    if style.with_outline {
                        icon.toif.width() + 2 * theme::BUTTON_OUTLINE
                    } else {
                        theme::BUTTON_ICON_WIDTH
                    }
                }
            }
        };

        // Arms should connect to the center, therefore decreasing the height
        let button_height = if style.with_arms {
            theme::BUTTON_HEIGHT - 2
        } else {
            theme::BUTTON_HEIGHT
        };
        let button_bounds = self.bounds.split_bottom(button_height).1;
        match self.pos {
            ButtonPos::Left => button_bounds.split_left(button_width).0,
            ButtonPos::Right => button_bounds.split_right(button_width).1,
            ButtonPos::Middle => button_bounds.split_center(button_width).1,
        }
    }

    /// Determine baseline point for the text.
    fn get_text_baseline(&self, style: &ButtonStyle) -> Point {
        // Arms and outline require the text to be elevated.
        // Moving text to the right and elevating it for arms and outline.
        let (mut offset_x, offset_y) = if style.with_outline {
            (theme::BUTTON_OUTLINE, theme::BUTTON_OUTLINE)
        } else if style.with_arms {
            (theme::ARMS_MARGIN, theme::ARMS_MARGIN)
        } else {
            (0, 0)
        };

        // Centering the text in case of fixed width.
        if let ButtonContent::Text(text) = &self.content {
            if let Some(fixed_width) = style.fixed_width {
                let diff = fixed_width - text.map(|t| style.font.visible_text_width(t));
                offset_x = diff / 2;
            }
        }

        self.get_current_area().bottom_left() + Offset::new(offset_x, -offset_y)
    }
}

impl Component for Button {
    type Msg = Never;

    fn place(&mut self, bounds: Rect) -> Rect {
        self.bounds = bounds;
        self.get_current_area()
    }

    fn event(&mut self, _ctx: &mut EventCtx, _event: Event) -> Option<Self::Msg> {
        // Events are handled by `ButtonController`
        None
    }

    fn render<'s>(&'s self, target: &mut impl Renderer<'s>) {
        let style = self.style();
        let fg_color = style.text_color;
        let bg_color = fg_color.negate();
        let area = self.get_current_area();
        let inversed_colors = bg_color != theme::BG;

        // Filling the background (with 2-pixel rounding when applicable)
        if inversed_colors {
            shape::Bar::new(area)
                .with_radius(3)
                .with_bg(bg_color)
                .render(target);
        } else if style.with_outline {
            shape::Bar::new(area)
                .with_radius(3)
                .with_fg(fg_color)
                .render(target);
        } else {
            shape::Bar::new(area).with_bg(bg_color).render(target);
        }

        // Optionally display "arms" at both sides of content - always in FG and BG
        // colors (they are not inverted).
        if style.with_arms {
            shape::ToifImage::new(area.left_center(), theme::ICON_ARM_LEFT.toif)
                .with_align(Alignment2D::TOP_RIGHT)
                .with_fg(theme::FG)
                .render(target);

            shape::ToifImage::new(area.right_center(), theme::ICON_ARM_RIGHT.toif)
                .with_align(Alignment2D::TOP_LEFT)
                .with_fg(theme::FG)
                .render(target);
        }

        // Painting the content
        match &self.content {
            ButtonContent::Text(text) => text.map(|t| {
                shape::Text::new(
                    self.get_text_baseline(style) - Offset::x(style.font.start_x_bearing(t)),
                    t,
                    style.font,
                )
                .with_fg(fg_color)
                .render(target);
            }),
            ButtonContent::Icon(icon) => {
                // Allowing for possible offset of the area from current style
                let icon_area = area.translate(style.offset);
                if style.with_outline {
                    shape::ToifImage::new(icon_area.center(), icon.toif)
                        .with_align(Alignment2D::CENTER)
                        .with_fg(fg_color)
                        .render(target);
                } else {
                    // Positioning the icon in the corresponding corner/center
                    match self.pos {
                        ButtonPos::Left => {
                            shape::ToifImage::new(icon_area.bottom_left(), icon.toif)
                                .with_align(Alignment2D::BOTTOM_LEFT)
                                .with_fg(fg_color)
                                .render(target)
                        }

                        ButtonPos::Right => {
                            shape::ToifImage::new(icon_area.bottom_right(), icon.toif)
                                .with_align(Alignment2D::BOTTOM_RIGHT)
                                .with_fg(fg_color)
                                .render(target)
                        }

                        ButtonPos::Middle => shape::ToifImage::new(icon_area.center(), icon.toif)
                            .with_align(Alignment2D::CENTER)
                            .with_fg(fg_color)
                            .render(target),
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
pub enum ButtonContent {
    Text(TString<'static>),
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
        font: Font,
        normal_color: Color,
        active_color: Color,
        with_outline: bool,
        with_arms: bool,
        fixed_width: Option<i16>,
        offset: Offset,
    ) -> Self {
        Self {
            normal: ButtonStyle {
                font,
                text_color: normal_color,
                with_outline,
                with_arms,
                fixed_width,
                offset,
            },
            active: ButtonStyle {
                font,
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
        font: Font,
        with_outline: bool,
        with_arms: bool,
        fixed_width: Option<i16>,
        offset: Offset,
    ) -> Self {
        Self::new(
            font,
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
pub struct ButtonDetails {
    pub content: ButtonContent,
    font: Font,
    pub duration: Option<Duration>,
    with_outline: bool,
    with_arms: bool,
    fixed_width: Option<i16>,
    offset: Offset,
    pub send_long_press: bool,
}

impl ButtonDetails {
    /// Text button.
    pub fn text(text: TString<'static>) -> Self {
        Self {
            content: ButtonContent::Text(text),
            font: fonts::FONT_NORMAL_UPPER,
            duration: None,
            with_outline: true,
            with_arms: false,
            fixed_width: None,
            offset: Offset::zero(),
            send_long_press: false,
        }
    }

    /// Icon button.
    pub fn icon(icon: Icon) -> Self {
        Self {
            content: ButtonContent::Icon(icon),
            font: fonts::FONT_NORMAL_UPPER,
            duration: None,
            with_outline: false,
            with_arms: false,
            fixed_width: None,
            offset: Offset::zero(),
            send_long_press: false,
        }
    }

    /// Resolves text and finds possible icon names.
    pub fn from_text_possible_icon(text: TString<'static>) -> Self {
        text.map(|t| match t {
            "" => Self::cancel_icon(),
            "<" => Self::left_arrow_icon(),
            "^" => Self::up_arrow_icon(),
            _ => Self::text(text),
        })
    }

    /// Text with arms signalling double press.
    pub fn armed_text(text: TString<'static>) -> Self {
        Self::text(text).with_arms()
    }

    /// Cross-style-icon cancel button with no outline.
    pub fn cancel_icon() -> Self {
        Self::icon(theme::ICON_CANCEL).with_offset(Offset::new(3, -3))
    }

    /// Left arrow to signal going back. No outline.
    pub fn left_arrow_icon() -> Self {
        Self::icon(theme::ICON_ARROW_LEFT).with_offset(Offset::new(4, -3))
    }

    /// Right arrow to signal going forward. No outline.
    pub fn right_arrow_icon() -> Self {
        Self::icon(theme::ICON_ARROW_RIGHT).with_offset(Offset::new(-4, -3))
    }

    /// Up arrow to signal paginating back. No outline. Offsetted little right
    /// to not be on the boundary.
    pub fn up_arrow_icon() -> Self {
        Self::icon(theme::ICON_ARROW_UP).with_offset(Offset::new(3, -4))
    }

    /// Down arrow to signal paginating forward. Takes half the screen's width
    pub fn down_arrow_icon_wide() -> Self {
        Self::icon(theme::ICON_ARROW_DOWN)
            .with_outline(true)
            .with_fixed_width(HALF_SCREEN_BUTTON_WIDTH)
    }

    /// Up arrow to signal paginating back. Takes half the screen's width
    pub fn up_arrow_icon_wide() -> Self {
        Self::icon(theme::ICON_ARROW_UP)
            .with_outline(true)
            .with_fixed_width(HALF_SCREEN_BUTTON_WIDTH)
    }

    /// Possible outline around the button.
    pub fn with_outline(mut self, outline: bool) -> Self {
        self.with_outline = outline;
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

    /// Specifying the font of the button.
    pub fn with_font(mut self, font: Font) -> Self {
        self.font = font;
        self
    }

    /// Button style that should be applied.
    pub fn style(&self) -> ButtonStyleSheet {
        ButtonStyleSheet::default(
            self.font,
            self.with_outline,
            self.with_arms,
            self.fixed_width,
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

    /// Arrows at sides, armed text in the middle.
    pub fn arrow_armed_arrow(text: TString<'static>) -> Self {
        Self::new(
            Some(ButtonDetails::left_arrow_icon()),
            Some(ButtonDetails::armed_text(text)),
            Some(ButtonDetails::right_arrow_icon()),
        )
    }

    /// Left cancel, armed text and next right arrow.
    pub fn cancel_armed_arrow(text: TString<'static>) -> Self {
        Self::new(
            Some(ButtonDetails::cancel_icon()),
            Some(ButtonDetails::armed_text(text)),
            Some(ButtonDetails::right_arrow_icon()),
        )
    }

    /// Middle armed text and next right arrow.
    pub fn none_armed_arrow(text: TString<'static>) -> Self {
        Self::new(
            None,
            Some(ButtonDetails::armed_text(text)),
            Some(ButtonDetails::right_arrow_icon()),
        )
    }

    /// Left text, armed text and right info icon/text.
    pub fn text_armed_info(left: TString<'static>, middle: TString<'static>) -> Self {
        Self::new(
            Some(ButtonDetails::from_text_possible_icon(left)),
            Some(ButtonDetails::armed_text(middle)),
            Some(
                ButtonDetails::text("i".into())
                    .with_fixed_width(theme::BUTTON_ICON_WIDTH)
                    .with_font(fonts::FONT_NORMAL),
            ),
        )
    }

    /// Left cancel, armed text and right info icon/text.
    pub fn cancel_armed_info(middle: TString<'static>) -> Self {
        Self::new(
            Some(ButtonDetails::cancel_icon()),
            Some(ButtonDetails::armed_text(middle)),
            Some(
                ButtonDetails::text("i".into())
                    .with_fixed_width(theme::BUTTON_ICON_WIDTH)
                    .with_font(fonts::FONT_NORMAL),
            ),
        )
    }

    /// Left cancel, armed text and blank on right.
    pub fn cancel_armed_none(middle: TString<'static>) -> Self {
        Self::new(
            Some(ButtonDetails::cancel_icon()),
            Some(ButtonDetails::armed_text(middle)),
            None,
        )
    }

    /// Left back arrow and middle armed text.
    pub fn arrow_armed_none(text: TString<'static>) -> Self {
        Self::new(
            Some(ButtonDetails::left_arrow_icon()),
            Some(ButtonDetails::armed_text(text)),
            None,
        )
    }

    /// Left and right texts.
    pub fn text_none_text(left: TString<'static>, right: TString<'static>) -> Self {
        Self::new(
            Some(ButtonDetails::from_text_possible_icon(left)),
            None,
            Some(ButtonDetails::from_text_possible_icon(right)),
        )
    }

    /// Left text and right arrow.
    pub fn text_none_arrow(text: TString<'static>) -> Self {
        Self::new(
            Some(ButtonDetails::from_text_possible_icon(text)),
            None,
            Some(ButtonDetails::right_arrow_icon()),
        )
    }

    /// Left text and WIDE right arrow.
    pub fn text_none_arrow_wide(text: TString<'static>) -> Self {
        Self::new(
            Some(ButtonDetails::from_text_possible_icon(text)),
            None,
            Some(ButtonDetails::down_arrow_icon_wide()),
        )
    }

    /// Only right text.
    pub fn none_none_text(text: TString<'static>) -> Self {
        Self::new(
            None,
            None,
            Some(ButtonDetails::from_text_possible_icon(text)),
        )
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
    pub fn arrow_none_text(text: TString<'static>) -> Self {
        Self::new(
            Some(ButtonDetails::left_arrow_icon()),
            None,
            Some(ButtonDetails::from_text_possible_icon(text)),
        )
    }

    /// Up arrow left and right text.
    pub fn up_arrow_none_text(text: TString<'static>) -> Self {
        Self::new(
            Some(ButtonDetails::up_arrow_icon()),
            None,
            Some(ButtonDetails::from_text_possible_icon(text)),
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

    /// Up arrow on left and right arrow facing down.
    pub fn up_arrow_none_arrow_wide() -> Self {
        Self::new(
            Some(ButtonDetails::up_arrow_icon()),
            None,
            Some(ButtonDetails::down_arrow_icon_wide()),
        )
    }

    /// Up arrow on left, middle text and info on the right.
    pub fn up_arrow_armed_info(text: TString<'static>) -> Self {
        Self::new(
            Some(ButtonDetails::up_arrow_icon()),
            Some(ButtonDetails::armed_text(text)),
            Some(
                ButtonDetails::text("i".into())
                    .with_fixed_width(theme::BUTTON_ICON_WIDTH)
                    .with_font(fonts::FONT_NORMAL),
            ),
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
    pub fn cancel_none_text(text: TString<'static>) -> Self {
        Self::new(
            Some(ButtonDetails::cancel_icon()),
            None,
            Some(ButtonDetails::from_text_possible_icon(text)),
        )
    }

    /// Cancel cross on left and hold-to-confirm text on the right.
    pub fn cancel_none_htc(text: TString<'static>) -> Self {
        Self::new(
            Some(ButtonDetails::cancel_icon()),
            None,
            Some(ButtonDetails::text(text).with_default_duration()),
        )
    }

    /// Arrow back on left and hold-to-confirm text on the right.
    pub fn arrow_none_htc(text: TString<'static>) -> Self {
        Self::new(
            Some(ButtonDetails::left_arrow_icon()),
            None,
            Some(ButtonDetails::text(text).with_default_duration()),
        )
    }

    /// Only armed text in the middle.
    pub fn none_armed_none(text: TString<'static>) -> Self {
        Self::new(None, Some(ButtonDetails::armed_text(text)), None)
    }

    /// HTC on both sides.
    pub fn htc_none_htc(left: TString<'static>, right: TString<'static>) -> Self {
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

    /// Only confirming with middle
    pub fn none_confirm_none() -> Self {
        Self::new(None, Some(ButtonAction::Confirm), None)
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

    /// Only going to the next page with middle
    pub fn none_next_none() -> Self {
        Self::new(None, Some(ButtonAction::NextPage), None)
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

    /// Cancelling with left and confirming with middle
    pub fn cancel_confirm_none() -> Self {
        Self::new(
            Some(ButtonAction::Cancel),
            Some(ButtonAction::Confirm),
            None,
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
impl crate::trace::Trace for Button {
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.component("Button");
        match self.content {
            ButtonContent::Text(text) => t.string("text", text),
            ButtonContent::Icon(icon) => {
                t.null("text");
                t.string("icon", icon.name.into());
            }
        }
    }
}

#[cfg(feature = "ui_debug")]
impl crate::trace::Trace for ButtonDetails {
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.component("ButtonDetails");
        match self.content {
            ButtonContent::Text(text) => {
                t.string("text", text);
            }
            ButtonContent::Icon(icon) => {
                t.null("text");
                t.string("icon", icon.name.into());
            }
        }
        if let Some(duration) = &self.duration {
            t.int("hold_to_confirm", duration.to_millis() as i64);
        }
    }
}
