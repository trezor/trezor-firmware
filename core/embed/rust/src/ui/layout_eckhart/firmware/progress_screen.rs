use core::mem;

use crate::{
    strutil::TString,
    translations::TR,
    ui::{
        component::{
            text::paragraphs::{Paragraph, ParagraphSource as _, ParagraphVecShort, Paragraphs},
            Component, Event, EventCtx, Label, Never,
        },
        geometry::{Alignment, Alignment2D, LinearPlacement, Offset, Rect},
        shape::{self, Renderer},
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
    text: Paragraphs<ParagraphVecShort<'static>>,
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
    ) -> Self {
        Self {
            indeterminate,
            text: Self::create_paragraphs(title, description),
            value: 0,
            border: ScreenBorder::new(theme::GREEN_LIME),
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
            text: Self::create_paragraphs(title, description),
            value: 0,
            border: ScreenBorder::new(theme::GREEN_LIME),
            coinjoin_progress: true,
            coinjoin_do_not_disconnect: Some(
                Label::centered(
                    TR::coinjoin__title_do_not_disconnect.into(),
                    theme::TEXT_REGULAR,
                )
                .vertically_centered(),
            ),
        }
    }

    fn create_paragraphs(
        title: TString<'static>,
        description: TString<'static>,
    ) -> Paragraphs<ParagraphVecShort<'static>> {
        ParagraphVecShort::from_iter([
            Paragraph::new(&theme::firmware::TEXT_MEDIUM_GREY, title).centered(),
            Paragraph::new(&theme::firmware::TEXT_MEDIUM_GREY, description).centered(),
        ])
        .into_paragraphs()
        .with_placement(LinearPlacement::vertical().align_at_center())
    }
}

impl Component for ProgressScreen {
    type Msg = Never;

    fn place(&mut self, bounds: Rect) -> Rect {
        debug_assert_eq!(bounds.height(), SCREEN.height());
        debug_assert_eq!(bounds.width(), SCREEN.width());
        let bounds = bounds.inset(theme::SIDE_INSETS);

        let max_text_area = 3 * theme::TEXT_REGULAR.text_font.text_max_height();
        let middle_text_area = Rect::snap(
            SCREEN.center(),
            Offset::new(bounds.width(), max_text_area),
            Alignment2D::CENTER,
        );
        let action_bar_area = bounds.split_bottom(theme::ACTION_BAR_HEIGHT).1;

        self.coinjoin_do_not_disconnect.place(middle_text_area);
        self.text.place(action_bar_area);
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
                    if self.text.inner()[1].content() != &new_description {
                        self.text.mutate(|p| p[1].update(new_description));
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
            if !self.coinjoin_progress {
                render_percentage(progress_val, target);
            }
        }
        if self.coinjoin_progress {
            self.coinjoin_do_not_disconnect.render(target);
        }
        self.text.render(target);
    }
}

fn render_percentage<'s>(progress: u16, target: &mut impl Renderer<'s>) {
    let progress_percent = uformat!("{}%", (progress as f32 / 10.0) as i16);
    shape::Text::new(
        SCREEN.center(),
        &progress_percent,
        fonts::FONT_SATOSHI_EXTRALIGHT_72,
    )
    .with_align(Alignment::Center)
    .with_fg(theme::GREY_LIGHT)
    .render(target);
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
