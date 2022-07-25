use core::ops::Deref;

use heapless::String;

use crate::time::Duration;

use crate::ui::{display, geometry::Point, util};

use super::{theme, ButtonStyleSheet};

const MIDDLE_ROW: i32 = 62;
const LEFT_COL: i32 = 5;
const MIDDLE_COL: i32 = 64;
const RIGHT_COL: i32 = 123;

/// Helper to unite the row height.
fn row_height_bold() -> i32 {
    // It never reaches the maximum height
    theme::FONT_BOLD.line_height() - 2
}

/// Display header text.
pub fn display_header(baseline: Point, text: &str) {
    display::text(baseline, text, theme::FONT_HEADER, theme::FG, theme::BG);
}

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
    pub text: Option<T>,
    pub icon: Option<&'static [u8]>,
    // TODO: `icon_text` is just hack so that we can instantiate
    // HoldToConfirm element when text is None.
    pub icon_text: Option<T>,
    pub duration: Option<Duration>,
    pub is_cancel: bool,
    pub with_outline: bool,
    pub with_arms: bool,
    pub force_width: Option<i32>,
}

impl<T: Clone + AsRef<str>> ButtonDetails<T> {
    /// Text button.
    pub fn new(text: T) -> Self {
        Self {
            text: Some(text),
            icon: None,
            icon_text: None,
            duration: None,
            is_cancel: false,
            with_outline: true,
            with_arms: false,
            force_width: None,
        }
    }

    /// Icon button.
    /// NOTE: `icon_text` needs to be specified, any text is enough.
    pub fn icon(icon: &'static [u8], icon_text: T) -> Self {
        Self {
            text: None,
            icon: Some(icon),
            icon_text: Some(icon_text),
            duration: None,
            is_cancel: false,
            with_outline: true,
            with_arms: false,
            force_width: None,
        }
    }

    /// Cancel style button.
    pub fn with_cancel(mut self) -> Self {
        self.is_cancel = true;
        self
    }

    /// No outline around the button.
    pub fn with_no_outline(mut self) -> Self {
        self.with_outline = false;
        self
    }

    /// Left and right "arms" around the button.
    /// Automatically disabling the outline.
    pub fn with_arms(mut self) -> Self {
        self.with_arms = true;
        self.with_outline = false;
        self
    }

    /// Duration of the hold-to-confirm.
    pub fn with_duration(mut self, duration: Duration) -> Self {
        self.duration = Some(duration);
        self
    }

    /// Width of the button.
    pub fn force_width(mut self, width: i32) -> Self {
        self.force_width = Some(width);
        self
    }

    /// Print attributes for debugging purposes.
    pub fn print(&self) {
        let text = if let Some(text) = self.text.clone() {
            String::<20>::from(text.as_ref())
        } else {
            String::<20>::from("None")
        };
        let icon_text = if let Some(icon_text) = self.icon_text.clone() {
            String::<20>::from(icon_text.as_ref())
        } else {
            String::<20>::from("None")
        };
        let force_width = if let Some(force_width) = self.force_width {
            String::<20>::from(inttostr!(force_width))
        } else {
            String::<20>::from("None")
        };
        println!(
            "ButtonDetails:: text: ",
            text.as_ref(),
            ", icon_text: ",
            icon_text.as_ref(),
            ", with_outline: ",
            booltostr!(self.with_outline),
            ", with_arms: ",
            booltostr!(self.with_arms),
            ", force_width: ",
            force_width.as_ref()
        );
    }

    /// Button style that should be applied.
    pub fn style(&self) -> ButtonStyleSheet {
        if self.is_cancel {
            ButtonStyleSheet::cancel(self.with_outline, self.with_arms, self.force_width)
        } else {
            ButtonStyleSheet::default(self.with_outline, self.with_arms, self.force_width)
        }
    }

    /// Identifier of this button configuration.
    /// To quickly compare two buttons and see if there was a change.
    pub fn id(&self) -> String<60> {
        // TODO: we could maybe use `Eq` or `PartialEq` for comparison,
        // but that wold require some generic Trait changes (T: PartialEq),
        // which was not possible for AsRef<str>?
        let text = if let Some(text) = self.text.clone() {
            String::<20>::from(text.as_ref())
        } else {
            String::<20>::from("")
        };
        // TODO: the icon should be hashed, icon size is not really good but works for now
        let icon_size = if let Some(icon) = self.icon {
            icon.len()
        } else {
            0
        };
        let duration_ms = self.duration.unwrap_or(Duration::ZERO).to_millis();
        build_string!(
            60,
            text.as_ref(),
            "--",
            String::<10>::from(icon_size as u32).as_ref(),
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
    /// Custom texts for all three buttons.
    pub fn custom(left: &'static str, middle: &'static str, right: &'static str) -> Self {
        Self::new(
            Some(ButtonDetails::new(left)),
            Some(ButtonDetails::new(middle)),
            Some(ButtonDetails::new(right)),
        )
    }

    /// Default button layout for all three buttons.
    pub fn default_three() -> Self {
        Self::custom("<", "SELECT", ">")
    }

    /// Default button layout for all three buttons - icons.
    pub fn default_three_icons() -> Self {
        Self::new(
            Some(ButtonDetails::icon(theme::ICON_ARROW_LEFT, "arr_left").with_no_outline()),
            Some(ButtonDetails::new("SELECT").with_arms()),
            Some(ButtonDetails::icon(theme::ICON_ARROW_RIGHT, "arr_right").with_no_outline()),
        )
    }

    /// Just right and left, no middle.
    pub fn default_left_right() -> Self {
        Self::new(
            Some(ButtonDetails::new("<")),
            None,
            Some(ButtonDetails::new(">")),
        )
    }

    /// Setting a special middle text.
    pub fn special_middle(middle: &'static str) -> Self {
        Self::custom("<", middle, ">")
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

// TODO: support multiple font sizes - 64 in the middle and 32 on the edges.
// Do it at least for the PIN and BIP39, maybe passphrase as well.
// NOTE: beware of the size-limits of the flash - export just
// those symbols that we really need.
// Or maybe we could somehow scale the already existing symbols, not
// to use any more space.

impl ChoiceItem for StringChoiceItem {
    fn paint_center(&mut self) {
        // Displaying the center choice lower than the rest,
        // to make it more clear this is the current choice
        // (and also the left and right ones do not collide with it)
        display_bold_center(
            Point::new(MIDDLE_COL, MIDDLE_ROW + row_height_bold()),
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
            let offset = MIDDLE_ROW + index as i32 * row_height_bold() + row_height_bold();
            display_bold_center(Point::new(MIDDLE_COL, offset), line);
        }
    }

    fn paint_left(&mut self) {
        for (index, line) in self.text.split(self.delimiter).enumerate() {
            let offset = MIDDLE_ROW + index as i32 * row_height_bold();
            display_bold(Point::new(LEFT_COL, offset), line);
        }
    }

    fn paint_right(&mut self) {
        for (index, line) in self.text.split(self.delimiter).enumerate() {
            let offset = MIDDLE_ROW + index as i32 * row_height_bold();
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
        assert_eq!(btn.id(), String::<50>::from("Test--0--0"));
        let btn = ButtonDetails::new("Duration").with_duration(Duration::from_secs(1));
        assert_eq!(btn.id(), String::<50>::from("Duration--0--1000"));
    }
}
