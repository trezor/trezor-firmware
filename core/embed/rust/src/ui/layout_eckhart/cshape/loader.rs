use crate::ui::{
    constant::SCREEN,
    geometry::{Offset, Rect},
    lerp::Lerp,
    shape::{self, Renderer},
};

use super::{super::theme::BG, ScreenBorder};

pub fn render_loader<'s>(
    progress: u16,
    border: &'static ScreenBorder,
    target: &mut impl Renderer<'s>,
) {
    // convert to ration from 0.0 to 1.0
    let progress_ratio = (progress as f32 / 1000.0).clamp(0.0, 1.0);
    let (clip, top_gap) = get_clips(progress_ratio);
    render_clipped_border(border, clip, top_gap, u8::MAX, target);
}

fn get_clips(progress_ratio: f32) -> (Rect, Rect) {
    /// Ratio of total_duration for the bottom part of the border
    const BOTTOM_DURATION_RATIO: f32 = 0.125;
    /// Ratio of total_duration for the side parts of the border
    const SIDES_DURATION_RATIO: f32 = 0.5;
    /// Ratio of total_duration for the top part of the border
    const TOP_DURATION_RATIO: f32 = 0.375;

    const TOP_GAP_ZERO: Rect = Rect::from_center_and_size(
        SCREEN.top_center().ofs(Offset::y(ScreenBorder::WIDTH / 2)),
        Offset::zero(),
    );
    const TOP_GAP_FULL: Rect = Rect::from_center_and_size(
        SCREEN.top_center().ofs(Offset::y(ScreenBorder::WIDTH / 2)),
        Offset::new(SCREEN.width(), ScreenBorder::WIDTH),
    );

    match progress_ratio {
        // Bottom phase growing linearly
        p if p < BOTTOM_DURATION_RATIO => {
            let bottom_progress = (p / BOTTOM_DURATION_RATIO).clamp(0.0, 1.0);
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
        p if p < (BOTTOM_DURATION_RATIO + SIDES_DURATION_RATIO) => {
            let sides_progress =
                ((p - BOTTOM_DURATION_RATIO) / SIDES_DURATION_RATIO).clamp(0.0, 1.0);
            let height = i16::lerp(ScreenBorder::WIDTH, SCREEN.height(), sides_progress);
            let clip = Rect::from_bottom_left_and_size(
                SCREEN.bottom_left(),
                Offset::new(SCREEN.width(), height),
            );
            (clip, TOP_GAP_FULL)
        }

        // Top gap shrinking linearly
        p if p < 1.0 => {
            let top_progress = ((p - BOTTOM_DURATION_RATIO - SIDES_DURATION_RATIO)
                / TOP_DURATION_RATIO)
                .clamp(0.0, 1.0);
            let width = i16::lerp(SCREEN.width(), 0, top_progress);
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

fn render_clipped_border<'s>(
    border: &'static ScreenBorder,
    clip: Rect,
    top_gap: Rect,
    alpha: u8,
    target: &mut impl Renderer<'s>,
) {
    target.in_clip(clip, &|target| {
        border.render(alpha, target);
    });
    shape::Bar::new(top_gap)
        .with_bg(BG)
        .with_fg(BG)
        .render(target);
}
