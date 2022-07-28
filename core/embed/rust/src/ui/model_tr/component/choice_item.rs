use crate::ui::{geometry::Point, model_tr::theme, util};
use heapless::String;

use super::{
    common::{display, display_center, display_magnified, display_right},
    ButtonDetails, ButtonLayout,
};

const MIDDLE_ROW: i32 = 61;
const MIDDLE_ROW_BIG: i32 = 71;
const LEFT_COL: i32 = 1;
const MIDDLE_COL: i32 = 64;
const RIGHT_COL: i32 = 127;

/// Helper to unite the row height.
fn row_height() -> i32 {
    // It never reaches the maximum height
    theme::FONT_NORMAL.line_height() - 4
}

/// Component that can be used as a choice item.
/// Allows to have a choice of anything that can be painted on screen.
///
/// Controls the painting of the current, previous and next item
/// through `paint_XXX()` methods.
/// Defines the behavior of all three buttons through `btn_XXX` attributes.
///
/// Possible implementations:
/// - [x] `TextChoiceItem` - for regular text
/// - [x] `MultilineTextChoiceItem` - for multiline text
/// - [x] `BigCharacterChoiceItem` - for one big character
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
    Text(TextChoiceItem),
    MultilineText(MultilineTextChoiceItem),
    BigCharacter(BigCharacterChoiceItem),
}

impl ChoiceItems {
    // TODO: can we somehow avoid the repetitions here?
    pub fn set_left_btn(&mut self, btn_left: Option<ButtonDetails<&'static str>>) {
        match self {
            ChoiceItems::Text(item) => item.btn_layout.btn_left = btn_left,
            ChoiceItems::MultilineText(item) => item.btn_layout.btn_left = btn_left,
            ChoiceItems::BigCharacter(item) => item.btn_layout.btn_left = btn_left,
        }
    }

    pub fn set_middle_btn(&mut self, btn_middle: Option<ButtonDetails<&'static str>>) {
        match self {
            ChoiceItems::Text(item) => item.btn_layout.btn_middle = btn_middle,
            ChoiceItems::MultilineText(item) => item.btn_layout.btn_middle = btn_middle,
            ChoiceItems::BigCharacter(item) => item.btn_layout.btn_middle = btn_middle,
        }
    }

    pub fn set_right_btn(&mut self, btn_right: Option<ButtonDetails<&'static str>>) {
        match self {
            ChoiceItems::Text(item) => item.btn_layout.btn_right = btn_right,
            ChoiceItems::MultilineText(item) => item.btn_layout.btn_right = btn_right,
            ChoiceItems::BigCharacter(item) => item.btn_layout.btn_right = btn_right,
        }
    }

    pub fn set_text(&mut self, text: String<100>) {
        match self {
            ChoiceItems::Text(item) => item.text = text,
            ChoiceItems::MultilineText(item) => item.text = text,
            ChoiceItems::BigCharacter(_) => {
                panic!("No text setting for BigCharacter")
            }
        }
    }
}

impl ChoiceItem for ChoiceItems {
    fn paint_center(&mut self) {
        match self {
            ChoiceItems::Text(item) => item.paint_center(),
            ChoiceItems::MultilineText(item) => item.paint_center(),
            ChoiceItems::BigCharacter(item) => item.paint_center(),
        }
    }

    fn paint_left(&mut self) {
        match self {
            ChoiceItems::Text(item) => item.paint_left(),
            ChoiceItems::MultilineText(item) => item.paint_left(),
            ChoiceItems::BigCharacter(item) => item.paint_left(),
        }
    }

    fn paint_right(&mut self) {
        match self {
            ChoiceItems::Text(item) => item.paint_right(),
            ChoiceItems::MultilineText(item) => item.paint_right(),
            ChoiceItems::BigCharacter(item) => item.paint_right(),
        }
    }

    fn btn_layout(&self) -> ButtonLayout<&'static str> {
        match self {
            ChoiceItems::Text(item) => item.btn_layout(),
            ChoiceItems::MultilineText(item) => item.btn_layout(),
            ChoiceItems::BigCharacter(item) => item.btn_layout(),
        }
    }
}

