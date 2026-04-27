use crate::{
    strutil::TString,
    time::Duration,
    translations::TR,
    ui::{
        component::{Component, Event, EventCtx, Never, Timer},
        display::Color,
        geometry::{Alignment2D, Offset, Rect},
        notification::{Notification, NotificationLevel},
        shape::Renderer,
        util::animation_disabled,
    },
};

use super::{
    super::{
        super::component::{Button, ButtonContent},
        theme::{self, firmware::button_homebar_style, ScreenBackground},
        Hint,
    },
    helpers::{render_pill_shaped_background, SHADOW_HEIGHT},
};

#[cfg(feature = "rgb_led")]
use crate::ui::led::LedState;

pub(super) struct HomescreenNotificationCenter {
    /// Current notification to display, if any
    notification: Option<Notification>,
    /// Whether the notification is actionable (i.e. has a corresponding entry
    /// in the DeviceMenu)
    pub(super) actionable_notification: bool,
    /// Notification text display
    hint: Option<Hint<'static>>,
    hint_shadow_area: Rect,
    /// LED color
    led_color: Option<Color>,
    /// Whether the LED is currently active
    led_active: bool,
    /// Timer for toggling the LED on/off
    led_timer: Timer,
    /// Whether a custom background image is used, which affects the UI
    background_image: bool,
    /// Whether the notification UI (hint/actionbar) has become visible.
    /// Starts false, becomes true after the first LED toggle duration,
    /// and stays true permanently.
    pub(super) notification_visible: bool,
}

impl HomescreenNotificationCenter {
    pub(super) fn new(
        notification: Option<Notification>,
        locked: bool,
        coinjoin_authorized: bool,
        background_image: bool,
    ) -> Self {
        // If there's a notification which has an entry in the DeviceMenu
        let actionable_notification = notification.as_ref().is_some_and(|n| n.actionable);

        let led_color = match notification {
            Some(ref notification) => Some(Self::get_notification_led_color(notification)),
            None if locked && coinjoin_authorized => Some(theme::LED_GREEN_LIME),
            None => None,
        };

        let hint = match notification {
            Some(ref n) if !n.actionable => Some(Self::get_notification_hint(n)),
            None if locked && coinjoin_authorized => Some(Hint::new_instruction_green(
                TR::coinjoin__do_not_disconnect,
                Some(theme::ICON_INFO),
            )),
            _ => None,
        };

        // Alerts are visible immediately
        let is_alert = notification
            .as_ref()
            .map(|n| matches!(n.level, NotificationLevel::Alert))
            .unwrap_or(false);
        let show_immediately = is_alert || animation_disabled();

        Self {
            notification,
            actionable_notification,
            hint,
            hint_shadow_area: Rect::zero(),
            led_color,
            led_active: false,
            led_timer: Timer::new(),
            background_image,
            notification_visible: show_immediately && led_color.is_some(),
        }
    }

    pub(super) fn homebar_button(&self, bootscreen: bool, locked: bool) -> Button {
        let text: Option<TString<'static>> = if bootscreen || locked {
            Some(TR::lockscreen__unlock.into())
        } else if self.actionable_notification {
            self.notification.as_ref().map(|n| n.text)
        } else {
            None
        };
        let level = self.notification.as_ref().map(|n| n.level);
        let (style_sheet, gradient) =
            button_homebar_style(level.as_ref(), self.actionable_notification);
        Button::new(ButtonContent::HomeBar(text))
            .styled(style_sheet)
            .with_gradient(gradient)
    }

    fn notification_level(&self) -> Option<NotificationLevel> {
        self.notification.as_ref().map(|n| n.level)
    }

    pub(super) fn is_alert(&self) -> bool {
        self.notification_level()
            .map(|level| matches!(level, NotificationLevel::Alert))
            .unwrap_or(false)
    }

    fn get_notification_led_color(n: &Notification) -> Color {
        match n.level {
            NotificationLevel::Alert => theme::LED_RED,
            NotificationLevel::Warning => theme::LED_YELLOW,
            NotificationLevel::Info => theme::LED_BLUE,
            NotificationLevel::Success => theme::LED_GREEN_LIGHT,
        }
    }

    fn get_notification_hint(n: &Notification) -> Hint<'static> {
        match n.level {
            NotificationLevel::Alert => Hint::new_warning_danger(n.text),
            NotificationLevel::Warning => Hint::new_warning_neutral(n.text),
            NotificationLevel::Info => Hint::new_instruction(n.text, None),
            NotificationLevel::Success => {
                Hint::new_instruction_green(n.text, Some(theme::ICON_INFO))
            }
        }
    }
}

impl Component for HomescreenNotificationCenter {
    type Msg = Never;
    fn place(&mut self, bounds: Rect) -> Rect {
        if let Some(hint) = &mut self.hint {
            let hint_height = hint.height();
            let hint_height_content = hint.height_no_padding().max(SHADOW_HEIGHT);
            let hint_width = hint.width();
            let (_rest, hint_area) = bounds.split_bottom(hint_height);

            let shadow_offset_x = Offset::x(hint_height_content / 2);
            let shadow_size = Offset::new(hint_width + theme::PADDING, hint_height_content)
                + shadow_offset_x * 2.0;
            // FIXME: hardcoded offset to properly center the shadow necessary due to
            // asymmetric insets of the HintContent::Instruction
            let shadow_anchor = hint_area.left_center() - shadow_offset_x - Offset::y(4);
            self.hint_shadow_area =
                Rect::snap(shadow_anchor, shadow_size, Alignment2D::CENTER_LEFT);
            hint.place(hint_area);
        }
        bounds
    }
    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        const LED_TOGGLE_DURATION: Duration = Duration::from_millis(3000);

        if self.led_color.is_some() {
            if self.is_alert() || animation_disabled() {
                // Alert: LED is always on, notification visible immediately
                if matches!(event, Event::Attach(_)) {
                    self.led_active = true;
                    self.notification_visible = true;
                    ctx.request_paint();
                }
            } else {
                match event {
                    Event::Attach(_) => {
                        // Start off, schedule turning on after LED_TOGGLE_DURATION
                        self.led_active = false;
                        self.notification_visible = false;
                        self.led_timer.start(ctx, LED_TOGGLE_DURATION);
                    }
                    Event::Timer(_) if self.led_timer.expire(event) => {
                        if !self.led_active {
                            // Turn on LED, make notification UI visible (permanently)
                            self.led_active = true;
                            self.notification_visible = true;
                            self.led_timer.start(ctx, LED_TOGGLE_DURATION);
                        } else {
                            // Turn off LED, but notification UI stays visible
                            self.led_active = false;
                        }
                        ctx.request_paint();
                    }
                    _ => {}
                }
            }
        }
        None
    }
    fn render<'s>(&'s self, target: &mut impl Renderer<'s>) {
        let active_color = if self.led_active {
            self.led_color
        } else {
            None
        };

        if self.background_image {
            // Only render hint shadow when notification is visible
            if self.notification_visible {
                render_pill_shaped_background(self.hint_shadow_area, target);
            }
        } else {
            // default homescreen
            ScreenBackground::new(active_color, None).render(target);
        }
        // Only render hint when notification has become visible
        if self.notification_visible {
            self.hint.render(target);
        }

        #[cfg(feature = "rgb_led")]
        target.set_led_state(LedState::Static(active_color.unwrap_or_else(Color::black)));
    }
}
