use crate::{
    strutil::TString,
    time::{Duration, Stopwatch},
    ui::{
        component::{Component, Event, EventCtx, Never},
        display::Color,
        geometry::{Offset, Rect},
        lerp::Lerp,
        shape::{self, Renderer},
    },
};

use super::{
    super::{component::Header, cshape::ScreenBorder, theme},
    constant::SCREEN,
};

/// A component that displays a border that grows from the bottom of the screen
/// to the top. The animation is parametrizable by color and duration.
pub struct HoldToConfirmAnim {
    /// Intended total duration of Hold to Confirm animation
    total_duration: Duration,
    /// Screen border and header overlay color
    color: Color,
    /// Screen border shape
    border: ScreenBorder,
    /// Timer for the animation
    timer: Stopwatch,
    /// Header overlay text shown during the animation
    header_overlay: Option<TString<'static>>,
    /// Rollback animation state
    rollback: RollbackState,
}

/// State of the rollback animation, when `stop` is called.
struct RollbackState {
    /// Timer for the rollback animation
    timer: Stopwatch,
    /// Point in time of the growth animation when the rollback was initiated
    duration: Duration,
}

impl HoldToConfirmAnim {
    /// Ratio of total_duration for the bottom part of the border
    const BOTTOM_DURATION_RATIO: f32 = 0.125;
    /// Ratio of total_duration for the side parts of the border
    const SIDES_DURATION_RATIO: f32 = 0.5;
    /// Ratio of total_duration for the top part of the border
    const TOP_DURATION_RATIO: f32 = 0.375;

    /// Duration ratio for the rollback animation after `stop` is called
    const ROLLBACK_DURATION_RATIO: f32 = Self::TOP_DURATION_RATIO;

    /// Duration after which the header overlay is shown after `start` is called
    const HEADER_OVERLAY_DELAY: Duration = Duration::from_millis(300);

    pub fn new() -> Self {
        let default_color = theme::GREEN_LIME;
        Self {
            total_duration: theme::CONFIRM_HOLD_DURATION,
            color: default_color,
            border: ScreenBorder::new(default_color),
            timer: Stopwatch::default(),
            header_overlay: None,
            rollback: RollbackState {
                timer: Stopwatch::default(),
                duration: Duration::default(),
            },
        }
    }

    pub fn with_color(mut self, color: Color) -> Self {
        self.color = color;
        self.border = ScreenBorder::new(color);
        self
    }

    pub fn with_duration(mut self, duration: Duration) -> Self {
        self.total_duration = duration;
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
        self.rollback.timer = Stopwatch::new_started();
        self.rollback.duration = self.timer.elapsed();
        self.timer = Stopwatch::new_stopped();
    }

    fn is_active(&self) -> bool {
        self.timer.is_running_within(self.total_duration)
    }

    fn is_rollback(&self) -> bool {
        self.rollback
            .timer
            .is_running_within(self.rollback_duration())
    }

    fn rollback_duration(&self) -> Duration {
        self.total_duration * Self::ROLLBACK_DURATION_RATIO
    }
}

impl Component for HoldToConfirmAnim {
    type Msg = Never;

    fn place(&mut self, bounds: Rect) -> Rect {
        bounds
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        if let Event::Timer(EventCtx::ANIM_FRAME_TIMER) = event {
            if self.is_active() || self.is_rollback() {
                ctx.request_anim_frame();
                ctx.request_paint();
            }
        };
        None
    }

    fn render<'s>(&'s self, target: &mut impl Renderer<'s>) {
        // Rollback & Fading out animation
        if self.is_rollback() {
            let rollback_elapsed = self.rollback.timer.elapsed();
            let alpha = self.get_rollback_alpha(rollback_elapsed);
            let rollback_duration_progressed = self
                .rollback
                .duration
                .checked_add(rollback_elapsed)
                .unwrap_or(Duration::default());
            let (clip, top_gap) = self.get_clips(rollback_duration_progressed);
            let top_back_rollback = self.get_top_gap_rollback(rollback_elapsed);
            let top_gap = top_gap.union(top_back_rollback);
            self.render_clipped_border(clip, top_gap, alpha, target);
        }

        // Growing animation
        if self.is_active() {
            // override header with custom text
            if self.timer.elapsed() > Self::HEADER_OVERLAY_DELAY {
                self.render_header_overlay(target);
            }
            // growing border
            let (clip, top_gap) = self.get_clips(self.timer.elapsed());
            self.render_clipped_border(clip, top_gap, u8::MAX, target);
        }
    }
}

