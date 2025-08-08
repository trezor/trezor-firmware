use crate::{
    strutil::TString,
    ui::{
        component::{Component, Event, EventCtx, Label},
        event::BLEEvent,
        geometry::{Alignment2D, Insets, Offset, Rect},
        shape::{self, Renderer},
    },
};

use super::{
    super::{
        component::{Button, FuelGauge},
        constant::SCREEN,
        theme,
    },
    pairing_mode::PairingMsg,
    BldActionBar, BldActionBarMsg, BldHeader, BldHeaderMsg,
};

/// Full-screen component for the wireless setup screen. It shows instructions
/// for the user and QR code to download the Trezor Suite app.
pub struct WirelessSetupScreen {
    /// Header with the device name
    header: BldHeader<'static>,
    /// Instruction text for the user
    instruction: Label<'static>,
    /// Area for the QR code
    qr_area: Rect,
    /// Action bar to invoke more info
    action_bar: BldActionBar,
    /// More info section that can be toggled
    more_info: MoreInfo<'static>,
    /// Flag to indicate if the more info section is currently showing
    more_info_showing: bool,
}

struct MoreInfo<'a> {
    header: BldHeader<'a>,
    instruction_primary: Label<'a>,
    instruction_secondary: Label<'a>,
    action_bar: BldActionBar,
}

impl WirelessSetupScreen {
    pub fn new(name: TString<'static>) -> Self {
        let instruction = Label::left_aligned(
            "Get the Trezor Suite app to begin setup.".into(),
            theme::TEXT_NORMAL,
        );
        let btn = Button::with_text("More info".into())
            .styled(theme::bootloader::button_bld_initial_setup())
            .with_gradient(theme::Gradient::DefaultGrey);
        let btn_more_info =
            Button::with_text("More at trezor.io/start".into()).initially_enabled(false);
        let more_info = MoreInfo {
            header: BldHeader::new(TString::empty())
                .with_fuel_gauge(Some(FuelGauge::always()))
                .with_close_button(),
            instruction_primary: Label::left_aligned(
                "The Trezor Suite app is required to set up your Trezor.".into(),
                theme::TEXT_NORMAL,
            ),
            instruction_secondary: Label::left_aligned(
                "Setup via USB-C isn't supported on Apple devices running iOS or iPadOS.".into(),
                theme::TEXT_SMALL_GREY,
            ),
            action_bar: BldActionBar::new_single(btn_more_info),
        };

        Self {
            header: BldHeader::new(name),
            instruction,
            qr_area: Rect::zero(),
            action_bar: BldActionBar::new_single(btn),
            more_info,
            more_info_showing: false,
        }
    }

    fn render_qr_code<'s>(&'s self, target: &mut impl Renderer<'s>) {
        if self.qr_area.is_empty() {
            return;
        }

        let qr_code_size = theme::bootloader::ICON_QR_TREZOR_IO_SETUP.toif.width();
        let qr_code_pad_width = 11;
        let pad_area = Rect::snap(
            self.qr_area.center(),
            Offset::uniform(qr_code_size + qr_code_pad_width),
            Alignment2D::CENTER,
        );

        shape::Bar::new(pad_area)
            .with_fg(theme::WHITE)
            .with_bg(theme::WHITE)
            .with_radius(4)
            .render(target);
        shape::ToifImage::new(
            pad_area.center(),
            theme::bootloader::ICON_QR_TREZOR_IO_SETUP.toif,
        )
        .with_align(Alignment2D::CENTER)
        .with_fg(theme::WHITE)
        .with_bg(theme::BLACK)
        .render(target);
    }
}

impl Component for WirelessSetupScreen {
    type Msg = PairingMsg;

    fn place(&mut self, _bounds: Rect) -> Rect {
        let (header_area, rest) = SCREEN.split_top(theme::HEADER_HEIGHT);
        let (content_area, action_bar_area) = rest.split_bottom(theme::ACTION_BAR_HEIGHT);
        // let content_area = content_area.inset(theme::SIDE_INSETS);
        let content_area = content_area.inset(Insets::sides(20));

        self.header.place(header_area);
        self.instruction.place(content_area);
        self.action_bar.place(action_bar_area);
        // remaining space is used for the QR code which will be rendered in the center
        self.qr_area = content_area.inset(Insets::top(
            self.instruction.text_height(content_area.width()) + 32,
        ));

        // Place the toggled MoreInfo sections accordingly
        self.more_info.header.place(header_area);
        self.more_info.instruction_primary.place(content_area);
        self.more_info.instruction_secondary.place(
            content_area.inset(Insets::top(
                self.more_info
                    .instruction_primary
                    .text_height(content_area.width())
                    + 32,
            )),
        );
        self.more_info.action_bar.place(action_bar_area);
        SCREEN
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        if let Some(BldActionBarMsg::Confirmed) = self.action_bar.event(ctx, event) {
            self.more_info_showing = true;
        }
        if let Some(BldHeaderMsg::Cancelled) = self.more_info.header.event(ctx, event) {
            self.more_info_showing = false;
        }

        if let Event::BLE(BLEEvent::PairingRequest(code)) = event {
            return Some(PairingMsg::Pairing(code));
        }
        if let Event::BLE(BLEEvent::PairingCanceled) = event {
            return Some(PairingMsg::Cancel);
        }
        if let Event::BLE(BLEEvent::Disconnected) = event {
            return Some(PairingMsg::Cancel);
        }
        None
    }

    fn render<'s>(&'s self, target: &mut impl Renderer<'s>) {
        if self.more_info_showing {
            self.more_info.header.render(target);
            self.more_info.instruction_primary.render(target);
            self.more_info.instruction_secondary.render(target);
            self.more_info.action_bar.render(target);
        } else {
            self.header.render(target);
            self.instruction.render(target);
            self.action_bar.render(target);
            self.render_qr_code(target);
        }
    }
}
