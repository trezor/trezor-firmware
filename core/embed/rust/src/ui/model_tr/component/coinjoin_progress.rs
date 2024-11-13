use core::mem;

use crate::{
    strutil::TString,
    translations::TR,
    ui::{
        component::{
            base::Never,
            text::util::{text_multiline, text_multiline_bottom},
            Component, Event, EventCtx,
        },
        display::Font,
        geometry::{Alignment, Alignment2D, Insets, Offset, Rect},
        model_tr::cshape,
        shape,
        shape::Renderer,
        util::animation_disabled,
    },
};

use super::theme;

const FOOTER_TEXT_MARGIN: i16 = 8;
const LOADER_OFFSET: i16 = -15;
const LOADER_SPEED: u16 = 10;

pub struct CoinJoinProgress {
    value: u16,
    loader_y_offset: i16,
    text: TString<'static>,
    area: Rect,
    indeterminate: bool,
}

impl CoinJoinProgress {
    pub fn new(text: TString<'static>, indeterminate: bool) -> Self {
        Self {
            value: 0,
            loader_y_offset: LOADER_OFFSET,
            text,
            area: Rect::zero(),
            indeterminate,
        }
    }
}

impl Component for CoinJoinProgress {
    type Msg = Never;

    fn place(&mut self, bounds: Rect) -> Rect {
        self.area = bounds;
        bounds
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        if animation_disabled() {
            return None;
        }

        // Indeterminate needs to request frames to animate.
        // Determinate ones are receiving Event::Progress events.
        if self.indeterminate {
            match event {
                Event::Attach(_) => {
                    ctx.request_anim_frame();
                }
                Event::Timer(EventCtx::ANIM_FRAME_TIMER) => {
                    self.value = (self.value + LOADER_SPEED) % 1000;
                    ctx.request_anim_frame();
                    ctx.request_paint();
                }
                _ => {}
            }
        } else if let Event::Progress(new_value, _new_description) = event {
            if mem::replace(&mut self.value, new_value) != new_value {
                ctx.request_paint();
            }
        }

        None
    }

    fn render<'s>(&'s self, target: &mut impl Renderer<'s>) {
        // TOP
        let center = self.area.center() + Offset::y(self.loader_y_offset);

        if self.indeterminate {
            text_multiline(
                target,
                self.area,
                TR::coinjoin__title_progress.into(),
                Font::BOLD,
                theme::FG,
                theme::BG,
                Alignment::Center,
            );
            cshape::LoaderSmall::new(center, self.value)
                .with_color(theme::FG)
                .render(target);
        } else {
            cshape::LoaderCircular::new(center, self.value)
                .with_color(theme::FG)
                .render(target);
            shape::ToifImage::new(center, theme::ICON_TICK_FAT.toif)
                .with_align(Alignment2D::CENTER)
                .with_fg(theme::FG)
                .render(target);
        }

        // BOTTOM
        let top_rest = text_multiline_bottom(
            target,
            self.area,
            TR::coinjoin__do_not_disconnect.into(),
            Font::BOLD,
            theme::FG,
            theme::BG,
            Alignment::Center,
        );
        if let Some(rest) = top_rest {
            text_multiline_bottom(
                target,
                rest.inset(Insets::bottom(FOOTER_TEXT_MARGIN)),
                self.text,
                Font::NORMAL,
                theme::FG,
                theme::BG,
                Alignment::Center,
            );
        }
    }
}

#[cfg(feature = "ui_debug")]
impl crate::trace::Trace for CoinJoinProgress {
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.component("CoinJoinProgress");
        t.string("header", TR::coinjoin__title_progress.into());
        t.string("text", self.text);
        t.string("footer", TR::coinjoin__do_not_disconnect.into());
    }
}
