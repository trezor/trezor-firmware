use crate::ui::{component::LineBreaking, display::Font};
use core::iter;

#[derive(Copy, Clone, Eq, PartialEq, Debug)]
struct LineBreak {
    /// Index of character **after** the line-break.
    next_index: usize,
    /// Distance from the last line-break of the sequence, in pixels.
    width: i32,
    style: BreakStyle,
}

#[derive(Copy, Clone, Eq, PartialEq, Debug)]
enum BreakStyle {
    Hard,
    AtWhitespaceOrWordBoundary,
    InsideWord,
}

#[derive(Copy, Clone, Eq, PartialEq, Debug)]
pub enum SpanEnd {
    Continue,
    LineBreak,
    HyphenAndBreak,
}

impl SpanEnd {
    pub const fn is_linebreak(&self) -> bool {
        !matches!(self, SpanEnd::Continue)
    }
}

#[derive(Copy, Clone, Eq, PartialEq, Debug)]
pub struct Span<'a> {
    /// Text contents of the span, including any trailing space.
    pub text: &'a str,
    /// Line appendix, if any.
    pub end: SpanEnd,
    /// Width of the span, in pixels.
    pub width: i32,
}

#[derive(Copy, Clone, Eq, PartialEq, Debug)]
pub struct LayoutFit {
    /// Number of lines of the content that fit in the bounds.
    pub lines: usize,
    /// Total characters that fit in the bounds.
    pub chars: usize,
    /// End of last line as offset from line start.
    pub final_offset: i32,
    /// Does the layout fit end with a linebreak?
    pub new_line: bool,
}

impl LayoutFit {
    pub const fn empty() -> Self {
        Self {
            lines: 0,
            chars: 0,
            final_offset: 0,
            new_line: true,
        }
    }

    pub const fn consume(self, span: Span) -> Self {
        Self {
            lines: self.lines + self.new_line as usize,
            chars: self.chars + span.text.len(),
            final_offset: if span.end.is_linebreak() {
                0
            } else {
                self.final_offset + span.width
            },
            new_line: span.end.is_linebreak(),
        }
    }

    pub fn update(&mut self, span: Span) {
        *self = self.consume(span);
    }

    pub fn of<'a>(spans: impl Iterator<Item = Span<'a>>) -> Self {
        Self::empty().fit_spans(spans)
    }

    pub fn fit_spans<'a>(self, spans: impl Iterator<Item = Span<'a>>) -> Self {
        spans.fold(self, Self::consume)
    }
}

/// Fit a given set of spans into the provided vertical space.
///
/// This is essentially a line counter with some additional bells and whistles.
/// The returned value tells you:
/// * index of the last character that fits in the bounds,
/// * total height of the content that fits in the bounds,
/// * horizontal offset of the last rendered character (in case a subsequent
///   call wants to continue on the same line).
// pub fn fit<'a>(
//     spans: impl Iterator<Item = Span<'a>>,
//     line_height: i32,
//     max_height: i32,
// ) -> LayoutFit {
//     let mut fit = LayoutFit::empty();
//     if line_height < max_height {
//         return fit;
//     }
//     for span in spans {
//         if fit.height + line_height > max_height {
//             break;
//         } else {
//             fit.final_offset = span.width;
//             fit.chars = span.text.len();
//             fit.height += line_height;
//         }
//     }
//     fit
// }

