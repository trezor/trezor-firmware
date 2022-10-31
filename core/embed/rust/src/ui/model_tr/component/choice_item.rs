use crate::ui::{geometry::Point, display::Font, util::char_to_string};
use heapless::String;

use super::{
    common::{display, display_center, display_right},
    ButtonDetails, ButtonLayout,
};

const MIDDLE_ROW: i16 = 61;
const LEFT_COL: i16 = 1;
const MIDDLE_COL: i16 = 64;
const RIGHT_COL: i16 = 127;

/// Helper to unite the row height.
fn row_height() -> i16 {
    // It never reaches the maximum height
    Font::NORMAL.line_height() - 4
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
pub trait ChoiceItemAPI {
    fn paint_center(&mut self);
    fn paint_left(&mut self);
    fn paint_right(&mut self);
    fn btn_layout(&self) -> ButtonLayout<&'static str>;
}

// TODO: consider having
// pub trait ChoiceItemOperations {}

// TODO: consider storing all the text components as `T: AsRef<str>`
// Tried, but it makes the code unnecessarily messy with all the <T>
// definitions, which needs to be added to all the components using it.

/// Storing all the possible implementations of `ChoiceItemAPI`.
/// Done like this as we want to use multiple different choice pages
/// at the same time in `ChoicePage` - for example Multiline and BigLetters
#[derive(Clone)]
pub enum ChoiceItem {
    Text(TextChoiceItem),
    MultilineText(MultilineTextChoiceItem),
    BigCharacter(BigCharacterChoiceItem),
}

impl ChoiceItem {
    // TODO: can we somehow avoid the repetitions here?
    pub fn set_left_btn(&mut self, btn_left: Option<ButtonDetails<&'static str>>) {
        match self {
            ChoiceItem::Text(item) => item.btn_layout.btn_left = btn_left,
            ChoiceItem::MultilineText(item) => item.btn_layout.btn_left = btn_left,
            ChoiceItem::BigCharacter(item) => item.btn_layout.btn_left = btn_left,
        }
    }

    pub fn set_middle_btn(&mut self, btn_middle: Option<ButtonDetails<&'static str>>) {
        match self {
            ChoiceItem::Text(item) => item.btn_layout.btn_middle = btn_middle,
            ChoiceItem::MultilineText(item) => item.btn_layout.btn_middle = btn_middle,
            ChoiceItem::BigCharacter(item) => item.btn_layout.btn_middle = btn_middle,
        }
    }

    pub fn set_right_btn(&mut self, btn_right: Option<ButtonDetails<&'static str>>) {
        match self {
            ChoiceItem::Text(item) => item.btn_layout.btn_right = btn_right,
            ChoiceItem::MultilineText(item) => item.btn_layout.btn_right = btn_right,
            ChoiceItem::BigCharacter(item) => item.btn_layout.btn_right = btn_right,
        }
    }

    pub fn set_text(&mut self, text: String<50>) {
        match self {
            ChoiceItem::Text(item) => item.text = text,
            ChoiceItem::MultilineText(item) => item.text = text,
            ChoiceItem::BigCharacter(_) => {
                panic!("No text setting for BigCharacter")
            }
        }
    }
}

impl ChoiceItemAPI for ChoiceItem {
    fn paint_center(&mut self) {
        match self {
            ChoiceItem::Text(item) => item.paint_center(),
            ChoiceItem::MultilineText(item) => item.paint_center(),
            ChoiceItem::BigCharacter(item) => item.paint_center(),
        }
    }

    fn paint_left(&mut self) {
        match self {
            ChoiceItem::Text(item) => item.paint_left(),
            ChoiceItem::MultilineText(item) => item.paint_left(),
            ChoiceItem::BigCharacter(item) => item.paint_left(),
        }
    }

    fn paint_right(&mut self) {
        match self {
            ChoiceItem::Text(item) => item.paint_right(),
            ChoiceItem::MultilineText(item) => item.paint_right(),
            ChoiceItem::BigCharacter(item) => item.paint_right(),
        }
    }

    fn btn_layout(&self) -> ButtonLayout<&'static str> {
        match self {
            ChoiceItem::Text(item) => item.btn_layout(),
            ChoiceItem::MultilineText(item) => item.btn_layout(),
            ChoiceItem::BigCharacter(item) => item.btn_layout(),
        }
    }
}

/// Simple string component used as a choice item.
#[derive(Clone)]
pub struct TextChoiceItem {
    pub text: String<50>,
    pub btn_layout: ButtonLayout<&'static str>,
}

