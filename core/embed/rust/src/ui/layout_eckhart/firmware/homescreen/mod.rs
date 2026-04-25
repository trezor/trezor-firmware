mod header;
mod helpers;
mod notification_center;

use header::HomescreenHeader;
use helpers::get_homescreen_image;
use notification_center::HomescreenNotificationCenter;

pub use helpers::check_homescreen_format;

use crate::{
    error::Error,
    io::BinaryData,
    strutil::TString,
    translations::TR,
    ui::{
        component::{Component, Event, EventCtx, Swipe},
        display::image::ImageInfo,
        geometry::{Direction, Rect},
        notification::Notification,
        shape::{self, Renderer},
        util::animation_disabled,
    },
};

use super::{
    super::component::{Button, ButtonContent},
    constant::SCREEN,
    theme::{self, firmware::button_homebar_style},
    ActionBar, ActionBarMsg,
};

/// Full-screen component for the homescreen and lockscreen.
pub struct Homescreen {
    /// Device name label, fuel gauge, and connection status
    header: HomescreenHeader,
    /// Notification rendering, including LED and hint text
    notification_center: HomescreenNotificationCenter,
    /// Home action bar
    action_bar: ActionBar,
    /// Background image
    image: Option<BinaryData<'static>>,
    /// Whether the homescreen is locked
    locked: bool,
    /// Whether the homescreen is a boot screen
    bootscreen: bool,
    /// Swipe component for vertical swiping
    swipe: Swipe,
    /// Notification homebar button (with notification style), if applicable
    notification_btn: Option<Button>,
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
        let image_used = image.is_some();

        let notification_center = HomescreenNotificationCenter::new(
            notification,
            locked,
            coinjoin_authorized,
            image_used,
        );

        // Build the default homebar (as if no notification)
        let default_btn = Self::make_default_homebar(bootscreen, locked);
        // Build the notification homebar if there's an actionable notification
        let notification_btn = if notification_center.actionable_notification {
            Some(notification_center.homebar_button(bootscreen, locked))
        } else {
            None
        };

        let is_alert = notification_center.is_alert();
        let show_immediately = is_alert || animation_disabled();

        // Start with default button unless notification shows immediately
        let initial_btn = if show_immediately && notification_btn.is_some() {
            notification_center.homebar_button(bootscreen, locked)
        } else {
            default_btn
        };

        Ok(Self {
            header: HomescreenHeader::new(label, image_used, !is_alert),
            notification_center,
            action_bar: ActionBar::new_single(initial_btn),
            image,
            locked,
            bootscreen,
            swipe: Swipe::new().up(),
            notification_btn,
        })
    }

    /// Build a homebar button with default style (no notification)
    fn make_default_homebar(bootscreen: bool, locked: bool) -> Button {
        let text: Option<TString<'static>> = if bootscreen || locked {
            Some(TR::lockscreen__unlock.into())
        } else {
            None
        };
        let (style_sheet, gradient) = button_homebar_style(None, false);
        Button::new(ButtonContent::HomeBar(text))
            .styled(style_sheet)
            .with_gradient(gradient)
    }
}

impl Component for Homescreen {
    type Msg = HomescreenMsg;

    fn place(&mut self, bounds: Rect) -> Rect {
        // assert full screen
        debug_assert_eq!(bounds.height(), SCREEN.height());
        debug_assert_eq!(bounds.width(), SCREEN.width());

        let (rest, bar_area) = bounds.split_bottom(theme::ACTION_BAR_HEIGHT);
        let (status_area, rest) = rest.split_top(theme::HEADER_HEIGHT);

        self.header.place(status_area.inset(theme::SIDE_INSETS));
        self.notification_center.place(rest);
        self.action_bar.place(bar_area);
        // Swipe component is placed in the action bar touch area
        self.swipe.place(self.action_bar.touch_area());
        bounds
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        self.header.event(ctx, event);
        self.notification_center.event(ctx, event);

        // Swap action bar to notification style when notification becomes visible
        if self.notification_center.notification_visible {
            if let Some(btn) = self.notification_btn.take() {
                self.action_bar = ActionBar::new_single(btn);
                // Re-place the action bar in its area
                let bar_area = SCREEN.split_bottom(theme::ACTION_BAR_HEIGHT).1;
                self.action_bar.place(bar_area);
                self.swipe.place(self.action_bar.touch_area());
                ctx.request_paint();
            }
        }

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
        }
        self.notification_center.render(target);
        self.header.render(target);
        self.action_bar.render(target);
    }
}

#[cfg(feature = "ui_debug")]
impl crate::trace::Trace for Homescreen {
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.component("Homescreen");
        t.child("status", &self.header);
        t.child("homebar", &self.action_bar);
    }
}
