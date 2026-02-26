use num_traits::clamp_max;

use crate::{
    error::Error,
    io::BinaryData,
    strutil::TString,
    translations::TR,
    ui::{
        component::{text::TextStyle, Component, Event, EventCtx, Label, Never, Swipe},
        display::{image::ImageInfo, Color},
        geometry::{Alignment2D, Direction, Insets, Offset, Point, Rect},
        layout::util::get_user_custom_image,
        notification::{Notification, NotificationLevel},
        shape::{self, Renderer},
    },
};

use super::{
    super::component::{Button, ButtonContent, ConnectionIndicator, FuelGauge},
    constant::{HEIGHT, SCREEN, WIDTH},
    theme::{self, firmware::button_homebar_style, ScreenBackground},
    ActionBar, ActionBarMsg, Hint,
};

#[cfg(feature = "rgb_led")]
use crate::ui::led::LedState;

/// Full-screen component for the homescreen and lockscreen.
pub struct Homescreen {
    /// Device name label, fuel gauge, and connection status
    status: HomescreenStatus,
    /// Notification
    hint: Option<Hint<'static>>,
    /// Home action bar
    action_bar: ActionBar,
    /// Background image
    image: Option<BinaryData<'static>>,
    /// LED color
    led_color: Option<Color>,
    /// Whether the homescreen is locked
    locked: bool,
    /// Whether the homescreen is a boot screen
    bootscreen: bool,
    /// Swipe component for vertical swiping
    swipe: Swipe,
    // swipe_config: SwipeConfig,
}

pub enum HomescreenMsg {
    Dismissed,
    Menu,
}

impl Homescreen {
    pub fn new(
        label: TString<'static>,
        _lockable: bool,
        locked: bool,
        bootscreen: bool,
        coinjoin_authorized: bool,
        notification: Option<Notification>,
    ) -> Result<Self, Error> {
        let image = get_homescreen_image();

        // Notification
        let (led_color, hint) = match notification {
            Some(ref notification) => {
                let (led_color, hint) = Self::get_notification_display(notification);
                (Some(led_color), Some(hint))
            }
            None if locked && coinjoin_authorized => (
                Some(theme::LED_GREEN_LIME),
                Some(Hint::new_instruction_green(
                    TR::coinjoin__do_not_disconnect,
                    Some(theme::ICON_INFO),
                )),
            ),
            None => (None, None),
        };

        // Homebar
        let (style_sheet, gradient) = button_homebar_style(notification.map(|n| n.level));
        let btn = Button::new(Self::homebar_content(bootscreen, locked))
            .styled(style_sheet)
            .with_gradient(gradient);

        Ok(Self {
            status: HomescreenStatus::new(label.clone(), image.is_some()),
            hint,
            action_bar: ActionBar::new_single(btn),
            image,
            led_color,
            locked,
            bootscreen,
            swipe: Swipe::new().up(),
        })
    }

    fn homebar_content(bootscreen: bool, locked: bool) -> ButtonContent {
        let text = (bootscreen || locked).then_some(TR::lockscreen__unlock.into());
        ButtonContent::HomeBar(text)
    }

    fn get_notification_display(n: &Notification) -> (Color, Hint<'static>) {
        match n.level {
            NotificationLevel::Alert => (theme::LED_RED, Hint::new_warning_danger(n.text)),
            NotificationLevel::Warning => (theme::LED_YELLOW, Hint::new_warning_neutral(n.text)),
            NotificationLevel::Info => (theme::LED_BLUE, Hint::new_instruction(n.text, None)),
            NotificationLevel::Success => (
                theme::LED_GREEN_LIGHT,
                Hint::new_instruction_green(n.text, Some(theme::ICON_INFO)),
            ),
        }
    }
}

impl Component for Homescreen {
    type Msg = HomescreenMsg;

    fn place(&mut self, bounds: Rect) -> Rect {
        // assert full screen
        debug_assert_eq!(bounds.height(), SCREEN.height());
        debug_assert_eq!(bounds.width(), SCREEN.width());

        let (rest, bar_area) = bounds.split_bottom(theme::ACTION_BAR_HEIGHT);
        let status_area = if let Some(hint) = &mut self.hint {
            let (rest, hint_area) = rest.split_bottom(hint.height());
            hint.place(hint_area);
            rest
        } else {
            rest
        };

        self.status.place(status_area.inset(theme::SIDE_INSETS));
        self.action_bar.place(bar_area);
        // Swipe component is placed in the action bar touch area
        self.swipe.place(self.action_bar.touch_area());
        bounds
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        self.status.event(ctx, event);
        let swipe_up = matches!(self.swipe.event(ctx, event), Some(Direction::Up));
        let homebar_tap = matches!(
            self.action_bar.event(ctx, event),
            Some(ActionBarMsg::Confirmed)
        );
        if swipe_up || homebar_tap {
            return if self.locked {
                Some(HomescreenMsg::Dismissed)
            } else {
                Some(HomescreenMsg::Menu)
            };
        }

        None
    }

    fn render<'s>(&'s self, target: &mut impl Renderer<'s>) {
        if let Some(image) = self.image {
            if let ImageInfo::Jpeg(_) = ImageInfo::parse(image) {
                shape::JpegImage::new_image(SCREEN.top_left(), image).render(target);
            }
        } else {
            ScreenBackground::new(self.led_color, None).render(target);
        }
        self.status.render(target);
        self.hint.render(target);
        self.action_bar.render(target);

        #[cfg(feature = "rgb_led")]
        target.set_led_state(LedState::Static(
            self.led_color.unwrap_or_else(Color::black),
        ));
    }
}

