use crate::{
    io::BinaryData,
    ui::{
        component::{Component, Event, EventCtx, Never},
        geometry::{Alignment2D, Rect},
        shape,
        shape::Renderer,
    },
};

pub struct Jpeg {
    area: Rect,
    image: BinaryData<'static>,
    scale: u8,
}

impl Jpeg {
    pub fn new(image: BinaryData<'static>, scale: u8) -> Self {
        Self {
            area: Rect::zero(),
            image,
            scale,
        }
    }
}

impl Component for Jpeg {
    type Msg = Never;

    fn place(&mut self, bounds: Rect) -> Rect {
        self.area = bounds;
        self.area
    }

    fn event(&mut self, _ctx: &mut EventCtx, _event: Event) -> Option<Self::Msg> {
        None
    }

    fn render<'s>(&'s self, target: &mut impl Renderer<'s>) {
        shape::JpegImage::new_image(self.area.center(), self.image)
            .with_align(Alignment2D::CENTER)
            .with_scale(self.scale)
            .render(target);
    }
}

#[cfg(feature = "ui_debug")]
impl crate::trace::Trace for Jpeg {
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.component("Jpeg");
    }
}

#[cfg(feature = "micropython")]
mod micropython {
    use crate::{error::Error, micropython::obj::Obj, ui::layout::obj::ComponentMsgObj};
    impl ComponentMsgObj for super::Jpeg {
        fn msg_try_into_obj(&self, _msg: Self::Msg) -> Result<Obj, Error> {
            unreachable!();
        }
    }
}
