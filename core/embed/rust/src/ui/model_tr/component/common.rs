use core::ops::Deref;

use heapless::String;

use crate::{time::Duration, util};

use crate::ui::{display, geometry::Point};

use super::theme;

const MIDDLE_ROW: i32 = 72;
const LEFT_COL: i32 = 5;
const MIDDLE_COL: i32 = 64;
const RIGHT_COL: i32 = 123;

const ROW_HEIGHT: i32 = 10;

/// Display bold white text on black background
pub fn display_bold(baseline: Point, text: &str) {
    display::text(baseline, text, theme::FONT_BOLD, theme::FG, theme::BG);
}

/// Display bold white text on black background,
/// centered around a baseline Point
pub fn display_bold_center(baseline: Point, text: &str) {
    display::text_center(baseline, text, theme::FONT_BOLD, theme::FG, theme::BG);
}

/// Display bold white text on black background,
/// with right boundary at a baseline Point
pub fn display_bold_right(baseline: Point, text: &str) {
    display::text_right(baseline, text, theme::FONT_BOLD, theme::FG, theme::BG);
}

/// Component that can be used as a choice item.
/// Allows to have a choice of anything that can be painted on screen.
///
/// Controls the painting of the current, previous and next item
/// through `paint_XXX()` methods.
/// Defines the behavior of all three buttons through `btn_XXX` attributes.
///
/// Possible implementations:
/// - [x] `StringChoiceItem` - for regular text
/// - [x] `MultilineStringChoiceItem` - for multiline text
/// - [ ] `IconChoiceItem` - for showing icons
/// - [ ] `JustCenterChoice` - paint_left() and paint_right() show nothing
/// - [ ] `LongStringsChoice` - paint_left() and paint_right() show ellipsis
pub trait ChoiceItem {
    fn paint_center(&mut self);
    fn paint_left(&mut self);
    fn paint_right(&mut self);
    fn btn_left(&mut self) -> Option<ButtonDetails>;
    fn btn_middle(&mut self) -> Option<ButtonDetails>;
    fn btn_right(&mut self) -> Option<ButtonDetails>;
}

/// Describing the button in the choice item.
#[derive(Debug, Clone, Copy)]
pub struct ButtonDetails {
    pub text: &'static str,
    pub duration: Option<Duration>,
}

impl ButtonDetails {
    pub fn new(text: &'static str) -> Self {
        Self {
            text,
            duration: None,
        }
    }

    pub fn with_duration(mut self, duration: Duration) -> Self {
        self.duration = Some(duration);
        self
    }
}

/// Simple string component used as a choice item.
#[derive(Debug, Clone)]
pub struct StringChoiceItem {
    pub text: String<100>,
    pub btn_left: Option<ButtonDetails>,
    pub btn_middle: Option<ButtonDetails>,
    pub btn_right: Option<ButtonDetails>,
}

impl StringChoiceItem {
    pub fn from_str<T>(
        text: T,
        btn_left: Option<ButtonDetails>,
        btn_middle: Option<ButtonDetails>,
        btn_right: Option<ButtonDetails>,
    ) -> Self
    where
        T: Deref<Target = str>,
    {
        Self {
            text: String::from(text.as_ref()),
            btn_left,
            btn_middle,
            btn_right,
        }
    }

    pub fn from_char(
        ch: char,
        btn_left: Option<ButtonDetails>,
        btn_middle: Option<ButtonDetails>,
        btn_right: Option<ButtonDetails>,
    ) -> Self {
        Self {
            text: util::char_to_string(ch),
            btn_left,
            btn_middle,
            btn_right,
        }
    }
}

impl ChoiceItem for StringChoiceItem {
    fn paint_center(&mut self) {
        // Displaying the center choice lower than the rest,
        // to make it more clear this is the current choice
        // (and also the left and right ones do not collide with it)
        display_bold_center(
            Point::new(MIDDLE_COL, MIDDLE_ROW + ROW_HEIGHT),
            self.text.as_str(),
        );
    }

    fn paint_left(&mut self) {
        display_bold(Point::new(LEFT_COL, MIDDLE_ROW), self.text.as_str());
    }

    fn paint_right(&mut self) {
        display_bold_right(Point::new(RIGHT_COL, MIDDLE_ROW), self.text.as_str());
    }

    fn btn_left(&mut self) -> Option<ButtonDetails> {
        self.btn_left
    }

    fn btn_middle(&mut self) -> Option<ButtonDetails> {
        self.btn_middle
    }

    fn btn_right(&mut self) -> Option<ButtonDetails> {
        self.btn_right
    }
}

/// Multiline string component used as a choice item.
///
/// Lines are delimited by '\n' character, unless specified explicitly.
#[derive(Debug)]
pub struct MultilineStringChoiceItem {
    // Arbitrary chosen. TODO: agree on this
    pub text: String<100>,
    delimiter: char,
    pub btn_left: Option<ButtonDetails>,
    pub btn_middle: Option<ButtonDetails>,
    pub btn_right: Option<ButtonDetails>,
}

impl MultilineStringChoiceItem {
    pub fn new(
        text: String<100>,
        btn_left: Option<ButtonDetails>,
        btn_middle: Option<ButtonDetails>,
        btn_right: Option<ButtonDetails>,
    ) -> Self {
        Self {
            text,
            delimiter: '\n',
            btn_left,
            btn_middle,
            btn_right,
        }
    }

    /// Allows for changing the line delimiter to arbitrary char.
    pub fn use_delimiter(mut self, delimiter: char) -> Self {
        self.delimiter = delimiter;
        self
    }
}

impl ChoiceItem for MultilineStringChoiceItem {
    fn paint_center(&mut self) {
        // Displaying the center choice lower than the rest,
        // to make it more clear this is the current choice
        for (index, line) in self.text.split(self.delimiter).enumerate() {
            let offset = MIDDLE_ROW + index as i32 * ROW_HEIGHT + ROW_HEIGHT;
            display_bold_center(Point::new(MIDDLE_COL, offset), line);
        }
    }

    fn paint_left(&mut self) {
        for (index, line) in self.text.split(self.delimiter).enumerate() {
            let offset = MIDDLE_ROW + index as i32 * ROW_HEIGHT;
            display_bold(Point::new(LEFT_COL, offset), line);
        }
    }

    fn paint_right(&mut self) {
        for (index, line) in self.text.split(self.delimiter).enumerate() {
            let offset = MIDDLE_ROW + index as i32 * ROW_HEIGHT;
            display_bold_right(Point::new(RIGHT_COL, offset), line);
        }
    }

    fn btn_left(&mut self) -> Option<ButtonDetails> {
        self.btn_left
    }

    fn btn_middle(&mut self) -> Option<ButtonDetails> {
        self.btn_middle
    }

    fn btn_right(&mut self) -> Option<ButtonDetails> {
        self.btn_right
    }
}
