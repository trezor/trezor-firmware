use crate::ui::{
    constant::SCREEN,
    geometry::{Alignment2D, Offset, Point, Rect},
    lerp::Lerp,
    shape::{self, Renderer},
};

use super::{
    super::theme::{self, ICON_BORDER_BL, ICON_BORDER_BR},
    ScreenBorder,
};

/// Renders the loader. Higher `progress` reveals the `border` from the top in
/// clock-wise direction. Used in ProgressScreen and Bootloader. `progress` goes
/// from 0 to 1000.
pub fn render_loader<'s>(progress: u16, border: &'s ScreenBorder, target: &mut impl Renderer<'s>) {
    let progress_ratio = progress_to_ratio(progress);
    // Draw the border first
    border.render(u8::MAX, target);
    // Draw the progressively shrinking covers
    for cover in get_progress_covers(progress_ratio) {
        shape::Bar::new(cover)
            .with_bg(theme::BLACK)
            .with_alpha(u8::MAX)
            .render(target);
    }
}

/// Render the loader in indeterminate mode. A constant size portion of the
/// border is rendered at each time moving around in clock-wise direction.
pub fn render_loader_indeterminate<'s>(
    progress: u16,
    border: &'s ScreenBorder,
    target: &mut impl Renderer<'s>,
) {
    let progress_ratio = progress_to_ratio(progress);
    let clip = get_clip_indeterminate(progress_ratio);
    // Draw the border in clip
    target.in_clip(clip, &|target| {
        border.render(u8::MAX, target);
    });
}

fn progress_to_ratio(progress: u16) -> f32 {
    // convert to ratio from 0.0 to 1.0
    (progress as f32 / 1000.0).clamp(0.0, 1.0)
}

fn get_clip_indeterminate(progress_ratio: f32) -> Rect {
    const CLIP_SIZE: i16 = 190;

    // Define 8 points (+1 duplicate) for an octagonal path around the display
    // Position them to ensure the clip always shows `CLIP_SIZE`-wide part of the
    // border "Right end" and "Left start" points are shifted in y-axis a little
    // bit upwards to account for the irregular corner shape
    const PATH_POINTS: [Point; 9] = [
        // Top start
        Point::new(CLIP_SIZE / 2, -CLIP_SIZE / 2 + ScreenBorder::WIDTH),
        // Top end
        Point::new(
            SCREEN.width() - CLIP_SIZE / 2,
            -CLIP_SIZE / 2 + ScreenBorder::WIDTH,
        ),
        // Right start
        Point::new(
            SCREEN.width() + CLIP_SIZE / 2 - ScreenBorder::WIDTH,
            CLIP_SIZE / 2,
        ),
        // Right end
        Point::new(
            SCREEN.width() + CLIP_SIZE / 2 - ScreenBorder::WIDTH,
            SCREEN.height() - CLIP_SIZE / 2 - 60,
        ),
        // Bottom start
        Point::new(
            SCREEN.width() - CLIP_SIZE / 2 - ScreenBorder::WIDTH,
            SCREEN.height() + CLIP_SIZE / 2 - ScreenBorder::WIDTH,
        ),
        // Bottom end
        Point::new(
            CLIP_SIZE / 2,
            SCREEN.height() + CLIP_SIZE / 2 - ScreenBorder::WIDTH,
        ),
        // Left start
        Point::new(
            -CLIP_SIZE / 2 + ScreenBorder::WIDTH,
            SCREEN.height() - CLIP_SIZE / 2 - 60,
        ),
        // Left end
        Point::new(-CLIP_SIZE / 2 + ScreenBorder::WIDTH, CLIP_SIZE / 2),
        // Top start - duplicate to close the loop
        Point::new(CLIP_SIZE / 2, -CLIP_SIZE / 2 + ScreenBorder::WIDTH),
    ];

    // Calculate which segment we're in and how far along that segment
    let path_length = PATH_POINTS.len() - 1; // -1 because the last point is a duplicate
    let segment_position = progress_ratio * path_length as f32;

    // Integer part gives us the segment
    let segment = segment_position as usize % path_length;

    // Fractional part gives us the position within the segment
    let segment_ratio = segment_position - segment as f32;

    // Get the current point and the next point
    let current = PATH_POINTS[segment];
    let next = PATH_POINTS[segment + 1];

    // Linearly interpolate between the current and next points
    let center = Point::lerp(current, next, segment_ratio);

    Rect::snap(center, Offset::uniform(CLIP_SIZE), Alignment2D::CENTER)
}