/// Generate spans of text to render as separate lines.
///
/// Spans include trailing whitespace, which is also accounted for in the
/// returned `width`.
///
/// `width` is not guaranteed to be smaller than `available_width`, but it is
/// always safe to render only up to `available_width`; any overflow is
/// guaranteed to be whitespace.
///
/// Trailing empty spans are not emitted. I.e., if the text is empty, no span is
/// returned. If the text ends with a newline, the last span will contain the
/// last line of text, including the newline, instead of an empty span that does
/// not end on a newline.
pub fn break_text_to_spans(
    text: &str,
    text_font: impl GlyphMetrics,
    breaking: LineBreaking,
    available_width: i32,
    initial_offset: i32,
) -> impl Iterator<Item = Span> {
    let mut finished = text.is_empty();
    let mut last_break = LineBreak {
        next_index: 0,
        width: 0,
        style: BreakStyle::AtWhitespaceOrWordBoundary,
    };
    let mut breaks = select_line_breaks(
        text.char_indices(),
        text_font,
        breaking,
        available_width,
        initial_offset,
    );
    iter::from_fn(move || {
        if finished {
            None
        } else if let Some(lb) = breaks.next() {
            let start_of_line = last_break.next_index;
            let end_of_line = lb.next_index; // Not inclusive.
            last_break = lb;
            Some(Span {
                text: &text[start_of_line..end_of_line],
                end: match lb.style {
                    BreakStyle::Hard | BreakStyle::AtWhitespaceOrWordBoundary => SpanEnd::LineBreak,
                    BreakStyle::InsideWord => SpanEnd::HyphenAndBreak,
                },
                width: lb.width,
            })
        } else {
            finished = true;
            let remaining_text = &text[last_break.next_index..];
            (!remaining_text.is_empty()).then_some(Span {
                text: remaining_text,
                end: SpanEnd::Continue,
                width: text_font.text_width(remaining_text),
            })
        }
    })
}

/// Generate line breaks for the given text.
///
/// Calculates the points where we need to break the text in order to fit into
/// `available_width`. Depending on `breaking` parameter, we either break at
/// arbitrary characters, or try to break only at whitespace, inserting hyphens
/// where necessary.
///
/// Width given in the linebreak can be larger than `available_width`, but
/// the overflow is guaranteed to be whitespace only.
fn select_line_breaks(
    chars: impl Iterator<Item = (usize, char)>,
    text_font: impl GlyphMetrics,
    breaking: LineBreaking,
    available_width: i32,
    initial_offset: i32,
) -> impl Iterator<Item = LineBreak> {
    let hyphen_width = text_font.char_width('-');

    let mut proposed = None;
    let mut line_width = initial_offset;
    let mut found_any_whitespace = false;

    chars.filter_map(move |(offset, ch)| {
        let char_width = text_font.char_width(ch);
        let exceeds_available_width = line_width + char_width > available_width;
        let have_space_for_break = line_width + char_width + hyphen_width <= available_width;
        let can_break_word =
            matches!(breaking, LineBreaking::BreakWordsAndInsertHyphen) || !found_any_whitespace;

        let next_offset = offset + ch.len_utf8();
        let next_line_width = line_width + char_width;

        let break_line = match ch {
            '\n' | '\r' => {
                // Immediate hard break.
                Some(LineBreak {
                    next_index: next_offset,
                    width: next_line_width,
                    style: BreakStyle::Hard,
                })
            }
            ' ' | '\t' => {
                // Whitespace, propose a line-break after this character.
                proposed = Some(LineBreak {
                    next_index: next_offset,
                    width: next_line_width,
                    style: BreakStyle::AtWhitespaceOrWordBoundary,
                });
                found_any_whitespace = true;
                None
            }
            _ if have_space_for_break && can_break_word => {
                // Propose a word-break after this character. In case the next character is
                // whitespace, the proposed word break is replaced by a whitespace break.
                proposed = Some(LineBreak {
                    next_index: next_offset,
                    width: next_line_width,
                    style: BreakStyle::InsideWord,
                });
                None
            }
            _ if exceeds_available_width => {
                // Consume the last proposed line-break. In case we don't have anything
                // proposed, we hard-break immediately before this character. This only happens
                // if the first character of the line doesn't fit.
                Some(proposed.unwrap_or(LineBreak {
                    next_index: offset,
                    width: line_width,
                    style: BreakStyle::Hard,
                }))
            }
            _ => None,
        };
        if let Some(br) = break_line {
            // Reset the state.
            proposed = None;
            line_width -= br.width;
            found_any_whitespace = false;
        }
        // Shift cursor.
        line_width += char_width;
        break_line
    })
}

pub trait GlyphMetrics: Copy {
    fn char_width(&self, ch: char) -> i32;
    fn text_width(&self, text: &str) -> i32;
    fn line_height(&self) -> i32;
}

impl GlyphMetrics for Font {
    fn char_width(&self, ch: char) -> i32 {
        Font::char_width(*self, ch)
    }

    fn text_width(&self, text: &str) -> i32 {
        Font::text_width(*self, text)
    }

