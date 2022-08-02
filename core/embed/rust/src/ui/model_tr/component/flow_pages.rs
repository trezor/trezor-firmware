use crate::ui::{display::Icon, geometry::Point, model_tr::theme};
use heapless::{String, Vec};

use super::{common, ButtonLayout};

pub trait FlowPage {
    fn paint(&mut self);
    fn btn_layout(&self) -> ButtonLayout<&'static str>;
}

#[derive(Clone, Debug)]
pub enum FlowPages {
    RecipientAddress(RecipientAddressPage),
    ConfirmSend(ConfirmSendPage),
}

impl FlowPage for FlowPages {
    fn paint(&mut self) {
        match self {
            FlowPages::RecipientAddress(item) => item.paint(),
            FlowPages::ConfirmSend(item) => item.paint(),
        }
    }

    fn btn_layout(&self) -> ButtonLayout<&'static str> {
        match self {
            FlowPages::RecipientAddress(item) => item.btn_layout(),
            FlowPages::ConfirmSend(item) => item.btn_layout(),
        }
    }
}

/// Page displaying recipient address.
#[derive(Debug, Clone)]
pub struct RecipientAddressPage {
    // TODO: what is the maximum address length?
    pub address: String<100>,
    pub btn_layout: ButtonLayout<&'static str>,
}

impl RecipientAddressPage {
    pub fn new<T>(address: T, btn_layout: ButtonLayout<&'static str>) -> Self
    where
        T: AsRef<str>,
    {
        Self {
            address: String::from(address.as_ref()),
            btn_layout,
        }
    }
}

impl FlowPage for RecipientAddressPage {
    fn paint(&mut self) {
        common::icon_with_text(
            Point::new(0, 12),
            Icon::new(theme::ICON_USER, "user"),
            "Recipient",
            theme::FONT_NORMAL,
        );

        // Showing the address in chunks of 4 characters, with 3 chunks per line.
        // Putting two spaces between chunks on the same line.

        const CHUNK_SIZE: usize = 4;
        const CHUNKS_PER_PAGE: usize = 3;
        const ROW_CHARS: usize = CHUNK_SIZE * CHUNKS_PER_PAGE;

        let rows: Vec<&str, 8> = self
            .address
            .as_bytes()
            .chunks(ROW_CHARS)
            .map(|buf| unsafe { core::str::from_utf8_unchecked(buf) })
            .collect();

        for (row_id, row) in rows.iter().enumerate() {
            let mut buf: String<{ 2 * ROW_CHARS }> = String::new();
            for (ch_id, ch) in row.chars().enumerate() {
                buf.push(ch).unwrap();
                if ch_id % CHUNK_SIZE == CHUNK_SIZE - 1 {
                    buf.push(' ').unwrap();
                    buf.push(' ').unwrap();
                }
            }
            common::display(
                Point::new(1, 40 + theme::FONT_BOLD.line_height() * row_id as i32),
                buf.as_str(),
                theme::FONT_BOLD,
            );
        }
    }

    fn btn_layout(&self) -> ButtonLayout<&'static str> {
        self.btn_layout.clone()
    }
}

/// Confirm address and amount for single output.
#[derive(Debug, Clone)]
pub struct ConfirmSendPage {
    pub address: String<100>,
    // TODO: what is the maximum amount length?
    pub amount: String<25>,
    pub btn_layout: ButtonLayout<&'static str>,
}

impl ConfirmSendPage {
    pub fn new<T>(address: T, amount: T, btn_layout: ButtonLayout<&'static str>) -> Self
    where
        T: AsRef<str>,
    {
        Self {
            address: String::from(address.as_ref()),
            amount: String::from(amount.as_ref()),
            btn_layout,
        }
    }
}

impl FlowPage for ConfirmSendPage {
    fn paint(&mut self) {
        common::display(Point::new(0, 12), "Send", theme::FONT_BOLD);

        common::icon_with_text(
            Point::new(0, 32),
            Icon::new(theme::ICON_USER, "user"),
            "Recipient",
            theme::FONT_NORMAL,
        );

        // Displaying just the left and right end of the address

        const CHARS_TO_SHOW: usize = 4;
        const ELLIPSIS: &str = " ... ";

        let len = self.address.len();
        let start = self.address.get(0..CHARS_TO_SHOW).unwrap();
        let end = self.address.get((len - CHARS_TO_SHOW)..len).unwrap();
        let trunc_addr = build_string!(20, start, ELLIPSIS, end);
        common::display(Point::new(1, 48), &trunc_addr, theme::FONT_BOLD);

        common::icon_with_text(
            Point::new(0, 72),
            Icon::new(theme::ICON_AMOUNT, "amount"),
            "Amount",
            theme::FONT_NORMAL,
        );
        common::display(Point::new(1, 88), &self.amount, theme::FONT_BOLD);
    }

    fn btn_layout(&self) -> ButtonLayout<&'static str> {
        self.btn_layout.clone()
    }
}
