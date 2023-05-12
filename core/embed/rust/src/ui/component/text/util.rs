use crate::ui::{
    display::{Color, Font},
    geometry::{Alignment, Rect},
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
pub fn text_multiline_split_words(
    area: Rect,
    text: &str,
    font: Font,
    fg_color: Color,
    bg_color: Color,
    alignment: Alignment,
) -> Option<Rect> {
    let text_style = TextStyle::new(font, fg_color, bg_color, fg_color, fg_color);
    let text_layout = TextLayout::new(text_style)
        .with_bounds(area)
        .with_align(alignment);
    let layout_fit = text_layout.render_text(text);
    match layout_fit {
        LayoutFit::Fitting { height, .. } => Some(area.split_top(height).1),
        LayoutFit::OutOfBounds { .. } => None,
    }
}
