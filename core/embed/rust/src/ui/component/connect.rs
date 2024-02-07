use crate::{
    strutil::TString,
    ui::{
        component::{Component, Event, EventCtx, Never, Pad},
        display::{self, Color, Font},
        geometry::{Offset, Rect},
    },
};

pub struct Connect {
    fg: Color,
    bg: Pad,
    message: TString<'static>,
}

impl Connect {
    pub fn new<T>(message: T, fg: Color, bg: Color) -> Self
    where
        T: Into<TString<'static>>,
    {
        let mut instance = Self {
            fg,
            bg: Pad::with_background(bg),
            message: message.into(),
        };

        instance.bg.clear();
        instance
    }
}

impl Component for Connect {
    type Msg = Never;

    fn place(&mut self, bounds: Rect) -> Rect {
        self.bg.place(bounds);
        bounds
    }

    fn event(&mut self, _ctx: &mut EventCtx, _event: Event) -> Option<Self::Msg> {
        None
    }

    fn paint(&mut self) {
        let font = Font::NORMAL;

        self.bg.paint();
        self.message.map(|t| {
            display::text_center(
                self.bg.area.center() + Offset::y(font.text_height() / 2),
                t,
                font,
                self.fg,
                self.bg.color,
            )
        });
    }
}

#[cfg(feature = "micropython")]
mod micropython {
    use crate::{error::Error, micropython::obj::Obj, ui::layout::obj::ComponentMsgObj};

    use super::Connect;

    impl ComponentMsgObj for Connect {
        fn msg_try_into_obj(&self, _msg: Self::Msg) -> Result<Obj, Error> {
            unreachable!()
        }
    }
}

#[cfg(feature = "ui_debug")]
impl crate::trace::Trace for Connect {
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.component("Connect");
        t.string("message", self.message);
    }
}
