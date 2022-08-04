//! Including some useful debugging features,
//! like printing of the struct details.

use heapless::String;

use super::display::Color;
use super::geometry::{Point, Rect};
use super::model_tr::component::ButtonDetails;

// NOTE: not defining a common trait, like
// Debug {fn print(&self);}, so that the trait does
// not need to be imported when using the
// print() function. It suits the use-case of being quickly
// able to use the print() for debugging and then delete it.

/// TODO: find out how much storage these functions take
/// and probably hide them behind debug feature

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
