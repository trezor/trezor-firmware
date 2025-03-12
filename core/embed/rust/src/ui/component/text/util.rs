use crate::{
    strutil::TString,
    ui::{
        display::{Color, Font},
        geometry::{Alignment, Rect},
        shape::Renderer,
    },
};

use super::{
    layout::{LayoutFit, TextLayout},
    TextStyle,
};

/// Draws longer multiline texts inside an area.
/// Splits lines on word boundaries/whitespace.
/// When a word is too long to fit one line, splitting
/// it on multiple lines with "-" at the line-ends.
///
/// If it fits, returns the rest of the area.
/// If it does not fit, returns `None`.
pub fn text_multiline<'s>(
    target: &mut impl Renderer<'s>,
    area: Rect,
    text: TString<'_>,
    font: Font,
    fg_color: Color,
    bg_color: Color,
    alignment: Alignment,
) -> Option<Rect> {
    let text_style = TextStyle::new(font, fg_color, bg_color, fg_color, fg_color);
    let text_layout = TextLayout::new(text_style)
        .with_bounds(area)
        .with_align(alignment);
    let layout_fit = text.map(|t| text_layout.render_text(t, target));
    match layout_fit {
        LayoutFit::Fitting { height, .. } => Some(area.split_top(height).1),
        LayoutFit::OutOfBounds { .. } => None,
    }
}

/// Same as `text_multiline` above, but aligns the text to the bottom of the
/// area.
pub fn text_multiline_bottom<'s>(
    target: &mut impl Renderer<'s>,
    area: Rect,
    text: TString<'_>,
    font: Font,
    fg_color: Color,
    bg_color: Color,
    alignment: Alignment,
) -> Option<Rect> {
    let text_style = TextStyle::new(font, fg_color, bg_color, fg_color, fg_color);
    let mut text_layout = TextLayout::new(text_style)
        .with_bounds(area)
        .with_align(alignment);
    // When text fits the area, displaying it in the bottom part.
    // When not, render it "normally".
    text.map(|t| match text_layout.fit_text(t) {
        LayoutFit::Fitting { height, .. } => {
            let (top, bottom) = area.split_bottom(height);
            text_layout = text_layout.with_bounds(bottom);
            text_layout.render_text(t, target);
            Some(top)
        }
        LayoutFit::OutOfBounds { .. } => {
            text_layout.render_text(t, target);
            None
        }
    })
}
