use crate::ui::{component::LineBreaking, display::Font};
use core::iter;

#[derive(Copy, Clone, Eq, PartialEq, Debug)]
struct LineBreak {
    /// Index of character **after** the line-break.
    offset: usize,
    /// Distance from the last line-break of the sequence, in pixels.
    width: i16,
    style: BreakStyle,
}

#[derive(Copy, Clone, Eq, PartialEq, Debug)]
enum BreakStyle {
    Hard,
    AtWhitespaceOrWordBoundary,
    InsideWord,
}

fn limit_line_breaks(
    breaks: impl Iterator<Item = LineBreak>,
    line_height: i16,
    available_height: i16,
) -> impl Iterator<Item = LineBreak> {
    breaks.take(available_height as usize / line_height as usize)
}

#[derive(Copy, Clone, Eq, PartialEq, Debug)]
enum Appendix {
    None,
    Hyphen,
}

#[derive(Copy, Clone, Eq, PartialEq, Debug)]
struct Span<'a> {
    text: &'a str,
    append: Appendix,
}

fn break_text_to_spans(
    text: &str,
    text_font: impl GlyphMetrics,
    hyphen_font: impl GlyphMetrics,
    breaking: LineBreaking,
    available_width: i16,
) -> impl Iterator<Item = Span> {
    let mut finished = false;
    let mut last_break = LineBreak {
        offset: 0,
        width: 0,
        style: BreakStyle::AtWhitespaceOrWordBoundary,
    };
    let mut breaks = select_line_breaks(
        text.char_indices(),
        text_font,
        hyphen_font,
        breaking,
        available_width,
    );
    iter::from_fn(move || {
        if finished {
            None
        } else if let Some(lb) = breaks.next() {
            let start_of_line = last_break.offset;
            let end_of_line = lb.offset; // Not inclusive.
            last_break = lb;
            if let BreakStyle::AtWhitespaceOrWordBoundary = lb.style {
                last_break.offset += 1;
            }
            Some(Span {
                text: &text[start_of_line..end_of_line],
                append: match lb.style {
                    BreakStyle::Hard | BreakStyle::AtWhitespaceOrWordBoundary => Appendix::None,
                    BreakStyle::InsideWord => Appendix::Hyphen,
                },
            })
        } else {
            finished = true;
            Some(Span {
                text: &text[last_break.offset..],
                append: Appendix::None,
            })
        }
    })
}

fn select_line_breaks(
    chars: impl Iterator<Item = (usize, char)>,
    text_font: impl GlyphMetrics,
    hyphen_font: impl GlyphMetrics,
    breaking: LineBreaking,
    available_width: i16,
) -> impl Iterator<Item = LineBreak> {
    let hyphen_width = hyphen_font.char_width('-');

    let mut proposed = None;
    let mut line_width = 0;
    let mut found_any_whitespace = false;

    chars.filter_map(move |(offset, ch)| {
        let char_width = text_font.char_width(ch);
        let exceeds_available_width = line_width + char_width > available_width;
        let have_space_for_break = line_width + char_width + hyphen_width <= available_width;
        let can_break_word =
            matches!(breaking, LineBreaking::BreakWordsAndInsertHyphen) || !found_any_whitespace;

        let break_line = match ch {
            '\n' | '\r' => {
                // Immediate hard break.
                Some(LineBreak {
                    offset,
                    width: line_width,
                    style: BreakStyle::Hard,
                })
            }
            ' ' | '\t' => {
                // Whitespace, propose a line-break before this character.
                proposed = Some(LineBreak {
                    offset,
                    width: line_width,
                    style: BreakStyle::AtWhitespaceOrWordBoundary,
                });
                found_any_whitespace = true;
                None
            }
            _ if have_space_for_break && can_break_word => {
                // Propose a word-break after this character. In case the next character is
                // whitespace, the proposed word break is replaced by a whitespace break.
                proposed = Some(LineBreak {
                    offset: offset + 1,
                    width: line_width + char_width + hyphen_width,
                    style: BreakStyle::InsideWord,
                });
                None
            }
            _ if exceeds_available_width => {
                // Consume the last proposed line-break. In case we don't have anything
                // proposed, we hard-break immediately before this character. This only happens
                // if the first character of the line doesn't fit.
                Some(proposed.unwrap_or(LineBreak {
                    offset,
                    width: line_width,
                    style: BreakStyle::Hard,
                }))
            }
            _ => None,
        };
        if break_line.is_some() {
            // Reset the state.
            proposed = None;
            line_width = 0;
            found_any_whitespace = false;
        } else {
            // Shift cursor.
            line_width += char_width;
        }
        break_line
    })
}

pub trait GlyphMetrics {
    fn char_width(&self, ch: char) -> i16;
    fn line_height(&self) -> i16;
}

impl GlyphMetrics for Font {
    fn char_width(&self, ch: char) -> i16 {
        Font::char_width(*self, ch)
    }

    fn line_height(&self) -> i16 {
        Font::line_height(*self)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_selected_line_breaks() {
        assert_eq!(line_breaks("abcd ef", 34), vec![inside_word(2, 25)]);
    }

    #[test]
    fn test_break_text() {
        assert_eq!(
            break_text("abcd ef", 24),
            vec![
                Span {
                    text: "a",
                    append: Appendix::Hyphen
                },
                Span {
                    text: "bcd",
                    append: Appendix::None
                },
                Span {
                    text: "ef",
                    append: Appendix::None
                }
            ]
        )
    }

    #[derive(Copy, Clone)]
    struct Fixed {
        width: i16,
        height: i16,
    }

    impl GlyphMetrics for Fixed {
        fn char_width(&self, _ch: char) -> i16 {
            self.width
        }

        fn line_height(&self) -> i16 {
            self.height
        }
    }

    fn break_text(s: &str, w: i16) -> Vec<Span> {
        break_text_to_spans(
            s,
            Fixed {
                width: 10,
                height: 10,
            },
            Fixed {
                width: 5,
                height: 10,
            },
            LineBreaking::BreakWordsAndInsertHyphen,
            w,
        )
        .collect::<Vec<_>>()
    }

    fn line_breaks(s: &str, w: i16) -> Vec<LineBreak> {
        select_line_breaks(
            s.char_indices(),
            Fixed {
                width: 10,
                height: 10,
            },
            Fixed {
                width: 5,
                height: 10,
            },
            LineBreaking::BreakWordsAndInsertHyphen,
            w,
        )
        .collect::<Vec<_>>()
    }

    fn hard(offset: usize, width: i16) -> LineBreak {
        LineBreak {
            offset,
            width,
            style: BreakStyle::Hard,
        }
    }

    fn whitespace(offset: usize, width: i16) -> LineBreak {
        LineBreak {
            offset,
            width,
            style: BreakStyle::AtWhitespaceOrWordBoundary,
        }
    }

    fn inside_word(offset: usize, width: i16) -> LineBreak {
        LineBreak {
            offset,
            width,
            style: BreakStyle::InsideWord,
        }
    }
}
