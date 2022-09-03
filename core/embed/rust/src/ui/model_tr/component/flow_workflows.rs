//! Implementing specific workflows that are then called in `layout.rs`.
//! Each workflow is returning a `FlowPageMaker` (page/screen) on demand
//! based on the current page in `flow.rs`.
//! Before, when `layout.rs` was defining a `heapless::Vec` of `FlowPageMaker`s,
//! it was a very stack-expensive operation and StackOverflow was encountered.
//! With this "lazy-loading" approach (creating each page on demand) we can
//! have theoretically unlimited number of pages without triggering SO.
//! (Currently only the current page is stored on stack - in
//! `Flow::current_page`.)

use crate::{micropython::buffer::StrBuffer, time::Duration, ui::model_tr::theme};

use super::{ButtonActions, ButtonDetails, ButtonLayout, FlowPageMaker};

// TODO: consider having N and M const - one for amount
// of pages (instead of len) and second for the FlowPageMaker<M>
// TODO: look into inputting closures/functions directly, so we can
// define the layout in layout.rs and we do not need to have multiple instances
// of FlowPageGetter
pub trait GetFlowPageMaker {
    fn get_page<const M: usize>(&self, page: u8) -> FlowPageMaker<M>;
    fn length(&self) -> usize;
}

pub enum FlowPageGetter {
    Tutorial(TutorialFlow),
    PinConfirmAction(PinConfirmActionFlow),
    ConfirmTotal(ConfirmTotalFlow),
    ConfirmOutput(ConfirmOutputFlow),
}

impl GetFlowPageMaker for FlowPageGetter {
    fn get_page<const M: usize>(&self, page: u8) -> FlowPageMaker<M> {
        match self {
            FlowPageGetter::Tutorial(getter) => getter.get_page(page),
            FlowPageGetter::PinConfirmAction(getter) => getter.get_page(page),
            FlowPageGetter::ConfirmTotal(getter) => getter.get_page(page),
            FlowPageGetter::ConfirmOutput(getter) => getter.get_page(page),
        }
    }
    fn length(&self) -> usize {
        match self {
            FlowPageGetter::Tutorial(getter) => getter.length(),
            FlowPageGetter::PinConfirmAction(getter) => getter.length(),
            FlowPageGetter::ConfirmTotal(getter) => getter.length(),
            FlowPageGetter::ConfirmOutput(getter) => getter.length(),
        }
    }
}

pub struct TutorialFlow;
impl GetFlowPageMaker for TutorialFlow {
    fn get_page<const M: usize>(&self, page: u8) -> FlowPageMaker<M> {
        // Lazy-loaded list of screens to show, with custom content,
        // buttons and actions triggered by these buttons.
        // Cancelling the first screen will point to the last one,
        // which asks for confirmation whether user wants to
        // really cancel the tutorial.
        let screen = match page {
            // title, text, btn_layout, btn_actions
            0 => (
                "Hello!",
                "Welcome to Trezor.\n\n\nPress right to continue.",
                ButtonLayout::cancel_and_arrow(),
                ButtonActions::last_next(),
            ),
            1 => (
                "Basics",
                "Use Trezor by clicking left & right.\n\rPress right to continue.",
                ButtonLayout::left_right_arrows(),
                ButtonActions::prev_next(),
            ),
            2 => (
                "Confirm",
                "Press both left & right at the same time to confirm.",
                ButtonLayout::new(
                    Some(ButtonDetails::left_arrow_icon()),
                    Some(ButtonDetails::armed_text("CONFIRM")),
                    None,
                ),
                ButtonActions::prev_next_with_middle(),
            ),
            3 => (
                "Hold to confirm",
                "Press & hold right to approve important operations.",
                ButtonLayout::new(
                    Some(ButtonDetails::left_arrow_icon()),
                    None,
                    Some(
                        ButtonDetails::text("HOLD TO CONFIRM")
                            .with_duration(Duration::from_millis(2000)),
                    ),
                ),
                ButtonActions::prev_next(),
            ),
            // TODO: merge these two scrolls into one, with using a scrollbar
            4 => (
                "Screen scroll",
                "Press right to scroll down to read all content when text doesn't...",
                ButtonLayout::new(
                    Some(ButtonDetails::left_arrow_icon()),
                    None,
                    Some(ButtonDetails::down_arrow_icon_wide()),
                ),
                ButtonActions::prev_next(),
            ),
            5 => (
                "Screen scroll",
                "fit on one screen. Press left to scroll up.",
                ButtonLayout::new(
                    Some(ButtonDetails::up_arrow_icon_wide()),
                    None,
                    Some(ButtonDetails::text("CONFIRM")),
                ),
                ButtonActions::prev_next(),
            ),
            6 => (
                "Congrats!",
                "You're ready to use Trezor.",
                ButtonLayout::new(
                    Some(ButtonDetails::text("AGAIN")),
                    None,
                    Some(ButtonDetails::text("FINISH")),
                ),
                ButtonActions::beginning_confirm(),
            ),
            7 => (
                "Skip tutorial?",
                "Sure you want to skip the tutorial?",
                ButtonLayout::new(
                    Some(ButtonDetails::left_arrow_icon()),
                    None,
                    Some(ButtonDetails::text("CONFIRM")),
                ),
                ButtonActions::beginning_cancel(),
            ),
            _ => unreachable!(),
        };

        FlowPageMaker::new(screen.2.clone(), screen.3.clone())
            .text_bold(screen.0.into())
            .newline()
            .newline_half()
            .text_normal(screen.1.into())
    }

