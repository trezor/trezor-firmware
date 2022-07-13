use core::ops::Deref;

use heapless::String;

use crate::time::Duration;

use crate::ui::{display, geometry::Point, util};

use super::{theme, ButtonStyleSheet};

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
    fn btn_layout(&self) -> ButtonLayout<&'static str>;
}

/// Describing the button in the choice item.
#[derive(Debug, Clone, Copy)]
pub struct ButtonDetails<T> {
    pub text: T,
    pub duration: Option<Duration>,
    pub is_cancel: bool,
}

impl<T: AsRef<str>> ButtonDetails<T> {
    pub fn new(text: T) -> Self {
        Self {
            text,
            duration: None,
            is_cancel: false,
        }
    }

    pub fn cancel(text: T) -> Self {
        Self {
            text,
            duration: None,
            is_cancel: true,
        }
    }

    pub fn with_duration(mut self, duration: Duration) -> Self {
        self.duration = Some(duration);
        self
    }

    pub fn style(&self) -> ButtonStyleSheet {
        if self.is_cancel {
            theme::button_cancel()
        } else {
            theme::button_default()
        }
    }

    /// Identifier of this button configuration.
    /// To quickly compare two buttons and see if there was a change.
    pub fn id(&self) -> String<50> {
        // TODO: we could maybe use `Eq` or `PartialEq` for comparison,
        // but that wold require some generic Trait changes (T: PartialEq),
        // which was not possible for AsRef<str>?
        let duration_ms = self.duration.unwrap_or(Duration::ZERO).to_millis();
        build_string!(
            50,
            self.text.as_ref(),
            "--",
            String::<20>::from(duration_ms).as_ref()
        )
    }
}

/// Holding the button details for all three possible buttons.
#[derive(Debug, Clone)]
pub struct ButtonLayout<T> {
    pub btn_left: Option<ButtonDetails<T>>,
    pub btn_middle: Option<ButtonDetails<T>>,
    pub btn_right: Option<ButtonDetails<T>>,
}

impl<T: AsRef<str>> ButtonLayout<T> {
    pub fn new(
        btn_left: Option<ButtonDetails<T>>,
        btn_middle: Option<ButtonDetails<T>>,
        btn_right: Option<ButtonDetails<T>>,
    ) -> Self {
        Self {
            btn_left,
            btn_middle,
            btn_right,
        }
    }

    /// Empty layout for when we cannot yet tell which buttons
    /// should be on the screen.
    pub fn empty() -> Self {
        Self::new(None, None, None)
    }
}

impl ButtonLayout<&'static str> {
    /// Default button layout for all three buttons.
    pub fn default_three() -> Self {
        Self::new(
            Some(ButtonDetails::new("BACK")),
            Some(ButtonDetails::new("SELECT")),
            Some(ButtonDetails::new("NEXT")),
        )
    }

    /// Default button layout for all three buttons.
    pub fn default_left_right() -> Self {
        Self::new(
            Some(ButtonDetails::new("BACK")),
            None,
            Some(ButtonDetails::new("NEXT")),
        )
    }
}

/// Simple string component used as a choice item.
#[derive(Debug, Clone)]
pub struct StringChoiceItem {
    pub text: String<100>,
    pub btn_layout: ButtonLayout<&'static str>,
}

impl StringChoiceItem {
    pub fn from_str<T>(text: T, btn_layout: ButtonLayout<&'static str>) -> Self
    where
        T: Deref<Target = str>,
    {
        Self {
            text: String::from(text.as_ref()),
            btn_layout,
        }
    }

    pub fn from_char(ch: char, btn_layout: ButtonLayout<&'static str>) -> Self {
        Self {
            text: util::char_to_string(ch),
            btn_layout,
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

    fn btn_layout(&self) -> ButtonLayout<&'static str> {
        self.btn_layout.clone()
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
    pub btn_layout: ButtonLayout<&'static str>,
}

impl MultilineStringChoiceItem {
    pub fn new(text: String<100>, btn_layout: ButtonLayout<&'static str>) -> Self {
        Self {
            text,
            delimiter: '\n',
            btn_layout,
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

    fn btn_layout(&self) -> ButtonLayout<&'static str> {
        self.btn_layout.clone()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_btn_details_id() {
        let btn = ButtonDetails::new("Test");
        assert_eq!(btn.id(), String::<50>::from("Test--0"));
        let btn = ButtonDetails::new("Duration").with_duration(Duration::from_secs(1));
        assert_eq!(btn.id(), String::<50>::from("Duration--1000"));
    }
}
