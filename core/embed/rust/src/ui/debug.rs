//! Including some useful debugging features,
//! like printing of the struct details.

use heapless::String;

use super::component::pad::Pad;
use super::component::text::common::TextBox;
use super::component::text::layout::{Span, TextLayout};
use super::display::{Color, Font, Icon};
use super::geometry::{Grid, Insets, Offset, Point, Rect};
use super::model_tr::component::ButtonDetails;
use crate::micropython::buffer::StrBuffer;
use crate::time::Duration;

// NOTE: not defining a common trait, like
// Debug {fn print(&self);}, so that the trait does
// not need to be imported when using the
// print() function. It suits the use-case of being quickly
// able to use the print() for debugging and then delete it.

/// TODO: find out how much storage these functions take
/// and probably hide them behind debug feature

impl StrBuffer {
    pub fn print(&self) {
        println!("StrBuffer:: ", self.as_ref());
    }
}

impl Duration {
    pub fn print(&self) {
        println!("Duration:: ", inttostr!(self.to_millis()));
    }
}

impl Point {
    pub fn print(&self) {
        println!(
            "Point:: ",
            "x: ",
            inttostr!(self.x),
            ", y: ",
            inttostr!(self.y)
        );
    }
}

impl Rect {
    pub fn print(&self) {
        println!(
            "Rect:: ",
            "x0: ",
            inttostr!(self.x0),
            ", y0: ",
            inttostr!(self.y0),
            ", x1: ",
            inttostr!(self.x1),
            ", y1: ",
            inttostr!(self.y1)
        );
    }
}

impl Color {
    pub fn print(&self) {
        println!(
            "Color:: ",
            "R: ",
            inttostr!(self.r()),
            ", G: ",
            inttostr!(self.g()),
            ", B: ",
            inttostr!(self.b())
        );
    }
}

impl Font {
    pub fn print(&self) {
        println!("Font:: ", "text_height: ", inttostr!(self.text_height()));
    }
}

impl<T: Clone + AsRef<str>> ButtonDetails<T> {
    pub fn print(&self) {
        let text = if let Some(text) = self.text.clone() {
            String::<20>::from(text.as_ref())
        } else {
            String::<20>::from("None")
        };
        let icon_text = if let Some(icon) = &self.icon {
            String::<20>::from(icon.text.as_ref())
        } else {
            String::<20>::from("None")
        };
        let force_width = if let Some(force_width) = self.force_width {
            String::<20>::from(inttostr!(force_width))
        } else {
            String::<20>::from("None")
        };
        println!(
            "ButtonDetails:: ",
            "text: ",
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
}

impl Offset {
    pub fn print(&self) {
        println!(
            "Offset:: ",
            "x: ",
            inttostr!(self.x),
            ", y: ",
            inttostr!(self.y)
        );
    }
}

impl Insets {
    pub fn print(&self) {
        println!(
            "Insets:: ",
            "top: ",
            inttostr!(self.top),
            ", right: ",
            inttostr!(self.right),
            ", bottom: ",
            inttostr!(self.bottom),
            ", left: ",
            inttostr!(self.left)
        );
    }
}

impl Grid {
    pub fn print(&self) {
        print!(
            "Grid:: ",
            "rows: ",
            inttostr!(self.rows as i32),
            ", cols: ",
            inttostr!(self.cols as i32),
            ", spacing: ",
            inttostr!(self.spacing as i32)
        );
        print!(", area: ");
        self.area.print();
    }
}

impl<T: AsRef<str>> Icon<T> {
    pub fn print(&self) {
        println!(
            "Icon:: ",
            "text: ",
            self.text.as_ref(),
            ", width: ",
            inttostr!(self.width() as i32),
            ", height: ",
            inttostr!(self.height() as i32)
        );
    }
}

impl TextLayout {
    pub fn print(&self) {
        print!(
            "TextLayout:: ",
            "padding_top: ",
            inttostr!(self.padding_top as i32),
            ", padding_bottom: ",
            inttostr!(self.padding_bottom as i32)
        );
        print!(", bounds: ");
        self.bounds.print();
    }
}

impl Span {
    pub fn print(&self) {
        print!(
            "Span:: ",
            "length: ",
            inttostr!(self.length as i32),
            ", skip_next_chars: ",
            inttostr!(self.skip_next_chars as i32),
            ", insert_hyphen_before_line_break: ",
            booltostr!(self.insert_hyphen_before_line_break)
        );
        print!(", advance: ");
        self.advance.print();
    }
}

impl Pad {
    pub fn print(&self) {
        print!("Pad:: ", "area: ");
        self.area.print();
    }
}

impl<const L: usize> TextBox<L> {
    pub fn print(&self) {
        println!("TextBox:: ", "content: ", self.content());
    }
}
