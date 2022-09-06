use crate::{
    time::Instant,
    ui::{
        component::{Component, Event, EventCtx},
        event::ButtonEvent,
        geometry::{Point, Rect},
        model_tr::component::{loader::Loader, ButtonPos, LoaderMsg, LoaderStyleSheet},
    },
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
    text_width: i16,
}

impl HoldToConfirm {
    pub fn new(pos: ButtonPos, text: &'static str, styles: LoaderStyleSheet) -> Self {
        let text_width = styles.normal.font.text_width(text.as_ref());
        Self {
            area: Rect::zero(),
            pos,
            loader: Loader::new(text, styles),
            baseline: Point::zero(),
            text_width,
        }
    }

    fn placement(&mut self, area: Rect, pos: ButtonPos) -> Rect {
        let button_width = self.text_width + 7;
        match pos {
            ButtonPos::Left => area.split_left(button_width).0,
            ButtonPos::Right => area.split_right(button_width).1,
        }
    }
}

impl Component for HoldToConfirm {
    type Msg = HoldToConfirmMsg;

    fn place(&mut self, bounds: Rect) -> Rect {
        let loader_area = self.placement(bounds, self.pos);
        self.loader.place(loader_area)
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
    fn trace(&self, d: &mut dyn crate::trace::Tracer) {
        d.open("HoldToConfirm");
        self.loader.trace(d);
        d.close();
    }
}