/// Helper component that displays device name label, battery status, and
/// connection status indicator.
/// It is combined because the label is shown together with the fuel gauge and
/// connection indicator when a custom background image is used.
struct HomescreenStatus {
    area: Rect,
    /// Device name
    label: Label<'static>,
    /// Fuel gauge (battery status indicator)
    fuel_gauge: FuelGauge,
    /// Whether the device is connected to Host (either via USB or BLE)
    connection_indicator: ConnectionIndicator,
    /// Whether a custom background image is used, which affects the layout and
    /// styling of the label
    background_image: bool,
    /// Cached text width of the label when a custom background image is used
    text_width: Option<i16>,
}

impl HomescreenStatus {
    const MAX_LABEL_WIDTH: i16 = 220;
    const LABEL_TEXT_STYLE_DEFAULT: TextStyle = theme::firmware::TEXT_BIG;
    const LABEL_TEXT_STYLE_WITH_IMG: TextStyle = theme::firmware::TEXT_SMALL;

    pub fn new(label: TString<'static>, background_image: bool) -> Self {
        let style = if background_image {
            Self::LABEL_TEXT_STYLE_WITH_IMG
        } else {
            Self::LABEL_TEXT_STYLE_DEFAULT
        };

        let text_width = if background_image {
            let width =
                label.map(|text| Self::LABEL_TEXT_STYLE_WITH_IMG.text_font.text_width(text));
            let width = clamp_max(width, Self::MAX_LABEL_WIDTH);
            Some(width)
        } else {
            None
        };

        Self {
            area: Rect::zero(),
            label: Label::left_aligned(label, style).top_aligned(),
            fuel_gauge: FuelGauge::always_icon_only(),
            connection_indicator: ConnectionIndicator::new(),
            background_image,
            text_width,
        }
    }

    fn render_pill_shaped_background<'s>(&'s self, area: Rect, target: &mut impl Renderer<'s>) {
        shape::Bar::new(area)
            .with_bg(theme::BG)
            .with_fg(theme::BG)
            .with_radius(27)
            .with_alpha(230) // 90%
            .render(target);
    }
}

impl Component for HomescreenStatus {
    type Msg = Never;

    fn place(&mut self, bounds: Rect) -> Rect {
        const LABEL_INSETS_DEFAULT: Insets = Insets::new(83, 24, 24, 0);
        const ICON_PERCENT_GAP: i16 = 16; // TODO: put to theme?
        let (header_area, _) = bounds.split_top(theme::HEADER_HEIGHT);
        let (fuel_gauge_area, _) = header_area.split_left(self.fuel_gauge.content_width());
        let connection_indicator_area = Rect::snap(
            fuel_gauge_area.right_center(),
            Offset::uniform(ConnectionIndicator::AREA_SIZE_NEEDED),
            Alignment2D::CENTER_LEFT,
        )
        .translate(Offset::x(ICON_PERCENT_GAP));

        let label_area = if !self.background_image {
            bounds.inset(LABEL_INSETS_DEFAULT)
        } else {
            let anchor = if self.connection_indicator.connected {
                connection_indicator_area.right_center()
            } else {
                fuel_gauge_area.right_center()
            };
            Rect::snap(
                anchor,
                Offset::new(
                    self.text_width.unwrap_or(0),
                    Self::LABEL_TEXT_STYLE_WITH_IMG.text_font.max_height,
                ),
                Alignment2D::CENTER_LEFT,
            )
            .translate(Offset::x(ICON_PERCENT_GAP))
        };

        self.fuel_gauge.place(fuel_gauge_area);
        self.connection_indicator.place(connection_indicator_area);
        self.label.place(label_area);
        self.area = bounds;
        self.area
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        self.fuel_gauge.event(ctx, event);
        let connection_event = self.connection_indicator.event(ctx, event);
        if matches!(event, Event::PM(_)) || connection_event.is_some() {
            // TODO: could FuelGauge also return Some(()) on update?
            self.place(self.area);
            ctx.request_paint();
        }
        None
    }

    fn render<'s>(&'s self, target: &mut impl Renderer<'s>) {
        if self.background_image {
            // render pill-shaped background for label to improve readability on
            // top of custom image
            let mut size_x = if self.connection_indicator.connected {
                self.connection_indicator.area.right_center().x
            } else {
                self.fuel_gauge.area.right_center().x
            };
            size_x += self.text_width.unwrap_or(0) + 2 * 16; // text width + gap on both sides
            let size = Offset::new(size_x, 54);
            let area = Rect::from_top_left_and_size(
                Point::new(0, 21) - Offset::x(27),
                size + Offset::x(27),
            );
            self.render_pill_shaped_background(area, target);
        }
        self.label.render(target);
        self.fuel_gauge.render(target);
        self.connection_indicator.render(target);
    }
}

pub fn check_homescreen_format(image: BinaryData) -> bool {
    match ImageInfo::parse(image) {
        ImageInfo::Jpeg(info) => {
            info.width() == WIDTH && info.height() == HEIGHT && info.mcu_height() <= 16
        }
        _ => false,
    }
}

fn get_homescreen_image() -> Option<BinaryData<'static>> {
    if let Ok(image) = get_user_custom_image() {
        if check_homescreen_format(image) {
            return Some(image);
        }
    }
    None
}

#[cfg(feature = "ui_debug")]
impl crate::trace::Trace for Homescreen {
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.component("Homescreen");
        t.child("status", &self.status);
        t.child("homebar", &self.action_bar);
    }
}
#[cfg(feature = "ui_debug")]
impl crate::trace::Trace for HomescreenStatus {
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.component("HomescreenStatus");
        t.child("label", &self.label);
        t.child("fuel_gauge", &self.fuel_gauge);
        t.child("connection_indicator", &self.connection_indicator);
    }
}
