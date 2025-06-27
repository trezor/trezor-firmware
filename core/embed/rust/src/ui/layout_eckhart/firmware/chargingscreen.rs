use crate::{
    error::Error,
    time::ShortDuration,
    trezorhal::power_manager::{self, ChargingState},
    ui::{
        component::{Component, Label},
        geometry::Rect,
    },
};

use super::{super::theme, constant::SCREEN};

const CHARGING_ANIM_DURATION: ShortDuration = ShortDuration::from_millis(2000);

/// Full-screen component for showing temporary charging animation.
pub struct Chargingscreen {
    label_charging: Label<'static>,
}

pub enum ChargingscreenMsg {
    /// Dismiss the charging screen.
    Dismissed,
}

impl Chargingscreen {
    pub fn new() -> Result<Self, Error> {
        Ok(Self {
            label_charging: Label::centered("Charging".into(), theme::TEXT_MEDIUM_GREY)
                .vertically_centered(),
        })
    }
}

impl Component for Chargingscreen {
    type Msg = ChargingscreenMsg;

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
        let label_area = rest
            .inset(theme::SIDE_INSETS)
            .inset(Insets::top(theme::PADDING));

        self.label.place(label_area);
        self.action_bar.place(bar_area);
        self.fuel_gauge.place(bar_area);
        // Locking button is placed everywhere except the action bar
        let locking_area = bounds.inset(Insets::bottom(self.action_bar.touch_area().height()));
        self.virtual_locking_button.place(locking_area);
        bounds
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        self.event_fuel_gauge(ctx, event);
        if let Some(ActionBarMsg::Confirmed) = self.action_bar.event(ctx, event) {
            if self.locked {
                return Some(HomescreenMsg::Dismissed);
            } else {
                return Some(HomescreenMsg::Menu);
            }
        }
        if self.lockable {
            Self::event_hold(self, ctx, event).then_some(HomescreenMsg::Dismissed)
        } else {
            None
        }
    }

    fn render<'s>(&'s self, target: &mut impl Renderer<'s>) {
        if let Some(image) = self.image {
            if let ImageInfo::Jpeg(_) = ImageInfo::parse(image) {
                shape::JpegImage::new_image(SCREEN.top_left(), image).render(target);
            }
        } else {
            render_default_hs(target, self.led_color);
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
