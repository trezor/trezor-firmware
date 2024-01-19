use core::mem;

use crate::{
    strutil::StringType,
    translations::TR,
    ui::{
        component::{
            base::Never,
            text::util::{text_multiline, text_multiline_bottom},
            Component, Event, EventCtx,
        },
        display::{self, Font},
        geometry::{Alignment, Insets, Rect},
        util::animation_disabled,
    },
};

use super::theme;

const FOOTER_TEXT_MARGIN: i16 = 8;
const LOADER_OFFSET: i16 = -15;
const LOADER_SPEED: u16 = 10;

pub struct CoinJoinProgress<T> {
    value: u16,
    loader_y_offset: i16,
    text: T,
    area: Rect,
    indeterminate: bool,
}

impl<T> CoinJoinProgress<T>
where
    T: StringType,
{
    pub fn new(text: T, indeterminate: bool) -> Self {
        Self {
            value: 0,
            loader_y_offset: LOADER_OFFSET,
            text,
            area: Rect::zero(),
            indeterminate,
        }
    }
}

impl<T> Component for CoinJoinProgress<T>
where
    T: StringType,
{
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
                Event::Attach => {
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

    fn paint(&mut self) {
        // TOP
        if self.indeterminate {
            text_multiline(
                self.area,
                TR::coinjoin__title_progress.into(),
                Font::BOLD,
                theme::FG,
                theme::BG,
                Alignment::Center,
            );
            display::loader::loader_small_indeterminate(
                self.value,
                self.loader_y_offset,
                theme::FG,
                theme::BG,
            );
        } else {
            display::loader(
                self.value,
                self.loader_y_offset,
                theme::FG,
                theme::BG,
                Some((theme::ICON_TICK_FAT, theme::FG)),
            );
        }

        // BOTTOM
        let top_rest = text_multiline_bottom(
            self.area,
            TR::coinjoin__do_not_disconnect.into(),
            Font::BOLD,
            theme::FG,
            theme::BG,
            Alignment::Center,
        );
        if let Some(rest) = top_rest {
            text_multiline_bottom(
                rest.inset(Insets::bottom(FOOTER_TEXT_MARGIN)),
                self.text.as_ref().into(),
                Font::NORMAL,
                theme::FG,
                theme::BG,
                Alignment::Center,
            );
        }
    }
}

#[cfg(feature = "ui_debug")]
impl<T> crate::trace::Trace for CoinJoinProgress<T>
where
    T: StringType,
{
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.component("CoinJoinProgress");
        t.string("header", TR::coinjoin__title_progress.into());
        t.string("text", self.text.as_ref().into());
        t.string("footer", TR::coinjoin__do_not_disconnect.into());
    }
}
