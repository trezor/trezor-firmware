//! Including some useful debugging features,
//! like printing of the struct details.

use heapless::String;

use super::{
    component::{
        pad::Pad,
        text::{
            common::TextBox,
            layout::{Span, TextLayout},
        },
    },
    display::{Color, Font, Icon},
    geometry::{Grid, Insets, Offset, Point, Rect},
};
use crate::{micropython::buffer::StrBuffer, time::Duration};

#[cfg(feature = "model_tr")]
use super::model_tr::component::ButtonDetails;

// NOTE: not defining a common trait, like
// Debug {fn print(&self);}, so that the trait does
// not need to be imported when using the
// print() function. It suits the use-case of being quickly
// able to use the print() for debugging and then delete it.

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
        print!("Rect:: ");
        println!(&self.corners_points());
    }

    pub fn corners_points(&self) -> String<30> {
        build_string!(
            30,
            "(",
            inttostr!(self.x0),
            ",",
            inttostr!(self.y0),
            "), (",
            inttostr!(self.x1),
            ",",
            inttostr!(self.y1),
            ")"
        )
    }
}

#[cfg(feature = "ui_debug")]
impl crate::trace::Trace for Rect {
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.open("Rect");
        t.string(&self.corners_points());
        t.close();
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

#[cfg(feature = "model_tr")]
impl ButtonDetails {
    pub fn print(&self) {
        let text: String<20> = if let Some(text) = self.text {
            text.as_ref().into()
        } else {
            "None".into()
        };
        let force_width: String<20> = if let Some(force_width) = self.force_width {
            inttostr!(force_width).into()
        } else {
            "None".into()
        };
        println!(
            "ButtonDetails:: ",
            "text: ",
            text.as_ref(),
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

impl Icon {
    pub fn dimension_str(&self) -> String<10> {
        build_string!(
            10,
            inttostr!(self.toif.width() as i32),
            "x",
            inttostr!(self.toif.height() as i32)
        )
    }

    pub fn print(&self) {
        println!(
            "Icon:: ",
            "width: ",
            inttostr!(self.toif.width() as i32),
            ", height: ",
            inttostr!(self.toif.height() as i32)
        );
    }
}

#[cfg(feature = "ui_debug")]
impl crate::trace::Trace for Icon {
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.open("Icon");
        t.string(&self.dimension_str());
        t.close();
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
            if self.insert_hyphen_before_line_break {
                "true"
            } else {
                "false"
            }
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
