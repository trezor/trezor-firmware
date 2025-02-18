use crate::{
    strutil::TString,
    time::{Duration, Stopwatch},
    ui::{
        component::{Component, Event, EventCtx, Never},
        display::Color,
        geometry::{Offset, Rect},
        shape::{self, Renderer},
    },
};

use super::{
    super::{component::Header, cshape::ScreenBorder, fonts, theme},
    constant::SCREEN,
};

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

    fn get_clips(&self) -> (Rect, Option<Rect>) {
        let ratio = self.timer.elapsed() / self.duration;

        let bottom_width = self.border.bottom_width();
        let total_height = SCREEN.height();
        let total_width = SCREEN.width();

        let circumference = 2 * total_height + total_width + bottom_width;
        let bottom_ratio = bottom_width as f32 / circumference as f32;
        let vertical_ratio = (2 * total_height) as f32 / circumference as f32;
        let upper_ratio = total_width as f32 / circumference as f32;

        let vertical_cut = bottom_ratio + vertical_ratio;

        if ratio < bottom_ratio {
            // Animate the bottom border growing horizontally.
            let clip_width = ((ratio / bottom_ratio) * bottom_width as f32) as i16;
            let clip_width = clip_width.clamp(0, bottom_width);
            (
                Rect::from_center_and_size(
                    SCREEN
                        .bottom_center()
                        .ofs(Offset::y(-ScreenBorder::WIDTH / 2)),
                    Offset::new(clip_width, ScreenBorder::WIDTH),
                ),
                None,
            )
        } else if ratio < vertical_cut {
            // Animate the vertical border growing from the bottom up.
            let progress = (ratio - bottom_ratio) / vertical_ratio;
            let clip_height = (progress * total_height as f32) as i16;
            let clip_height = clip_height.clamp(0, total_height - ScreenBorder::WIDTH);
            (
                Rect::from_bottom_left_and_size(
                    SCREEN.bottom_left(),
                    Offset::new(total_width, clip_height),
                ),
                None,
            )
        } else {
            // Animate the top border growing horizontally towards center.
            let progress = (ratio - vertical_cut) / upper_ratio;
            let clip_width = total_width - ((progress * total_width as f32) as i16);
            (
                SCREEN,
                Some(Rect::from_center_and_size(
                    SCREEN.top_center().ofs(Offset::y(ScreenBorder::WIDTH / 2)),
                    Offset::new(clip_width, ScreenBorder::WIDTH),
                )),
            )
        }
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
                    SCREEN.top_left(),
                    Offset::new(SCREEN.width(), Header::HEADER_HEIGHT),
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
            let (in_clip, out_clip_opt) = self.get_clips();
            target.in_clip(in_clip, &|target| {
                self.border.render(target);
            });
            // optional out clip for upper line rendering
            if let Some(out_clip) = out_clip_opt {
                shape::Bar::new(out_clip)
                    .with_bg(theme::BG)
                    .with_fg(theme::BG)
                    .render(target);
            }
        }
    }
}
