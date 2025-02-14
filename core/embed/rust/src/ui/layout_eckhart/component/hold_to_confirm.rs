use crate::{
    strutil::TString,
    time::{Duration, Stopwatch},
    ui::{
        component::{Component, Event, EventCtx, Never},
        display::Color,
        geometry::{Offset, Rect},
        layout_eckhart::{cshape::ScreenBorder, fonts},
        shape::{self, Renderer},
    },
};

use super::{constant, theme, Header};

/// A component that displays a border that grows from the bottom of the screen
/// to the top. The animation is parametrizable by color and duration.
pub struct HoldToConfirmAnim {
    /// Duration of the animation
    duration: Duration,
    /// Screen border and header overlay color
    color: Color,
    /// Screen border shape
    border: ScreenBorder,
    /// Timer for the animation
    timer: Stopwatch,
    /// Header overlay text shown during the animation
    header_overlay: Option<TString<'static>>,
}

impl HoldToConfirmAnim {
    pub fn new() -> Self {
        let default_color = theme::GREEN_LIME;
        Self {
            duration: theme::CONFIRM_HOLD_DURATION,
            color: default_color,
            border: ScreenBorder::new(default_color),
            timer: Stopwatch::default(),
            header_overlay: None,
        }
    }

    pub fn with_color(mut self, color: Color) -> Self {
        self.color = color;
        self.border = ScreenBorder::new(color);
        self
    }

    pub fn with_duration(mut self, duration: Duration) -> Self {
        self.duration = duration;
        self
    }

    pub fn with_header_overlay(mut self, header_text: TString<'static>) -> Self {
        self.header_overlay = Some(header_text);
        self
    }

    pub fn start(&mut self) {
        self.timer = Stopwatch::new_started();
    }

    pub fn stop(&mut self) {
        self.timer = Stopwatch::new_stopped();
    }

    fn is_active(&self) -> bool {
        self.timer.is_running_within(self.duration)
    }

    fn get_clip(&self) -> Rect {
        // TODO:
        // 1) there will be some easer function
        // 2) the growth of the top bar cannot be done with just one clip
        let screen = constant::screen();
        let ratio = self.timer.elapsed() / self.duration;
        let clip_height = ((ratio * screen.height() as f32) as i16).clamp(0, screen.height());
        Rect::from_bottom_left_and_size(
            screen.bottom_left(),
            Offset::new(screen.width(), clip_height),
        )
    }
}

impl Component for HoldToConfirmAnim {
    type Msg = Never;

    fn place(&mut self, bounds: Rect) -> Rect {
        bounds
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        if let Event::Timer(EventCtx::ANIM_FRAME_TIMER) = event {
            if self.is_active() {
                ctx.request_anim_frame();
                ctx.request_paint();
            }
        };
        None
    }

    fn render<'s>(&'s self, target: &mut impl Renderer<'s>) {
        if self.is_active() {
            // override header with custom text
            if let Some(text) = self.header_overlay {
                let font = fonts::FONT_SATOSHI_REGULAR_22;
                let header_pad = Rect::from_top_left_and_size(
                    constant::screen().top_left(),
                    Offset::new(constant::screen().width(), Header::HEADER_HEIGHT),
                );
                shape::Bar::new(header_pad)
                    .with_bg(theme::BG)
                    .render(target);
                text.map(|text| {
                    let text_pos = header_pad.top_left()
                        + Offset::new(24, font.vert_center(0, Header::HEADER_HEIGHT, text));
                    shape::Text::new(text_pos, text, font)
                        .with_fg(self.color)
                        .render(target);
                });
            }
            // growing border
            let clip = self.get_clip();
            target.in_clip(clip, &|target| {
                self.border.render(target);
            });
        }
    }
}