    fn length(&self) -> usize {
        8
    }
}

pub struct PinConfirmActionFlow {
    action: StrBuffer,
}
impl PinConfirmActionFlow {
    pub fn new(action: StrBuffer) -> Self {
        Self { action }
    }
}
impl GetFlowPageMaker for PinConfirmActionFlow {
    fn get_page<const M: usize>(&self, page: u8) -> FlowPageMaker<M> {
        let screen = match page {
            // title, text, btn_layout, btn_actions
            // NOTE: doing the newlines manually to look exactly same
            // as in the design.
            0 => (
                "PIN settings".into(),
                "PIN should\ncontain at\nleast four\ndigits",
                ButtonLayout::cancel_and_text("GOT IT"),
                ButtonActions::cancel_next(),
            ),
            1 => (
                self.action.clone(),
                "You'll use\nthis PIN to\naccess this\ndevice.",
                ButtonLayout::cancel_and_htc_text("HOLD TO CONFIRM", Duration::from_millis(1000)),
                ButtonActions::cancel_confirm(),
            ),
            _ => unreachable!(),
        };

        FlowPageMaker::new(screen.2.clone(), screen.3.clone())
            .text_bold(screen.0.clone())
            .newline()
            .newline_half()
            .text_normal(screen.1.into())
    }

    fn length(&self) -> usize {
        2
    }
}

pub struct ConfirmTotalFlow {
    total_amount: StrBuffer,
    fee_amount: StrBuffer,
    fee_rate_amount: Option<StrBuffer>,
    total_label: StrBuffer,
    fee_label: StrBuffer,
}
impl ConfirmTotalFlow {
    pub fn new(
        total_amount: StrBuffer,
        fee_amount: StrBuffer,
        fee_rate_amount: Option<StrBuffer>,
        total_label: StrBuffer,
        fee_label: StrBuffer,
    ) -> Self {
        Self {
            total_amount,
            fee_amount,
            fee_rate_amount,
            total_label,
            fee_label,
        }
    }
}
impl GetFlowPageMaker for ConfirmTotalFlow {
    fn get_page<const M: usize>(&self, page: u8) -> FlowPageMaker<M> {
        // One page with 2 or 3 pairs `icon + label + text`
        assert!(page == 0);

        let btn_layout = ButtonLayout::new(
            Some(ButtonDetails::cancel_icon()),
            None,
            Some(ButtonDetails::text("HOLD TO SEND").with_duration(Duration::from_secs(2))),
        );
        let btn_actions = ButtonActions::cancel_confirm();

        let mut page = FlowPageMaker::new(btn_layout, btn_actions)
            .icon_label_text(
                theme::ICON_PARAM,
                self.total_label.clone(),
                self.total_amount.clone(),
            )
            .newline()
            .icon_label_text(
                theme::ICON_PARAM,
                self.fee_label.clone(),
                self.fee_amount.clone(),
            );

        if let Some(fee_rate_amount) = &self.fee_rate_amount {
            page = page.newline().icon_label_text(
                theme::ICON_PARAM,
                "Fee rate".into(),
                fee_rate_amount.clone(),
            )
        }
        page
    }

    fn length(&self) -> usize {
        1
    }
}

pub struct ConfirmOutputFlow {
    address: StrBuffer,
    truncated_address: StrBuffer,
    amount: StrBuffer,
}
impl ConfirmOutputFlow {
    pub fn new(address: StrBuffer, truncated_address: StrBuffer, amount: StrBuffer) -> Self {
        Self {
            address,
            truncated_address,
            amount,
        }
    }
}
impl GetFlowPageMaker for ConfirmOutputFlow {
    fn get_page<const M: usize>(&self, page: u8) -> FlowPageMaker<M> {
        // Showing two screens - the recipient address and summary confirmation
        match page {
            0 => {
                // `icon + label + address`
                let btn_layout = ButtonLayout::new(
                    Some(ButtonDetails::cancel_icon()),
                    None,
                    Some(ButtonDetails::text("CONTINUE")),
                );
                let btn_actions = ButtonActions::cancel_next();
                FlowPageMaker::new(btn_layout, btn_actions).icon_label_text(
                    theme::ICON_USER,
                    "Recipient".into(),
                    self.address.clone(),
                )
            }
            1 => {
                // 2 pairs `icon + label + text`
                let btn_layout = ButtonLayout::new(
                    Some(ButtonDetails::cancel_icon()),
                    None,
                    Some(
                        ButtonDetails::text("HOLD TO CONFIRM")
                            .with_duration(Duration::from_secs(2)),
                    ),
                );
                let btn_actions = ButtonActions::cancel_confirm();

                FlowPageMaker::new(btn_layout, btn_actions)
                    .icon_label_text(
                        theme::ICON_USER,
                        "Recipient".into(),
                        self.truncated_address.clone(),
                    )
                    .newline()
                    .icon_label_text(theme::ICON_AMOUNT, "Amount".into(), self.amount.clone())
            }
            _ => unreachable!(),
        }
    }

    fn length(&self) -> usize {
        2
    }
}
