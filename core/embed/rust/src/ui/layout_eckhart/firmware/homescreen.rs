#[cfg(feature = "rgb_led")]
use crate::trezorhal::rgb_led;

use crate::{
    error::Error,
    io::BinaryData,
    strutil::TString,
    translations::TR,
    ui::{
        component::{text::TextStyle, Component, Event, EventCtx, Label, Never, Swipe},
        display::{image::ImageInfo, Color},
        geometry::{Alignment, Direction, Insets, Offset, Rect},
        layout::util::get_user_custom_image,
        shape::{self, Renderer},
        util::animation_disabled,
    },
};

use super::{
    super::{
        component::{Button, ButtonContent, FuelGauge},
        fonts,
    },
    constant::{HEIGHT, SCREEN, WIDTH},
    theme::{self, firmware::button_homebar_style, ScreenBackground},
    ActionBar, ActionBarMsg, Hint,
};

/// Full-screen component for the homescreen and lockscreen.
pub struct Homescreen {
    /// Device name with shadow
    label: HomeLabel,
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
    /// Fuel gauge (battery status indicator) rendered in the `action_bar` area
    fuel_gauge: FuelGauge,
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
        notification: Option<(TString<'static>, u8)>,
    ) -> Result<Self, Error> {
        let image = get_homescreen_image();
        let shadow = image.is_some();

        // Notification
        let mut notification_level = 4;
        let (led_color, hint) = match notification {
            Some((text, level)) => {
                notification_level = level;
                let (led_color, hint) = Self::get_notification_display(level, text);
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
        let (style_sheet, gradient) = button_homebar_style(notification_level);
        let btn = Button::new(Self::homebar_content(bootscreen, locked))
            .styled(style_sheet)
            .with_gradient(gradient);

        Ok(Self {
            label: HomeLabel::new(label, shadow),
            hint,
            action_bar: ActionBar::new_single(btn),
            image,
            led_color,
            locked,
            bootscreen,
            fuel_gauge: FuelGauge::homescreen_bar()
                .with_alignment(Alignment::Center)
                .with_font(fonts::FONT_SATOSHI_MEDIUM_26),
            swipe: Swipe::new().up(),
        })
    }

    fn homebar_content(bootscreen: bool, locked: bool) -> ButtonContent {
        let text = if bootscreen {
            Some(TR::instructions__tap_to_start.into())
        } else if locked {
            Some(TR::lockscreen__unlock.into())
        } else {
            None
        };
        ButtonContent::HomeBar(text)
    }

    fn get_notification_display(level: u8, text: TString<'static>) -> (Color, Hint<'static>) {
        match level {
            0 => (theme::LED_RED, Hint::new_warning_danger(text)),
            1 => (theme::LED_YELLOW, Hint::new_warning_neutral(text)),
            2 => (theme::LED_BLUE, Hint::new_instruction(text, None)),
            3 => (
                theme::LED_GREEN_LIGHT,
                Hint::new_instruction_green(text, Some(theme::ICON_INFO)),
            ),
            _ => (
                theme::LED_WHITE,
                Hint::new_instruction(text, Some(theme::ICON_INFO)),
            ),
        }
    }

    fn event_fuel_gauge(&mut self, ctx: &mut EventCtx, event: Event) {
        if animation_disabled() {
            return;
        }

        self.fuel_gauge.event(ctx, event);
        let bar_content = if self.fuel_gauge.should_be_shown() {
            ButtonContent::Empty
        } else {
            Self::homebar_content(self.bootscreen, self.locked)
        };

        if let Some(b) = self.action_bar.right_button_mut() {
            b.set_content(bar_content)
        }
    }
}

impl Drop for Homescreen {
    fn drop(&mut self) {
        // Turn off the LED when homescreen is destroyed
        #[cfg(feature = "rgb_led")]
        rgb_led::set_color(0);
    }
}

impl Component for Homescreen {
    type Msg = HomescreenMsg;

    fn place(&mut self, bounds: Rect) -> Rect {
        // assert full screen
        debug_assert_eq!(bounds.height(), SCREEN.height());
        debug_assert_eq!(bounds.width(), SCREEN.width());

        let (rest, bar_area) = bounds.split_bottom(theme::ACTION_BAR_HEIGHT);
        let rest = if let Some(hint) = &mut self.hint {
            let (rest, hint_area) = rest.split_bottom(hint.height());
            hint.place(hint_area);
            rest
        } else {
            rest
        };
        let label_area = rest.inset(theme::CONTENT_INSETS_NO_HEADER);

        self.label.place(label_area);
        self.action_bar.place(bar_area);
        self.fuel_gauge.place(bar_area);
        // Swipe component is placed in the action bar touch area
        self.swipe.place(self.action_bar.touch_area());
        bounds
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        self.event_fuel_gauge(ctx, event);

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
        self.label.render(target);
        self.hint.render(target);
        self.action_bar.render(target);
        if self.fuel_gauge.should_be_shown() {
            self.fuel_gauge.render(target);
        }

        #[cfg(feature = "rgb_led")]
        if let Some(rgb_led) = self.led_color {
            rgb_led::set_color(rgb_led.to_u32());
        } else {
            rgb_led::set_color(0);
        }
    }
}

/// Helper component to render a label with a shadow.
struct HomeLabel {
    label: Label<'static>,
    /// Label shadow, only rendered when custom homescreen image is set
    label_shadow: Option<Label<'static>>,
}

impl HomeLabel {
    const LABEL_SHADOW_OFFSET: Offset = Offset::uniform(2);
    const LABEL_TEXT_STYLE: TextStyle = theme::firmware::TEXT_BIG;
    const LABEL_SHADOW_TEXT_STYLE: TextStyle = TextStyle::new(
        fonts::FONT_SATOSHI_EXTRALIGHT_46,
        theme::BLACK,
        theme::BLACK,
        theme::BLACK,
        theme::BLACK,
    );

    fn new(label: TString<'static>, shadow: bool) -> Self {
        let label_primary = Label::left_aligned(label, Self::LABEL_TEXT_STYLE).top_aligned();
        let label_shadow = shadow
            .then_some(Label::left_aligned(label, Self::LABEL_SHADOW_TEXT_STYLE).top_aligned());
        Self {
            label: label_primary,
            label_shadow,
        }
    }

    fn inner(&self) -> &Label<'static> {
        &self.label
    }
}

impl Component for HomeLabel {
    type Msg = Never;
    fn place(&mut self, bounds: Rect) -> Rect {
        self.label.place(bounds);
        self.label_shadow
            .place(bounds.translate(Self::LABEL_SHADOW_OFFSET));
        bounds
    }
    fn event(&mut self, _ctx: &mut EventCtx, _event: Event) -> Option<Self::Msg> {
        None
    }
    fn render<'s>(&'s self, target: &mut impl Renderer<'s>) {
        self.label_shadow.render(target);
        self.label.render(target);
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
        t.child("label", self.label.inner());
    }
}
