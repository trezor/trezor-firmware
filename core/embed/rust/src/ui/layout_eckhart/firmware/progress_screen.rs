use core::mem;

use crate::{
    strutil::TString,
    translations::TR,
    ui::{
        component::{text::TextStyle, Component, Event, EventCtx, Label, Never},
        geometry::{Alignment2D, Offset, Rect},
        shape::Renderer,
        util::animation_disabled,
    },
};

use super::super::{
    constant::SCREEN,
    cshape::{render_loader, render_loader_indeterminate, ScreenBorder},
    fonts, theme,
};

const LOADER_SPEED: u16 = 5;

pub struct ProgressScreen {
    indeterminate: bool,
    /// Title of the progress screen, e.g. "Signing transaction..."
    title: Label<'static>,
    /// Description of the current progress, e.g. "Please wait"
    description: Label<'static>,
    /// Current value of the progress bar.
    value: u16,
    border: ScreenBorder,
    /// Whether the progress is for Coinjoin BusyScreen
    coinjoin_progress: bool,
    coinjoin_do_not_disconnect: Option<Label<'static>>,
}

impl ProgressScreen {
    pub fn new_progress(
        title: TString<'static>,
        indeterminate: bool,
        description: TString<'static>,
        danger: bool,
    ) -> Self {
        Self {
            indeterminate,
            title: Label::left_aligned(title, theme::TEXT_NORMAL),
            description: Label::centered(description, theme::TEXT_SMALL_GREY).vertically_centered(),
            value: 0,
            border: ScreenBorder::new(if danger {
                theme::ORANGE
            } else {
                theme::GREEN_LIME
            }),
            coinjoin_progress: false,
            coinjoin_do_not_disconnect: None,
        }
    }

    pub fn new_coinjoin_progress(
        title: TString<'static>,
        indeterminate: bool,
        description: TString<'static>,
    ) -> Self {
        Self {
            indeterminate,
            title: Label::left_aligned(title, theme::TEXT_NORMAL),
            description: Label::centered(description, theme::TEXT_SMALL_GREY).vertically_centered(),
            value: 0,
            border: ScreenBorder::new(theme::GREEN_LIME),
            coinjoin_progress: true,
            coinjoin_do_not_disconnect: Some(
                Label::centered(TR::coinjoin__do_not_disconnect.into(), theme::TEXT_REGULAR)
                    .vertically_centered(),
            ),
        }
    }
}

impl Component for ProgressScreen {
    type Msg = Never;

    fn place(&mut self, bounds: Rect) -> Rect {
        debug_assert_eq!(bounds.height(), SCREEN.height());
        debug_assert_eq!(bounds.width(), SCREEN.width());
        let bounds = bounds.inset(theme::SIDE_INSETS);

        let main_text_area = Rect::from_top_left_and_size(
            theme::PROGRESS_TEXT_ORIGIN,
            Offset::new(
                SCREEN.width() - 2 * theme::PADDING,
                4 * theme::TEXT_NORMAL.text_font.text_max_height(),
            ),
        );
        let middle_text_area = Rect::snap(
            main_text_area.bottom_center(),
            Offset::new(
                bounds.width(),
                3 * theme::TEXT_REGULAR.text_font.text_max_height(),
            ),
            Alignment2D::TOP_CENTER,
        );
        let action_bar_area = bounds.split_bottom(theme::ACTION_BAR_HEIGHT).1;

        self.coinjoin_do_not_disconnect.place(middle_text_area);
        self.title.place(main_text_area);
        self.description.place(action_bar_area);
        bounds
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        // ProgressScreen only reacts to Progress events
        // CoinjoinProgressScreen with indeterminate reacts to ANIM_FRAME_TIMER
        match event {
            _ if animation_disabled() => {
                return None;
            }
            Event::Attach(_) if self.coinjoin_progress && self.indeterminate => {
                ctx.request_anim_frame();
            }
            Event::Timer(EventCtx::ANIM_FRAME_TIMER) => {
                self.value = (self.value + LOADER_SPEED) % 1000;
                ctx.request_anim_frame();
                ctx.request_paint();
            }
            Event::Progress(new_value, new_description) => {
                if mem::replace(&mut self.value, new_value) != new_value {
                    if !animation_disabled() {
                        ctx.request_paint();
                    }
                    if self.description.text() != &new_description {
                        self.description.set_text(new_description);
                        ctx.request_paint();
                    }
                }
            }
            _ => {}
        }
        None
    }

    fn render<'s>(&'s self, target: &mut impl Renderer<'s>) {
        let progress_val = self.value.min(1000);
        if self.indeterminate {
            render_loader_indeterminate(progress_val, &self.border, target);
        } else {
            render_loader(progress_val, &self.border, target);
        }
        self.title.render(target);
        self.description.render(target);
        if self.coinjoin_progress {
            self.coinjoin_do_not_disconnect.render(target);
        }
    }
}

#[cfg(feature = "ui_debug")]
impl crate::trace::Trace for ProgressScreen {
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        if self.coinjoin_progress {
            t.component("CoinJoinProgress");
        } else {
            t.component("Progress");
        }
    }
}
