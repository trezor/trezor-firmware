use crate::ui::{
    component::{Component, Event, EventCtx, Timeout},
    display::{Color, Icon},
    geometry::{Alignment2D, Rect},
    shape,
    shape::Renderer,
};

use super::{theme, Swipe, SwipeDirection};

/// Component showing status of an operation. Most typically embedded as a
/// content of a Frame and showing success (checkmark with a circle around).
pub struct StatusScreen {
    area: Rect,
    icon: Icon,
    icon_color: Color,
    circle_color: Color,
    dismiss_type: DismissType,
}

enum DismissType {
    SwipeUp(Swipe),
    Timeout(Timeout),
}

const TIMEOUT_MS: u32 = 2000;

impl StatusScreen {
    fn new(icon: Icon, icon_color: Color, circle_color: Color, dismiss_style: DismissType) -> Self {
        Self {
            area: Rect::zero(),
            icon,
            icon_color,
            circle_color,
            dismiss_type: dismiss_style,
        }
    }

    pub fn new_success() -> Self {
        Self::new(
            theme::ICON_SIMPLE_CHECKMARK,
            theme::GREEN_LIME,
            theme::GREEN_LIGHT,
            DismissType::SwipeUp(Swipe::new().up()),
        )
    }

    pub fn new_success_timeout() -> Self {
        Self::new(
            theme::ICON_SIMPLE_CHECKMARK,
            theme::GREEN_LIME,
            theme::GREEN_LIGHT,
            DismissType::Timeout(Timeout::new(TIMEOUT_MS)),
        )
    }

    pub fn new_neutral() -> Self {
        Self::new(
            theme::ICON_SIMPLE_CHECKMARK,
            theme::GREY_EXTRA_LIGHT,
            theme::GREY_DARK,
            DismissType::SwipeUp(Swipe::new().up()),
        )
    }

    pub fn new_neutral_timeout() -> Self {
        Self::new(
            theme::ICON_SIMPLE_CHECKMARK,
            theme::GREY_EXTRA_LIGHT,
            theme::GREY_DARK,
            DismissType::Timeout(Timeout::new(TIMEOUT_MS)),
        )
    }
}

impl Component for StatusScreen {
    type Msg = ();

    fn place(&mut self, bounds: Rect) -> Rect {
        self.area = bounds;
        if let DismissType::SwipeUp(swipe) = &mut self.dismiss_type {
            swipe.place(bounds);
        }
        bounds
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        match self.dismiss_type {
            DismissType::SwipeUp(ref mut swipe) => {
                let swipe_dir = swipe.event(ctx, event);
                match swipe_dir {
                    Some(SwipeDirection::Up) => return Some(()),
                    _ => (),
                }
            }
            DismissType::Timeout(ref mut timeout) => {
                if let Some(_) = timeout.event(ctx, event) {
                    return Some(());
                }
            }
        }

        None
    }

    fn paint(&mut self) {
        todo!()
    }

    fn render<'s>(&'s self, target: &mut impl Renderer<'s>) {
        shape::Circle::new(self.area.center(), 40)
            .with_fg(self.circle_color)
            .with_bg(theme::BLACK)
            .with_thickness(2)
            .render(target);
        shape::ToifImage::new(self.area.center(), self.icon.toif)
            .with_align(Alignment2D::CENTER)
            .with_fg(self.icon_color)
            .render(target);
    }
}

#[cfg(feature = "ui_debug")]
impl crate::trace::Trace for StatusScreen {
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.component("StatusScreen");
    }
}