fn get_progress_covers(progress_ratio: f32) -> impl Iterator<Item = Rect> {
    let cover_1 = {
        // Top-center to top-right
        const PROGRESS_PORTION: f32 = 0.11;
        const PROGRESS_START: f32 = 0.0;
        const FULL_WIDTH: i16 = 190;
        let progress = ((progress_ratio - PROGRESS_START) / PROGRESS_PORTION).clamp(0.0, 1.0);
        let width = ((1.0 - progress) * FULL_WIDTH as f32) as i16;
        Rect::snap(
            SCREEN.top_right(),
            Offset::new(width, ScreenBorder::TOP_ARC_HEIGHT),
            Alignment2D::TOP_RIGHT,
        )
    };
    let cover_2 = {
        // Top-right to bottom-right
        const PROGRESS_PORTION: f32 = 0.3;
        const PROGRESS_START: f32 = 0.11;
        const FULL_HEIGHT: i16 = 502;
        let progress = ((progress_ratio - PROGRESS_START) / PROGRESS_PORTION).clamp(0.0, 1.0);
        let height = ((1.0 - progress) * FULL_HEIGHT as f32) as i16;
        Rect::snap(
            SCREEN.bottom_right(),
            Offset::new(ICON_BORDER_BR.toif.width(), height),
            Alignment2D::BOTTOM_RIGHT,
        )
    };
    let cover_3 = {
        // Bottom-right to bottom-left
        const PROGRESS_PORTION: f32 = 0.18;
        const PROGRESS_START: f32 = 0.41;
        const FULL_WIDTH: i16 = 298;
        let progress = ((progress_ratio - PROGRESS_START) / PROGRESS_PORTION).clamp(0.0, 1.0);
        let width = ((1.0 - progress) * FULL_WIDTH as f32) as i16;
        Rect::snap(
            SCREEN.bottom_left() + Offset::x(ICON_BORDER_BL.toif.width()),
            Offset::new(width, ScreenBorder::WIDTH),
            Alignment2D::BOTTOM_LEFT,
        )
    };
    let cover_4 = {
        // Bottom-left to top-left
        const PROGRESS_PORTION: f32 = 0.3;
        const PROGRESS_START: f32 = 0.59;
        const FULL_HEIGHT: i16 = 502;
        let progress = ((progress_ratio - PROGRESS_START) / PROGRESS_PORTION).clamp(0.0, 1.0);
        let height = ((1.0 - progress) * FULL_HEIGHT as f32) as i16;
        Rect::snap(
            SCREEN.top_left() + Offset::y(ScreenBorder::TOP_ARC_HEIGHT),
            Offset::new(ICON_BORDER_BL.toif.width(), height),
            Alignment2D::TOP_LEFT,
        )
    };
    let cover_5 = {
        // Top-left to top-center
        const PROGRESS_PORTION: f32 = 0.11;
        const PROGRESS_START: f32 = 0.89;
        const FULL_WIDTH: i16 = 190;
        let progress = ((progress_ratio - PROGRESS_START) / PROGRESS_PORTION).clamp(0.0, 1.0);
        let width = ((1.0 - progress) * FULL_WIDTH as f32) as i16;
        Rect::snap(
            SCREEN.top_center(),
            Offset::new(width, ScreenBorder::TOP_ARC_HEIGHT),
            Alignment2D::TOP_RIGHT,
        )
    };
    [cover_1, cover_2, cover_3, cover_4, cover_5].into_iter()
}
