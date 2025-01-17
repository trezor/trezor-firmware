use crate::ui::{
    component::{Component, Event, EventCtx, Never},
    geometry::{Alignment2D, Offset, Rect},
    shape,
    shape::Renderer,
};

use super::super::theme;

const ICON_TOP_MARGIN: i16 = 12;

pub struct WelcomeScreen {
    area: Rect,
    empty_lock: bool,
}

impl WelcomeScreen {
    pub fn new(empty_lock: bool) -> Self {
        Self {
            area: Rect::zero(),
            empty_lock,
        }
    }
}

impl Component for WelcomeScreen {
    type Msg = Never;

    fn place(&mut self, bounds: Rect) -> Rect {
        self.area = bounds;
        self.area
    }

    fn event(&mut self, _ctx: &mut EventCtx, _event: Event) -> Option<Self::Msg> {
        None
    }

    fn render<'s>(&'s self, target: &mut impl Renderer<'s>) {
        shape::ToifImage::new(
            self.area.bottom_center() - Offset::y(5),
            theme::ICON_DEVICE_NAME.toif,
        )
        .with_align(Alignment2D::BOTTOM_CENTER)
        .with_fg(theme::FG)
        .render(target);

        let icon = if self.empty_lock {
            theme::ICON_LOGO_EMPTY
        } else {
            theme::ICON_LOGO
        };

        shape::ToifImage::new(
            self.area.top_center() + Offset::y(ICON_TOP_MARGIN),
            icon.toif,
        )
        .with_align(Alignment2D::TOP_CENTER)
        .with_fg(theme::FG)
        .render(target);
    }
}

#[cfg(feature = "ui_debug")]
impl crate::trace::Trace for WelcomeScreen {
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.component("WelcomeScreen");
        t.string("model_name", "Trezor Safe 3".into());
    }
}