/// Simple string component used as a choice item.
#[derive(Debug, Clone)]
pub struct TextChoiceItem {
    pub text: String<100>,
    pub btn_layout: ButtonLayout<&'static str>,
}

impl TextChoiceItem {
    pub fn from_str<T>(text: T, btn_layout: ButtonLayout<&'static str>) -> Self
    where
        T: AsRef<str>,
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

impl ChoiceItem for TextChoiceItem {
    fn paint_center(&mut self) {
        // Displaying the center choice lower than the rest,
        // to make it more clear this is the current choice
        // (and also the left and right ones do not collide with it)
        display_center(
            Point::new(MIDDLE_COL, MIDDLE_ROW + row_height()),
            self.text.as_str(),
            theme::FONT_NORMAL,
        );
    }

    fn paint_left(&mut self) {
        display(
            Point::new(LEFT_COL, MIDDLE_ROW),
            self.text.as_str(),
            theme::FONT_NORMAL,
        );
    }

    fn paint_right(&mut self) {
        display_right(
            Point::new(RIGHT_COL, MIDDLE_ROW),
            self.text.as_str(),
            theme::FONT_NORMAL,
        );
    }

    fn btn_layout(&self) -> ButtonLayout<&'static str> {
        self.btn_layout.clone()
    }
}

/// Multiline string component used as a choice item.
///
/// Lines are delimited by '\n' character, unless specified explicitly.
#[derive(Debug)]
pub struct MultilineTextChoiceItem {
    // Arbitrary chosen. TODO: agree on this
    pub text: String<100>,
    delimiter: char,
    pub btn_layout: ButtonLayout<&'static str>,
}

impl MultilineTextChoiceItem {
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

// TODO: Make all the text be centered vertically - account for amount of lines.
impl ChoiceItem for MultilineTextChoiceItem {
    fn paint_center(&mut self) {
        // Displaying the center choice lower than the rest,
        // to make it more clear this is the current choice
        for (index, line) in self.text.split(self.delimiter).enumerate() {
            let offset = MIDDLE_ROW + index as i32 * row_height() + row_height();
            display_center(Point::new(MIDDLE_COL, offset), line, theme::FONT_NORMAL);
        }
    }

    fn paint_left(&mut self) {
        for (index, line) in self.text.split(self.delimiter).enumerate() {
            let offset = MIDDLE_ROW + index as i32 * row_height();
            display(Point::new(LEFT_COL, offset), line, theme::FONT_NORMAL);
        }
    }

    fn paint_right(&mut self) {
        for (index, line) in self.text.split(self.delimiter).enumerate() {
            let offset = MIDDLE_ROW + index as i32 * row_height();
            display_right(Point::new(RIGHT_COL, offset), line, theme::FONT_NORMAL);
        }
    }

    fn btn_layout(&self) -> ButtonLayout<&'static str> {
        self.btn_layout.clone()
    }
}

/// Choice item displaying single characters in BIG font.
/// Middle choice is magnified 4 times, left and right 2 times.
#[derive(Debug, Clone)]
pub struct BigCharacterChoiceItem {
    pub ch: char,
    pub btn_layout: ButtonLayout<&'static str>,
}

impl BigCharacterChoiceItem {
    pub fn new(ch: char, btn_layout: ButtonLayout<&'static str>) -> Self {
        Self { ch, btn_layout }
    }

    /// Taking the first character from the `text`.
    pub fn from_str<T>(text: T, btn_layout: ButtonLayout<&'static str>) -> Self
    where
        T: AsRef<str>,
    {
        Self {
            ch: text.as_ref().chars().next().unwrap(),
            btn_layout,
        }
    }
}

impl ChoiceItem for BigCharacterChoiceItem {
    fn paint_center(&mut self) {
        display_magnified(self.ch, 4, Point::new(MIDDLE_COL - 12, MIDDLE_ROW_BIG + 9));
    }

    fn paint_left(&mut self) {
        display_magnified(self.ch, 2, Point::new(LEFT_COL, MIDDLE_ROW_BIG));
    }

    fn paint_right(&mut self) {
        display_magnified(self.ch, 2, Point::new(RIGHT_COL - 12, MIDDLE_ROW_BIG));
    }

    fn btn_layout(&self) -> ButtonLayout<&'static str> {
        self.btn_layout.clone()
    }
}
