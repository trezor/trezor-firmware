use crate::ui::{
    display::{Font, Icon},
    geometry::Point,
    model_tr::theme,
    util,
};
use heapless::{String, Vec};

use super::{common, ButtonLayout};

pub trait FlowPage {
    fn paint(&mut self);
    fn btn_layout(&self) -> ButtonLayout<&'static str>;
}

// TODO: consider using `dyn` instead of `enum` to allow
// for more components implementing `FlowPage`
// Alloc screen by GC .. gc alloc, new
// dyn... gc dyn obj component
// Vec<Gc<dyn FlowPage>, 2>...

#[derive(Clone, Debug)]
pub enum FlowPages<T> {
    RecipientAddress(RecipientAddressPage<T>),
    ConfirmSend(ConfirmSendPage<T>),
    ConfirmTotal(ConfirmTotalPage<T>),
}

impl<T> FlowPage for FlowPages<T>
where
    T: AsRef<str>,
{
    fn paint(&mut self) {
        match self {
            FlowPages::RecipientAddress(item) => item.paint(),
            FlowPages::ConfirmSend(item) => item.paint(),
            FlowPages::ConfirmTotal(item) => item.paint(),
        }
    }

    fn btn_layout(&self) -> ButtonLayout<&'static str> {
        match self {
            FlowPages::RecipientAddress(item) => item.btn_layout(),
            FlowPages::ConfirmSend(item) => item.btn_layout(),
            FlowPages::ConfirmTotal(item) => item.btn_layout(),
        }
    }
}

/// Page displaying recipient address.
#[derive(Debug, Clone)]
pub struct RecipientAddressPage<T> {
    pub address: T,
    pub btn_layout: ButtonLayout<&'static str>,
}

impl<T> RecipientAddressPage<T>
where
    T: AsRef<str>,
{
    pub fn new(address: T, btn_layout: ButtonLayout<&'static str>) -> Self {
        Self {
            address,
            btn_layout,
        }
    }
}

impl<T> FlowPage for RecipientAddressPage<T>
where
    T: AsRef<str>,
{
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

        let addr_str: String<50> = String::from(self.address.as_ref());
        let rows: Vec<&str, 8> = addr_str
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
pub struct ConfirmSendPage<T> {
    pub address: T,
    pub amount: T,
    pub btn_layout: ButtonLayout<&'static str>,
}

impl<T> ConfirmSendPage<T>
where
    T: AsRef<str>,
{
    pub fn new(address: T, amount: T, btn_layout: ButtonLayout<&'static str>) -> Self {
        Self {
            address,
            amount,
            btn_layout,
        }
    }
}

impl<T> FlowPage for ConfirmSendPage<T>
where
    T: AsRef<str>,
{
    fn paint(&mut self) {
        let y_offset = 12;
        common::display(Point::new(0, y_offset), "Send", theme::FONT_BOLD);

        // TODO: create a general ICON-KEY-VALUE component and use it here
        // (probably then it can be called directly from layout.rs?)

        common::icon_with_text(
            Point::new(0, 32),
            Icon::new(theme::ICON_USER, "user"),
            "Recipient",
            theme::FONT_NORMAL,
        );

        // Displaying just the left and right end of the address
        const CHARS_TO_SHOW: usize = 4;
        const ELLIPSIS: &str = " ... ";
        let trunc_addr: String<20> =
            util::ellipsise_text(self.address.as_ref(), CHARS_TO_SHOW, ELLIPSIS);
        common::display(Point::new(1, 48), &trunc_addr, theme::FONT_BOLD);

        common::icon_with_text(
            Point::new(0, 72),
            Icon::new(theme::ICON_AMOUNT, "amount"),
            "Amount",
            theme::FONT_NORMAL,
        );
        common::display(Point::new(1, 88), self.amount.as_ref(), theme::FONT_BOLD);
    }

    fn btn_layout(&self) -> ButtonLayout<&'static str> {
        self.btn_layout.clone()
    }
}

/// Confirm address and amount for single output.
#[derive(Debug, Clone)]
pub struct ConfirmTotalPage<T> {
    pub title: T,
    pub total_amount: T,
    pub fee_amount: T,
    pub fee_rate_amount: Option<T>,
    pub total_label: T,
    pub fee_label: T,
    pub btn_layout: ButtonLayout<&'static str>,
}

impl<T> ConfirmTotalPage<T>
where
    T: AsRef<str>,
{
    pub fn new(
        title: T,
        total_amount: T,
        fee_amount: T,
        fee_rate_amount: Option<T>,
        total_label: T,
        fee_label: T,
        btn_layout: ButtonLayout<&'static str>,
    ) -> Self {
        Self {
            title,
            total_amount,
            fee_amount,
            fee_rate_amount,
            total_label,
            fee_label,
            btn_layout,
        }
    }
}

impl<T> FlowPage for ConfirmTotalPage<T>
where
    T: AsRef<str>,
{
    fn paint(&mut self) {
        // TODO: create a general ICON-KEY-VALUE component and use it here
        // (probably then it can be called directly from layout.rs?)

        const X_START: i32 = 0;
        const LABEL_FONT: Font = theme::FONT_NORMAL;
        const KEY_FONT: Font = theme::FONT_BOLD;
        let param_icon = Icon::new(theme::ICON_PARAM, "param");

        // Title/header
        let y_offset = common::paint_header(Point::zero(), &self.title, None);

        // Total amount
        let new_y = y_offset + LABEL_FONT.line_height();
        let y_offset = common::key_value_icon(
            Point::new(X_START, new_y),
            param_icon,
            self.total_label.as_ref(),
            LABEL_FONT,
            self.total_amount.as_ref(),
            KEY_FONT,
        );

        // Fee amount
        let new_y = new_y + y_offset + LABEL_FONT.line_height();
        let y_offset = common::key_value_icon(
            Point::new(X_START, new_y),
            param_icon,
            self.fee_label.as_ref(),
            LABEL_FONT,
            self.fee_amount.as_ref(),
            KEY_FONT,
        );

        // Optional fee rate amount
        if let Some(fee_rate_amount) = &self.fee_rate_amount {
            let new_y = new_y + y_offset + LABEL_FONT.line_height();
            common::key_value_icon(
                Point::new(X_START, new_y),
                param_icon,
                "Fee rate:",
                LABEL_FONT,
                fee_rate_amount.as_ref(),
                KEY_FONT,
            );
        }
    }

    fn btn_layout(&self) -> ButtonLayout<&'static str> {
        self.btn_layout.clone()
    }
}