// Rendering helpers
impl HoldToConfirmAnim {
    fn render_header_overlay<'s>(&'s self, target: &mut impl Renderer<'s>) {
        if let Some(text) = self.header_overlay {
            let font = theme::label_title_main().text_font;
            let header_pad = Rect::from_top_left_and_size(
                SCREEN.top_left(),
                Offset::new(SCREEN.width(), Header::HEADER_HEIGHT),
            );
            // FIXME: vert_center is precisely aligned with the `Header` title (which uses
            // `Label`) but this solution might break with `Header` changes
            let text_offset = Offset::new(
                Header::HEADER_INSETS.left,
                font.vert_center(0, Header::HEADER_HEIGHT - 1, "A"),
            );
            let text_pos = header_pad.top_left() + text_offset;
            shape::Bar::new(header_pad)
                .with_bg(theme::BG)
                .render(target);
            text.map(|text| {
                shape::Text::new(text_pos, text, font)
                    .with_fg(self.color)
                    .render(target);
            });
        }
    }

    fn render_clipped_border<'s>(
        &'s self,
        clip: Rect,
        top_gap: Rect,
        alpha: u8,
        target: &mut impl Renderer<'s>,
    ) {
        target.in_clip(clip, &|target| {
            self.border.render(alpha, target);
        });
        // optional out clip for upper line rendering
        shape::Bar::new(top_gap)
            .with_bg(theme::BG)
            .with_fg(theme::BG)
            .render(target);
    }

    fn get_rollback_alpha(&self, elapsed: Duration) -> u8 {
        let progress = (elapsed / self.rollback_duration()).clamp(0.0, 1.0);
        let shift = pareen::constant(0.0).seq_ease_out(
            0.0,
            easer::functions::Cubic,
            1.0,
            pareen::constant(1.0),
        );
        u8::lerp(u8::MAX, u8::MIN, shift.eval(progress))
    }

    fn get_top_gap_rollback(&self, elapsed: Duration) -> Rect {
        let progress = (elapsed / self.rollback_duration()).clamp(0.0, 1.0);
        let clip_width = (progress * SCREEN.width() as f32) as i16;
        Rect::from_center_and_size(
            SCREEN.top_center().ofs(Offset::y(ScreenBorder::WIDTH / 2)),
            Offset::new(clip_width, ScreenBorder::WIDTH),
        )
    }

    fn get_clips(&self, elapsed: Duration) -> (Rect, Rect) {
        let progress = (elapsed / self.total_duration).clamp(0.0, 1.0);

        const TOP_GAP_ZERO: Rect = Rect::from_center_and_size(
            SCREEN.top_center().ofs(Offset::y(ScreenBorder::WIDTH / 2)),
            Offset::zero(),
        );
        const TOP_GAP_FULL: Rect = Rect::from_center_and_size(
            SCREEN.top_center().ofs(Offset::y(ScreenBorder::WIDTH / 2)),
            Offset::new(SCREEN.width(), ScreenBorder::WIDTH),
        );
        match progress {
            // Bottom phase growing linearly
            p if p < Self::BOTTOM_DURATION_RATIO => {
                let bottom_progress = (p / Self::BOTTOM_DURATION_RATIO).clamp(0.0, 1.0);
                let width = i16::lerp(0, SCREEN.width(), bottom_progress);
                let clip = Rect::from_center_and_size(
                    SCREEN
                        .bottom_center()
                        .ofs(Offset::y(-ScreenBorder::WIDTH / 2)),
                    Offset::new(width, ScreenBorder::WIDTH),
                );
                (clip, TOP_GAP_FULL)
            }

            // Sides phase growing up linearly
            p if p < (Self::BOTTOM_DURATION_RATIO + Self::SIDES_DURATION_RATIO) => {
                let sides_progress = ((p - Self::BOTTOM_DURATION_RATIO)
                    / Self::SIDES_DURATION_RATIO)
                    .clamp(0.0, 1.0);
                let height = i16::lerp(ScreenBorder::WIDTH, SCREEN.height(), sides_progress);
                let clip = Rect::from_bottom_left_and_size(
                    SCREEN.bottom_left(),
                    Offset::new(SCREEN.width(), height),
                );
                (clip, TOP_GAP_FULL)
            }

            // Top phase
            p if p < 1.0 => {
                let top_progress = ((p - Self::BOTTOM_DURATION_RATIO - Self::SIDES_DURATION_RATIO)
                    / Self::TOP_DURATION_RATIO)
                    .clamp(0.0, 1.0);
                let ease = pareen::constant(0.0).seq_ease_out(
                    0.0,
                    easer::functions::Cubic,
                    1.0,
                    pareen::constant(1.0),
                );
                let eased_progress = ease.eval(top_progress);
                let width = i16::lerp(SCREEN.width(), 0, eased_progress);
                let top_gap = Rect::from_center_and_size(
                    SCREEN.top_center().ofs(Offset::y(ScreenBorder::WIDTH / 2)),
                    Offset::new(width, ScreenBorder::WIDTH),
                );
                (SCREEN, top_gap)
            }

            // Animation complete
            _ => (SCREEN, TOP_GAP_ZERO),
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_duration_ratios_sum_to_one() {
        const EPSILON: f32 = 0.001;
        let sum = HoldToConfirmAnim::BOTTOM_DURATION_RATIO
            + HoldToConfirmAnim::SIDES_DURATION_RATIO
            + HoldToConfirmAnim::TOP_DURATION_RATIO;

        assert!(
            sum > 1.0 - EPSILON && sum < 1.0 + EPSILON,
            "Duration ratios sum ({}) must be 1.0",
            sum
        );
    }
}
