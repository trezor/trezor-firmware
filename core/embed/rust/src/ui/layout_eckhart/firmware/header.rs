use crate::{
    strutil::TString,
    ui::{
        component::{text::TextStyle, Component, Event, EventCtx, Label},
        display::{Color, Icon},
        geometry::{Alignment2D, Insets, Rect},
        shape::{self, Renderer},
    },
};

use super::{
    super::component::{Button, ButtonContent, ButtonMsg, FuelGauge},
    constant, theme,
};

/// Component for the header of a screen. Eckhart UI shows the title (can be two
/// lines), optional icon button on the left, and optional icon button
/// (typically for menu) on the right.
pub struct Header {
    title: Label<'static>,
    /// button in the top-right corner
    right_button: Option<Button>,
    /// button in the top-left corner
    left_button: Option<Button>,
    right_button_msg: HeaderMsg,
    left_button_msg: HeaderMsg,
    /// icon in the top-left corner (used instead of left button)
    icon: Option<Icon>,
    icon_color: Option<Color>,
    icon_area: Rect,
    /// Battery status indicator
    fuel_gauge: Option<FuelGauge>,
}

#[derive(Copy, Clone)]
pub enum HeaderMsg {
    Back,
    Cancelled,
    Menu,
}

impl Header {
    pub const HEADER_HEIGHT: i16 = theme::HEADER_HEIGHT; // [px]
    const BUTTON_TOUCH_EXPAND: Insets = Insets::sides(32); // [px]

    pub const fn new(title: TString<'static>) -> Self {
        Self {
            title: Label::left_aligned(title, theme::label_title_main()).vertically_centered(),
            right_button: None,
            left_button: None,
            right_button_msg: HeaderMsg::Cancelled,
            left_button_msg: HeaderMsg::Cancelled,
            icon: None,
            icon_color: None,
            icon_area: Rect::zero(),
            fuel_gauge: Some(FuelGauge::on_charging_change()),
        }
    }

    #[inline(never)]
    pub fn with_text_style(mut self, style: TextStyle) -> Self {
        self.title = self.title.styled(style);
        self
    }

    #[inline(never)]
    pub fn with_right_button(self, button: Button, msg: HeaderMsg) -> Self {
        debug_assert!(matches!(button.content(), ButtonContent::Icon(_)));
        Self {
            right_button: Some(
                button
                    .with_expanded_touch_area(Self::BUTTON_TOUCH_EXPAND)
                    .with_radius(12),
            ),
            right_button_msg: msg,
            ..self
        }
    }

    #[inline(never)]
    pub fn with_left_button(self, button: Button, msg: HeaderMsg) -> Self {
        debug_assert!(matches!(button.content(), ButtonContent::Icon(_)));
        Self {
            icon: None,
            left_button: Some(
                button
                    .with_expanded_touch_area(Self::BUTTON_TOUCH_EXPAND)
                    .with_radius(12),
            ),
            left_button_msg: msg,
            ..self
        }
    }

    #[inline(never)]
    pub fn with_menu_button(self) -> Self {
        self.with_right_button(
            Button::with_icon(theme::ICON_MENU).styled(theme::button_header()),
            HeaderMsg::Menu,
        )
    }

    #[inline(never)]
    pub fn with_close_button(self) -> Self {
        self.with_right_button(
            Button::with_icon(theme::ICON_CLOSE).styled(theme::button_header()),
            HeaderMsg::Cancelled,
        )
    }

    #[inline(never)]
    pub fn with_icon(self, icon: Icon, color: Color) -> Self {
        Self {
            left_button: None,
            icon: Some(icon),
            icon_color: Some(color),
            ..self
        }
    }

    #[inline(never)]
    pub fn with_fuel_gauge(self, fuel_gauge: Option<FuelGauge>) -> Self {
        Self { fuel_gauge, ..self }
    }

    #[inline(never)]
    pub fn update_title(&mut self, ctx: &mut EventCtx, title: TString<'static>) {
        self.title.set_text(title);
        ctx.request_paint();
    }

    /// Whether any of the buttons is currently pressed
    /// Used for defining the order of rendering of overlapping components
    pub fn pressed(&self) -> bool {
        self.left_button.as_ref().is_some_and(|b| b.is_pressed())
            || self.right_button.as_ref().is_some_and(|b| b.is_pressed())
    }

    /// Calculates the width needed for the right button
    fn right_button_width(&self) -> i16 {
        if let Some(b) = &self.right_button {
            match b.content() {
                ButtonContent::Icon(icon) => icon.toif.width() + 2 * theme::PADDING,
                // We do not expect any other ButtonContent as the right button of the Header
                _ => unreachable!(),
            }
        } else {
            // Title must have a default padding from the right side
            theme::PADDING
        }
    }

    /// Calculates the width needed for the left icon, be it a button with icon
    /// or just icon
    fn left_object_width(&self) -> i16 {
        const ICON_MARGIN_RIGHT: i16 = 16; // [px]
        if let Some(b) = &self.left_button {
            match b.content() {
                ButtonContent::Icon(icon) => icon.toif.width() + 2 * theme::PADDING,
                // We do not expect any other ButtonContent as the left button of the Header
                _ => unreachable!(),
            }
        } else if let Some(icon) = self.icon {
            theme::PADDING + icon.toif.width() + ICON_MARGIN_RIGHT
        } else {
            // Title must have a default padding from the left side
            theme::PADDING
        }
    }
}

impl Component for Header {
    type Msg = HeaderMsg;

    fn place(&mut self, bounds: Rect) -> Rect {
        debug_assert_eq!(bounds.width(), constant::SCREEN.width());
        debug_assert_eq!(bounds.height(), Self::HEADER_HEIGHT);

        let (rest, right_button_area) = bounds.split_right(self.right_button_width());
        self.icon_area = rest.inset(Insets::left(theme::PADDING));
        let (left_object_area, title_area) = rest.split_left(self.left_object_width());

        self.left_button.place(left_object_area);
        self.title.place(title_area);
        self.fuel_gauge.place(self.icon_area);
        self.right_button.place(right_button_area);

        if let Some(fuel_gauge) = &mut self.fuel_gauge {
            // Force update the fuel gauge state, so it is up-to-date
            // necessary e.g. for the first DeviceMenu Submenu re-entry
            fuel_gauge.update_pm_state();
        }

        bounds
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        self.fuel_gauge.event(ctx, event);

        if let Some(ButtonMsg::Clicked) = self.left_button.event(ctx, event) {
            return Some(self.left_button_msg);
        };
        if let Some(ButtonMsg::Clicked) = self.right_button.event(ctx, event) {
            return Some(self.right_button_msg);
        };

        None
    }

    fn render<'s>(&'s self, target: &mut impl Renderer<'s>) {
        self.right_button.render(target);
        if self
            .fuel_gauge
            .as_ref()
            .is_some_and(|fg| fg.should_be_shown())
        {
            self.fuel_gauge.render(target);
        } else {
            self.left_button.render(target);
            if let Some(icon) = self.icon {
                shape::ToifImage::new(self.icon_area.left_center(), icon.toif)
                    .with_fg(self.icon_color.unwrap_or(theme::GREY_LIGHT))
                    .with_align(Alignment2D::CENTER_LEFT)
                    .render(target);
            }
            self.title.render(target);
        }
    }
}

#[cfg(feature = "ui_debug")]
impl crate::trace::Trace for Header {
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.component("Header");
        t.child("title", &self.title);
        if let Some(button) = &self.right_button {
            t.child("button", button);
        }
    }
}
