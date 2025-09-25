use crate::{
    strutil::TString,
    time::{Duration, Stopwatch},
    ui::{
        component::{Component, Event, EventCtx},
        display::Color,
        geometry::{Alignment2D, Insets, Offset, Rect},
        lerp::Lerp,
        shape::{self, Renderer},
    },
};

use super::{
    super::{cshape::ScreenBorder, firmware::Header, theme},
    constant::SCREEN,
};

#[cfg(feature = "haptic")]
use pareen;

#[cfg(feature = "haptic")]
use crate::trezorhal::haptic;

#[cfg(feature = "rgb_led")]
use crate::trezorhal::rgb_led;

/// A component that displays a border that grows from the bottom of the screen
/// to the top. The animation is parametrizable by color and duration.
pub struct HoldToConfirmAnim {
    /// Intended total duration of Hold to Confirm animation
    total_duration: Duration,
    /// Screen border and header overlay color
    color: Color,
    /// Screen border shape
    border: ScreenBorder,
    /// Header overlay text shown during the animation
    header_overlay: Option<TString<'static>>,
    /// Animation state
    state: AnimState,
}

pub enum HoldToConfirmMsg {
    /// The hold to confirm action was completed
    Finalized,
}

enum AnimState {
    Idle,
    /// Growing border from start
    Growing {
        stopwatch: Stopwatch,
    },
    /// State of the rollback animation, when `stop` is called.
    RollingBack {
        stopwatch: Stopwatch,
        started_at: Duration,
    },
    /// Finalizing animation after confirmation, when `finalize` is called.
    Finalizing {
        stopwatch: Stopwatch,
    },
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

    const FINALIZING_DURATION: Duration = Duration::from_millis(500);

    /// Duration after which the header overlay is shown after `start` is called
    const HEADER_OVERLAY_DELAY: Duration = Duration::from_millis(300);

    pub fn new() -> Self {
        let default_color = theme::GREEN_LIME;
        Self {
            total_duration: theme::CONFIRM_HOLD_DURATION.into(),
            color: default_color,
            border: ScreenBorder::new(default_color),
            header_overlay: None,
            state: AnimState::Idle,
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
        self.state = AnimState::Growing {
            stopwatch: Stopwatch::new_started(),
        };
    }

    pub fn stop(&mut self) {
        if let AnimState::Growing { stopwatch } = &self.state {
            let started_at = stopwatch.elapsed();
            self.state = AnimState::RollingBack {
                stopwatch: Stopwatch::new_started(),
                started_at,
            };
        }
    }

    pub fn finalize(&mut self) {
        #[cfg(feature = "rgb_led")]
        rgb_led::set_color(theme::color_to_led_color(self.color).into());
        self.state = AnimState::Finalizing {
            stopwatch: Stopwatch::new_started(),
        };
    }

    fn is_animating(&self) -> bool {
        match &self.state {
            AnimState::Idle => false,
            AnimState::Growing { stopwatch } => stopwatch.is_running_within(self.total_duration),
            AnimState::RollingBack { stopwatch, .. } => {
                stopwatch.is_running_within(self.rollback_duration())
            }
            AnimState::Finalizing { stopwatch } => {
                stopwatch.is_running_within(Self::FINALIZING_DURATION)
            }
        }
    }

    fn rollback_duration(&self) -> Duration {
        self.total_duration * Self::ROLLBACK_DURATION_RATIO
    }
}

impl Component for HoldToConfirmAnim {
    type Msg = HoldToConfirmMsg;

    fn place(&mut self, bounds: Rect) -> Rect {
        bounds
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        if let Event::Timer(EventCtx::ANIM_FRAME_TIMER) = event {
            if self.is_animating() {
                ctx.request_anim_frame();
                ctx.request_paint();
            }
            // Finalizing just completed
            if let AnimState::Finalizing { stopwatch } = &self.state {
                if stopwatch.is_running() && !stopwatch.is_running_within(Self::FINALIZING_DURATION)
                {
                    #[cfg(feature = "rgb_led")]
                    rgb_led::set_color(0);
                    return Some(HoldToConfirmMsg::Finalized);
                }
            }
        }
        None
    }

    fn render<'s>(&'s self, target: &mut impl Renderer<'s>) {
        match &self.state {
            AnimState::Idle => {}
            AnimState::RollingBack {
                stopwatch,
                started_at,
            } => {
                let rollback_elapsed = stopwatch.elapsed();
                let alpha = self.get_rollback_alpha(rollback_elapsed);
                let rollback_duration_progressed =
                    started_at.checked_add(rollback_elapsed).unwrap_or_default();
                let (clip, top_gap) = self.get_clips(rollback_duration_progressed);
                let top_back_rollback = self.get_top_gap_rollback(rollback_elapsed);
                let top_gap = top_gap.union(top_back_rollback);
                self.render_clipped_border(clip, top_gap, alpha, target);
            }
            AnimState::Growing { stopwatch } => {
                let elapsed = stopwatch.elapsed();
                if elapsed > Self::HEADER_OVERLAY_DELAY {
                    self.render_header_overlay(target);
                }
                let (clip, top_gap) = self.get_clips(elapsed);
                self.render_clipped_border(clip, top_gap, u8::MAX, target);

                #[cfg(feature = "haptic")]
                haptic::play_custom(self.get_haptic(elapsed), 100);
            }
            AnimState::Finalizing { stopwatch } => {
                let elapsed = stopwatch.elapsed();
                let alpha = self.get_finalizing_alpha(elapsed);
                self.render_done_icon(alpha, target);
                self.border.render(alpha, target);
            }
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
                theme::PADDING,
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
    fn render_done_icon<'s>(&'s self, alpha: u8, target: &mut impl Renderer<'s>) {
        let icon = theme::ICON_DONE;
        let header_pad = Rect::from_top_left_and_size(
            SCREEN.top_left(),
            Offset::new(SCREEN.width(), Header::HEADER_HEIGHT),
        );
        let icon_area = header_pad.inset(Insets::left(theme::PADDING));
        shape::Bar::new(header_pad)
            .with_bg(theme::BG)
            .render(target);
        shape::ToifImage::new(icon_area.left_center(), icon.toif)
            .with_fg(self.color)
            .with_alpha(alpha)
            .with_align(Alignment2D::CENTER_LEFT)
            .render(target);
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

    fn get_finalizing_alpha(&self, elapsed: Duration) -> u8 {
        let progress = (elapsed / Self::FINALIZING_DURATION).clamp(0.0, 1.0);
        let shift = pareen::constant(0.0).seq_ease_in(
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
            Offset::new(SCREEN.width(), ScreenBorder::TOP_ARC_HEIGHT),
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
                    Offset::new(width, ScreenBorder::TOP_ARC_HEIGHT),
                );
                (SCREEN, top_gap)
            }

            // Animation complete
            _ => (SCREEN, TOP_GAP_ZERO),
        }
    }

    #[cfg(feature = "haptic")]
    fn get_haptic(&self, elapsed: Duration) -> i8 {
        // Normalize elapsed time
        let progress = (elapsed / self.total_duration).clamp(0.0, 1.0);

        // Create a linear easing from 0.0 to 1.0 over normalized progress
        let ease = pareen::constant(0.0).seq_ease_in(
            0.0,
            easer::functions::Linear,
            1.0,
            pareen::constant(1.0),
        );

        // Scale eased value to 0–100
        (100.0 * ease.eval(progress)) as i8
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