    fn line_height(&self) -> i32 {
        Font::line_height(*self)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[derive(Clone, Copy)]
    pub struct Fixed {
        pub width: i32,
        pub height: i32,
    }

    impl GlyphMetrics for Fixed {
        fn char_width(&self, _ch: char) -> i32 {
            if _ch == '\n' {
                0
            } else {
                self.width
            }
        }

        fn text_width(&self, text: &str) -> i32 {
            text.chars().map(|ch| self.char_width(ch)).sum()
        }

        fn line_height(&self) -> i32 {
            self.height
        }
    }

    const FIXED_FONT: Fixed = Fixed {
        width: 1,
        height: 1,
    };

    #[test]
    fn test_span() {
        assert_eq!(spans_from("hello", 5), vec![("hello", false)]);
        assert_eq!(spans_from("", 5), vec![]);
        assert_eq!(
            spans_from("hello world", 5),
            vec![("hello ", false), ("world", false)]
        );
        assert_eq!(
            spans_from("hello\nworld", 5),
            vec![("hello\n", false), ("world", false)]
        );
        assert_eq!(
            spans_from("hello\n\nworld", 5),
            vec![("hello\n", false), ("\n", false), ("world", false)]
        );
    }

    #[test]
    fn test_leading_trailing() {
        assert_eq!(
            spans_from("\nhello\nworld\n", 5),
            vec![("\n", false), ("hello\n", false), ("world\n", false),]
        );
    }

    #[test]
    fn test_long_word() {
        assert_eq!(
            spans_from("Constantinople", 7),
            vec![("Consta", true), ("ntinop", true), ("le", false)]
        );

        assert_eq!(
            spans_from("Down with the establishment!", 5),
            vec![
                ("Down ", false),
                ("with ", false),
                ("the ", false),
                ("esta", true),
                ("blis", true),
                ("hmen", true),
                ("t!", false),
            ]
        );
    }

    #[test]
    fn test_layout_fit() {
        assert_eq!(
            LayoutFit::of(make_spans("hello world", 5)),
            LayoutFit {
                lines: 2,
                chars: 11,
                final_offset: 5,
                new_line: false,
            }
        );
        assert_eq!(
            LayoutFit::of(make_spans("hello\nworld", 5)),
            LayoutFit {
                lines: 2,
                chars: 11,
                final_offset: 5,
                new_line: false,
            }
        );
        assert_eq!(
            LayoutFit::of(make_spans("hello\nworld\n", 5)),
            LayoutFit {
                lines: 2,
                chars: 12,
                final_offset: 0,
                new_line: true,
            }
        );
        assert_eq!(
            LayoutFit::of(make_spans("hello\nworld\n\n", 5)),
            LayoutFit {
                lines: 3,
                chars: 13,
                final_offset: 0,
                new_line: true,
            }
        );
        assert_eq!(
            LayoutFit::of(make_spans("", 5)),
            LayoutFit {
                lines: 0,
                chars: 0,
                final_offset: 0,
                new_line: true,
            }
        );
        assert_eq!(
            LayoutFit::of(make_spans("\n", 5)),
            LayoutFit {
                lines: 1,
                chars: 1,
                final_offset: 0,
                new_line: true,
            }
        );
        assert_eq!(
            LayoutFit::of(make_spans("hello\n", 5)),
            LayoutFit {
                lines: 1,
                chars: 6,
                final_offset: 0,
                new_line: true,
            }
        );
    }

    #[test]
    fn test_char_boundary() {
        assert_eq!(
            spans_from("+ěščřžýáíé", 5),
            vec![("+ěšč", true), ("řžýá", true), ("íé", false)]
        );
    }

    fn make_spans(text: &str, max_width: i32) -> impl Iterator<Item = Span> {
        break_text_to_spans(
            text,
            FIXED_FONT,
            LineBreaking::BreakAtWhitespace,
            max_width,
            0,
        )
    }

    fn spans_from(text: &str, max_width: i32) -> Vec<(&str, bool)> {
        make_spans(text, max_width)
            .map(|span| (span.text, matches!(span.end, SpanEnd::HyphenAndBreak)))
            .collect()
    }
}
