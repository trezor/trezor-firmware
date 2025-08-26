use crate::{
    strutil::TString,
    time::{Duration, Stopwatch},
    translations::TR,
    ui::{
        component::{Component, Event, EventCtx, Label, Timeout},
        display::font::FontInfo,
        event::button::{ButtonEvent, PhysicalButton},
        geometry::{Alignment, Insets, Offset, Rect},
        shape::{Renderer, Text},
    },
};

use {
    super::super::{constant::SCREEN, fonts},
    super::{theme, ActionBar, HoldToConfirmAnim},
};

pub struct RestartScreen {
    htc_anim: HoldToConfirmAnim,
    timeout: Timeout,
    stopwatch: Stopwatch,
    countdown_area: Rect,
    label: Label<'static>,
}

pub enum RestartMsg {
    Cancelled,
    Confirmed,
}

impl RestartScreen {
    const HOLD_DURATION: Duration = Duration::from_secs(3);
    const COUNTDOWN_FONT: &FontInfo = fonts::FONT_SATOSHI_REGULAR_38;
    const COUNTDOWN_HEIGHT: i16 = 46;
    pub fn new(description: TString<'static>) -> Self {
        Self {
            htc_anim: HoldToConfirmAnim::new()
                .with_color(theme::GREY_LIGHT)
                .with_duration(Self::HOLD_DURATION),
            timeout: Timeout::new(Self::HOLD_DURATION.to_millis() as _),
            stopwatch: Stopwatch::new_started(),
            countdown_area: Rect::zero(),
            label: Label::new(description, Alignment::Center, theme::TEXT_SMALL_GREY)
                .vertically_centered(),
        }
    }
}

impl Component for RestartScreen {
    type Msg = RestartMsg;

    fn place(&mut self, bounds: Rect) -> Rect {
        // assert full screen
        debug_assert_eq!(bounds.height(), SCREEN.height());
        debug_assert_eq!(bounds.width(), SCREEN.width());

        self.htc_anim.place(bounds);
        let (rest, action_bar_area) = bounds.split_bottom(ActionBar::ACTION_BAR_HEIGHT);

        self.countdown_area = rest
            .inset(Insets::top(38))
            .inset(theme::SIDE_INSETS)
            .with_height(Self::COUNTDOWN_HEIGHT);
        self.label.place(action_bar_area);

        bounds
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        self.htc_anim.event(ctx, event);

        if self.timeout.event(ctx, event).is_some() {
            return Some(RestartMsg::Confirmed);
        }

        match event {
            Event::Attach(_) => {
                self.htc_anim.start();
                ctx.request_anim_frame();
                ctx.request_paint();
                ctx.disable_swipe();
                return None;
            }
            Event::Button(ButtonEvent::ButtonReleased(PhysicalButton::Power))
            | Event::Button(ButtonEvent::ButtonPressed(PhysicalButton::Power)) => {
                self.htc_anim.stop();
                ctx.request_anim_frame();
                ctx.request_paint();
                ctx.enable_swipe();
                return Some(RestartMsg::Cancelled);
            }
            _ => {}
        }
        None
    }

    fn render<'s>(&'s self, target: &mut impl Renderer<'s>) {
        self.label.render(target);

        let remaining_s = Self::HOLD_DURATION.to_secs() - self.stopwatch.elapsed().to_secs();
        let progress = uformat!(
            "{} {}..",
            TString::from_translation(TR::reboot__countdown),
            remaining_s as i16
        );
        Text::new(
            self.countdown_area
                .left_center()
                .ofs(Offset::y(Self::COUNTDOWN_FONT.allcase_text_height() / 2)),
            &progress,
            Self::COUNTDOWN_FONT,
        )
        .with_align(Alignment::Start)
        .with_fg(theme::GREY_LIGHT)
        .render(target);

        self.htc_anim.render(target);
    }
}

#[cfg(feature = "ui_debug")]
impl crate::trace::Trace for RestartScreen {
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.component("RestartScreen");
    }
}
