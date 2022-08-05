use crate::{
    micropython::buffer::StrBuffer,
    ui::{
        display::{Font, Icon},
        geometry::Point,
        model_tr::theme,
    },
};
use heapless::{String, Vec};

use super::flow::BtnActions;
use super::{common, ButtonLayout};

pub trait FlowPage {
    fn paint(&mut self, left_top: Point);
    fn btn_layout(&self) -> ButtonLayout<&'static str>;
    fn btn_actions(&self) -> BtnActions;
}

// TODO: consider using `dyn` instead of `enum` to allow
// for more components implementing `FlowPage`
// Alloc screen by GC .. gc alloc, new
// dyn... gc dyn obj component
// Vec<Gc<dyn FlowPage>, 2>...

#[derive(Clone, Debug)]
pub enum FlowPages<T> {
    RecipientAddress(RecipientAddressPage<T>),
    KeyValueIcon(KeyValueIconPage<T>),
}

impl<T> FlowPage for FlowPages<T>
where
    T: AsRef<str>,
    T: Clone,
{
    fn paint(&mut self, left_top: Point) {
        match self {
            FlowPages::RecipientAddress(item) => item.paint(left_top),
            FlowPages::KeyValueIcon(item) => item.paint(left_top),
        }
    }

    fn btn_layout(&self) -> ButtonLayout<&'static str> {
        match self {
            FlowPages::RecipientAddress(item) => item.btn_layout(),
            FlowPages::KeyValueIcon(item) => item.btn_layout(),
        }
    }

    fn btn_actions(&self) -> BtnActions {
        match self {
            FlowPages::RecipientAddress(item) => item.btn_actions(),
            FlowPages::KeyValueIcon(item) => item.btn_actions(),
        }
    }
}

/// Page displaying recipient address.
#[derive(Debug, Clone)]
pub struct RecipientAddressPage<T> {
    address: T,
    btn_layout: ButtonLayout<&'static str>,
    btn_actions: BtnActions,
}

impl<T> RecipientAddressPage<T>
where
    T: AsRef<str>,
{
    pub fn new(
        address: T,
        btn_layout: ButtonLayout<&'static str>,
        btn_actions: BtnActions,
    ) -> Self {
        Self {
            address,
            btn_layout,
            btn_actions,
        }
    }
}

impl<T> FlowPage for RecipientAddressPage<T>
where
    T: AsRef<str>,
{
    fn paint(&mut self, left_top: Point) {
        let x_start = left_top.x;
        let mut y_offset = left_top.y;

        let used_font = theme::FONT_NORMAL;
        y_offset += used_font.line_height();

        common::icon_with_text(
            Point::new(x_start, y_offset),
            Icon::new(theme::ICON_USER, "user"),
            "Recipient",
            used_font,
        );

        // Showing the address in chunks of 4 characters, with 3 chunks per line.
        // Putting two spaces between chunks on the same line.

        // TODO: we could have this logic in python and just sending the
        // list of strings (one per line) with already inserted spaces.

        const CHUNK_SIZE: usize = 4;
        const CHUNKS_PER_PAGE: usize = 3;
        const ROW_CHARS: usize = CHUNK_SIZE * CHUNKS_PER_PAGE;
        let line_height: i32 = theme::FONT_BOLD.line_height();

        // Taproot addresses are 62 characters, so rather allocating a little more
        // TODO: however, these 62 characters do not fit properly on the screen,
        // we can fit 5 rows by 12 characters, the last two are colliding with
        // the left button.
        let addr_str: String<80> = String::from(self.address.as_ref());
        let rows: Vec<&str, 8> = addr_str
            .as_bytes()
            .chunks(ROW_CHARS)
            .map(|buf| unsafe { core::str::from_utf8_unchecked(buf) })
            .collect();

        for row in rows.iter() {
            let mut buf: String<{ 2 * ROW_CHARS }> = String::new();
            for (ch_id, ch) in row.chars().enumerate() {
                buf.push(ch).unwrap();
                if ch_id % CHUNK_SIZE == CHUNK_SIZE - 1 {
                    buf.push(' ').unwrap();
                    buf.push(' ').unwrap();
                }
            }
            y_offset += line_height;
            common::display(
                Point::new(x_start, y_offset),
                buf.as_str(),
                theme::FONT_BOLD,
            );
        }
    }

    fn btn_layout(&self) -> ButtonLayout<&'static str> {
        self.btn_layout.clone()
    }

    fn btn_actions(&self) -> BtnActions {
        self.btn_actions.clone()
    }
}

/// Holding data for one element of key-value pair with icon.
/// Also allowing these to be drawn at a certain Point.
#[derive(Debug, Clone, Copy)]
pub struct KeyValueIcon<T> {
    pub label: T,
    pub value: T,
    pub label_font: Font,
    pub value_font: Font,
    pub icon: Icon<T>,
}

impl<T> KeyValueIcon<T>
where
    T: AsRef<str>,
    T: Clone,
{
    pub fn new(label: T, value: T, label_font: Font, value_font: Font, icon: Icon<T>) -> Self {
        Self {
            label,
            value,
            label_font,
            value_font,
            icon,
        }
    }

    /// New element with normal font for label and bold font for value.
    pub fn normal_bold(label: T, value: T, icon: Icon<T>) -> Self {
        Self::new(label, value, theme::FONT_NORMAL, theme::FONT_BOLD, icon)
    }

    /// Display itself starting at the given Point.
    pub fn draw(&self, baseline: Point) -> i32 {
        common::key_value_icon(
            baseline,
            self.icon.clone(),
            self.label.clone(),
            self.label_font,
            self.value.clone(),
            self.value_font,
        )
    }
}

impl KeyValueIcon<StrBuffer> {
    /// New element with normal font for label and bold font for value.
    /// Also using the general `param` icon.
    pub fn normal_bold_param(label: StrBuffer, value: StrBuffer) -> Self {
        Self::normal_bold(label, value, Icon::new(theme::ICON_PARAM, "param".into()))
    }
}

/// Show at most three key-value-icon pairs on a single screen.
#[derive(Debug, Clone)]
pub struct KeyValueIconPage<T> {
    pairs: Vec<KeyValueIcon<T>, 3>,
    btn_layout: ButtonLayout<&'static str>,
    btn_actions: BtnActions,
}

impl<T> KeyValueIconPage<T>
where
    T: AsRef<str>,
{
    pub fn new(
        pairs: Vec<KeyValueIcon<T>, 3>,
        btn_layout: ButtonLayout<&'static str>,
        btn_actions: BtnActions,
    ) -> Self {
        Self {
            pairs,
            btn_layout,
            btn_actions,
        }
    }
}

impl<T> FlowPage for KeyValueIconPage<T>
where
    T: AsRef<str>,
    T: Clone,
{
    fn paint(&mut self, left_top: Point) {
        let x_start = left_top.x;
        let mut y_offset = left_top.y;

        // Draw all the pairs - maximum three, can be even just one or two.
        // Gradually incrementing the `y_offset` according to the drawn height.
        for pair in self.pairs.iter() {
            y_offset += pair.label_font.line_height();
            y_offset += pair.draw(Point::new(x_start, y_offset));
        }
    }

    fn btn_layout(&self) -> ButtonLayout<&'static str> {
        self.btn_layout.clone()
    }

    fn btn_actions(&self) -> BtnActions {
        self.btn_actions.clone()
    }
}

}
