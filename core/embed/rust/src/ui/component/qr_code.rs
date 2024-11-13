use heapless::String;
use qrcodegen::{QrCode, QrCodeEcc, Version};

use crate::{
    error::Error,
    ui::{
        component::{Component, Event, EventCtx, Never},
        display::Color,
        geometry::{Offset, Rect},
        shape,
        shape::Renderer,
    },
};

const NVERSIONS: usize = 10; // range of versions (=capacities) that we support
const THRESHOLDS_BINARY: [usize; NVERSIONS] = [14, 26, 42, 62, 84, 106, 122, 152, 180, 213];
const THRESHOLDS_ALPHANUM: [usize; NVERSIONS] = [20, 38, 61, 90, 122, 154, 178, 221, 262, 311];
const ALPHANUMERIC_CHARSET: &str = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ $%*+-./:";
const MAX_DATA: usize = THRESHOLDS_ALPHANUM[THRESHOLDS_ALPHANUM.len() - 1];

const QR_MAX_VERSION: Version = Version::new(NVERSIONS as u8 - 1);
const CORNER_RADIUS: u8 = 4;

const DARK: Color = Color::rgb(0, 0, 0);
const LIGHT: Color = Color::rgb(0xff, 0xff, 0xff);

pub struct Qr {
    text: String<MAX_DATA>,
    border: i16,
    area: Rect,
}

impl Qr {
    pub fn new<T>(text: T, case_sensitive: bool) -> Result<Self, Error>
    where
        T: AsRef<str>,
    {
        let indata = text.as_ref();
        let mut s = String::new();

        if !case_sensitive
            && Self::is_smaller_for_alphanumeric(indata.len())
            && Self::is_alphanumeric_after_conversion(indata)
        {
            for c in indata.chars() {
                s.push(c.to_ascii_uppercase())
                    .map_err(|_| Error::OutOfRange)?;
            }
        } else {
            s.push_str(indata).map_err(|_| Error::OutOfRange)?;
        }

        Ok(Self {
            text: s,
            border: 0,
            area: Rect::zero(),
        })
    }

    pub fn with_border(mut self, border: i16) -> Self {
        self.border = border;
        self
    }

    fn is_alphanumeric_after_conversion(data: &str) -> bool {
        data.chars()
            .all(|c| ALPHANUMERIC_CHARSET.contains(c.to_ascii_uppercase()))
    }

    fn is_smaller_for_alphanumeric(len: usize) -> bool {
        for version in 0..NVERSIONS {
            if len <= THRESHOLDS_ALPHANUM[version] {
                return len > THRESHOLDS_BINARY[version];
            }
        }
        false
    }
}

impl Component for Qr {
    type Msg = Never;

    fn place(&mut self, bounds: Rect) -> Rect {
        self.area = bounds;
        bounds
    }

    fn event(&mut self, _ctx: &mut EventCtx, _event: Event) -> Option<Self::Msg> {
        None
    }

    fn render<'s>(&'s self, target: &mut impl Renderer<'s>) {
        let mut outbuffer = [0u8; QR_MAX_VERSION.buffer_len()];
        let mut tempbuffer = [0u8; QR_MAX_VERSION.buffer_len()];

        let qr = QrCode::encode_text(
            self.text.as_ref(),
            &mut tempbuffer,
            &mut outbuffer,
            QrCodeEcc::Medium,
            Version::MIN,
            QR_MAX_VERSION,
            None,
            true,
        );
        let qr = unwrap!(qr);

        let scale = (self.area.width().min(self.area.height()) - self.border) / (qr.size() as i16);
        let side = scale * qr.size() as i16;
        let qr_area = Rect::from_center_and_size(self.area.center(), Offset::uniform(side));

        if self.border > 0 {
            shape::Bar::new(qr_area.expand(self.border))
                .with_bg(LIGHT)
                .with_radius(CORNER_RADIUS as i16 + 1) // !@# + 1 to fix difference on TR
                .render(target);
        }

        shape::QrImage::new(qr_area, &qr)
            .with_fg(LIGHT)
            .with_bg(DARK)
            .render(target);
    }
}

#[cfg(feature = "ui_debug")]
impl crate::trace::Trace for Qr {
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.component("Qr");
        t.string("text", self.text.as_str().into());
    }
}

#[cfg(feature = "micropython")]
mod micropython {
    use crate::{error::Error, micropython::obj::Obj, ui::layout::obj::ComponentMsgObj};
    impl ComponentMsgObj for super::Qr {
        fn msg_try_into_obj(&self, _msg: Self::Msg) -> Result<Obj, Error> {
            unreachable!();
        }
    }
}