impl TextChoiceItem {
    pub fn new<T>(text: T, btn_layout: ButtonLayout<&'static str>) -> Self
    where
        T: AsRef<str>,
    {
        Self {
            text: String::from(text.as_ref()),
            btn_layout,
        }
    }
}

impl ChoiceItemAPI for TextChoiceItem {
    fn paint_center(&mut self) {
        // Displaying the center choice lower than the rest,
        // to make it more clear this is the current choice
        // (and also the left and right ones do not collide with it)
        display_center(
            Point::new(MIDDLE_COL, MIDDLE_ROW + row_height()),
            &self.text,
            Font::NORMAL,
        );
    }

    fn paint_left(&mut self) {
        display(
            Point::new(LEFT_COL, MIDDLE_ROW),
            &self.text,
            Font::NORMAL,
        );
    }

    fn paint_right(&mut self) {
        display_right(
            Point::new(RIGHT_COL, MIDDLE_ROW),
            &self.text,
            Font::NORMAL,
        );
    }

    fn btn_layout(&self) -> ButtonLayout<&'static str> {
        self.btn_layout.clone()
    }
}

/// Multiline string component used as a choice item.
///
/// Lines are delimited by '\n' character, unless specified explicitly.
#[derive(Clone)]
pub struct MultilineTextChoiceItem {
    // Arbitrary chosen. TODO: agree on this
    pub text: String<50>,
    delimiter: char,
    pub btn_layout: ButtonLayout<&'static str>,
}

impl MultilineTextChoiceItem {
    pub fn new(text: String<50>, btn_layout: ButtonLayout<&'static str>) -> Self {
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
impl ChoiceItemAPI for MultilineTextChoiceItem {
    fn paint_center(&mut self) {
        // Displaying the center choice lower than the rest,
        // to make it more clear this is the current choice
        for (index, line) in self.text.split(self.delimiter).enumerate() {
            let offset = MIDDLE_ROW + index as i16 * row_height() + row_height();
            display_center(Point::new(MIDDLE_COL, offset), &line, Font::NORMAL);
        }
    }

    fn paint_left(&mut self) {
        for (index, line) in self.text.split(self.delimiter).enumerate() {
            let offset = MIDDLE_ROW + index as i16 * row_height();
            display(Point::new(LEFT_COL, offset), &line, Font::NORMAL);
        }
    }

    fn paint_right(&mut self) {
        for (index, line) in self.text.split(self.delimiter).enumerate() {
            let offset = MIDDLE_ROW + index as i16 * row_height();
            display_right(Point::new(RIGHT_COL, offset), &line, Font::NORMAL);
        }
    }

    fn btn_layout(&self) -> ButtonLayout<&'static str> {
        self.btn_layout.clone()
    }
}

/// Choice item displaying single characters in BIG font.
/// Middle choice is magnified 4 times, left and right 2 times.
#[derive(Clone)]
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

    fn _paint_char(&mut self, baseline: Point) {
        display(
            baseline,
            &char_to_string::<1>(self.ch),
            Font::NORMAL,
        );
    }

}

impl ChoiceItemAPI for BigCharacterChoiceItem {
    fn paint_center(&mut self) {
        self._paint_char(Point::new(MIDDLE_COL - 12, MIDDLE_ROW + 9));
    }

    fn paint_left(&mut self) {
        self._paint_char(Point::new(LEFT_COL, MIDDLE_ROW));
    }

    fn paint_right(&mut self) {
        self._paint_char(Point::new(RIGHT_COL - 12, MIDDLE_ROW));
    }

    fn btn_layout(&self) -> ButtonLayout<&'static str> {
        self.btn_layout.clone()
    }
}

#[cfg(feature = "ui_debug")]
impl crate::trace::Trace for ChoiceItem {
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.open("ChoiceItem");
        match self {
            ChoiceItem::Text(item) => item.trace(t),
            ChoiceItem::MultilineText(item) => item.trace(t),
            ChoiceItem::BigCharacter(item) => item.trace(t),
        }
        t.close();
    }
}

#[cfg(feature = "ui_debug")]
impl crate::trace::Trace for TextChoiceItem {
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.open("TextChoiceItem");
        t.content_flag();
        t.string(&self.text);
        t.content_flag();
        t.close();
    }
}

#[cfg(feature = "ui_debug")]
use crate::ui::util;

#[cfg(feature = "ui_debug")]
impl crate::trace::Trace for MultilineTextChoiceItem {
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.open("MultilineTextChoiceItem");
        t.content_flag();
        t.string(&self.text);
        t.content_flag();
        t.field("delimiter", &(util::char_to_string::<1>(self.delimiter)));
        t.close();
    }
}

#[cfg(feature = "ui_debug")]
impl crate::trace::Trace for BigCharacterChoiceItem {
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.open("BigCharacterChoiceItem");
        t.content_flag();
        t.string(&util::char_to_string::<1>(self.ch));
        t.content_flag();
        t.close();
    }
}
