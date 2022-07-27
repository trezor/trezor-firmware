use crate::ui::{geometry::Point, util};
use core::ops::Deref;
use heapless::String;

use super::{
    common::{display_bold, display_bold_center, display_bold_right, row_height_bold},
    ButtonDetails, ButtonLayout,
};

const MIDDLE_ROW: i32 = 62;
const LEFT_COL: i32 = 5;
const MIDDLE_COL: i32 = 64;
const RIGHT_COL: i32 = 123;

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
/// - [ ] `BigStringChoiceItem` - for big text
/// - [ ] `IconChoiceItem` - for showing icons
/// - [ ] `JustCenterChoice` - paint_left() and paint_right() show nothing
/// - [ ] `LongStringsChoice` - paint_left() and paint_right() show ellipsis
pub trait ChoiceItem {
    fn paint_center(&mut self);
    fn paint_left(&mut self);
    fn paint_right(&mut self);
    fn btn_layout(&self) -> ButtonLayout<&'static str>;
}

// TODO: consider having
// pub trait ChoiceItemOperations {}

/// Storing all the possible implementations of `ChoiceItem`.
/// Done like this as we want to use multiple different choice pages
/// at the same time in `ChoicePage` - for example Multiline and BigLetters
#[derive(Debug)]
pub enum ChoiceItems {
    String(StringChoiceItem),
    MultilineString(MultilineStringChoiceItem),
}

impl ChoiceItems {
    pub fn set_left_btn(&mut self, btn_left: Option<ButtonDetails<&'static str>>) {
        match self {
            ChoiceItems::String(item) => item.btn_layout.btn_left = btn_left,
            ChoiceItems::MultilineString(item) => item.btn_layout.btn_left = btn_left,
        }
    }

    pub fn set_middle_btn(&mut self, btn_middle: Option<ButtonDetails<&'static str>>) {
        match self {
            ChoiceItems::String(item) => item.btn_layout.btn_middle = btn_middle,
            ChoiceItems::MultilineString(item) => item.btn_layout.btn_middle = btn_middle,
        }
    }

    pub fn set_right_btn(&mut self, btn_right: Option<ButtonDetails<&'static str>>) {
        match self {
            ChoiceItems::String(item) => item.btn_layout.btn_right = btn_right,
            ChoiceItems::MultilineString(item) => item.btn_layout.btn_right = btn_right,
        }
    }

    pub fn set_text(&mut self, text: String<100>) {
        match self {
            ChoiceItems::String(item) => item.text = text,
            ChoiceItems::MultilineString(item) => item.text = text,
        }
    }
}

impl ChoiceItem for ChoiceItems {
    fn paint_center(&mut self) {
        match self {
            ChoiceItems::String(item) => item.paint_center(),
            ChoiceItems::MultilineString(item) => item.paint_center(),
        }
    }

    fn paint_left(&mut self) {
        match self {
            ChoiceItems::String(item) => item.paint_left(),
            ChoiceItems::MultilineString(item) => item.paint_left(),
        }
    }

    fn paint_right(&mut self) {
        match self {
            ChoiceItems::String(item) => item.paint_right(),
            ChoiceItems::MultilineString(item) => item.paint_right(),
        }
    }

    fn btn_layout(&self) -> ButtonLayout<&'static str> {
        match self {
            ChoiceItems::String(item) => item.btn_layout(),
            ChoiceItems::MultilineString(item) => item.btn_layout(),
        }
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
