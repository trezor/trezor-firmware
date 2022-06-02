use crate::time::Instant;
use crate::ui::event::ButtonEvent;
use crate::ui::model_tr::component::loader::Loader;
use crate::ui::model_tr::component::{ButtonPos, LoaderMsg, LoaderStyle, LoaderStyleSheet};
use crate::ui::model_tr::theme::FONT_NORMAL;
use crate::ui::model_tr::theme::{BG, FG};
use crate::ui::{
    component::{Component, Event, EventCtx},
    geometry::{Point, Rect},
};

pub enum HoldToConfirmMsg {
    Confirmed,
    FailedToConfirm,
}

pub struct HoldToConfirm {
    area: Rect,
    pos: ButtonPos,
    loader: Loader,
    baseline: Point,
}

pub fn loader_default() -> LoaderStyleSheet {
    LoaderStyleSheet {
        normal: &LoaderStyle {
            font: FONT_NORMAL,
            fg_color: FG,
            bg_color: BG,
        },
    }
}

impl HoldToConfirm {
    pub fn new(pos: ButtonPos, text: &'static str) -> Self {
        Self {
            area: Rect::zero(),
            pos,
            loader: Loader::new(text, loader_default()),
            baseline: Point::zero(),
        }
    }
}

impl Component for HoldToConfirm {
    type Msg = HoldToConfirmMsg;

    fn place(&mut self, bounds: Rect) -> Rect {
        self.loader.place(bounds)
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        match event {
            Event::Button(ButtonEvent::ButtonPressed(which)) if self.pos.hit(&which) => {
                self.loader.start_growing(ctx, Instant::now());
            }
            Event::Button(ButtonEvent::ButtonReleased(which)) if self.pos.hit(&which) => {
                if self.loader.is_animating() {
                    self.loader.start_shrinking(ctx, Instant::now());
                }
            }
            _ => {}
        };

        let msg = self.loader.event(ctx, event);

        if let Some(LoaderMsg::GrownCompletely) = msg {
            return Some(HoldToConfirmMsg::Confirmed);
        }
        if let Some(LoaderMsg::ShrunkCompletely) = msg {
            return Some(HoldToConfirmMsg::FailedToConfirm);
        }

        None
    }

    fn paint(&mut self) {
        self.loader.paint();
    }
}

#[cfg(feature = "ui_debug")]
impl crate::trace::Trace for HoldToConfirm {
    fn trace(&self, _t: &mut dyn crate::trace::Tracer) {}
}
