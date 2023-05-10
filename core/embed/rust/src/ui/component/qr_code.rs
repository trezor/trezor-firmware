use heapless::String;
use qrcodegen::{QrCode, QrCodeEcc, Version};

use crate::{
    error::Error,
    ui::{
        component::{Component, Event, EventCtx, Never},
        constant,
        display::{pixeldata, pixeldata_dirty, rect_fill_rounded, set_window, Color},
        geometry::{Insets, Offset, Rect},
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

    fn draw(qr: &QrCode, area: Rect, border: i16, scale: i16) {
        if border > 0 {
            rect_fill_rounded(
                area.inset(Insets::uniform(-border)),
                LIGHT,
                DARK,
                CORNER_RADIUS,
            );
        }

        let window = area.clamp(constant::screen());
        set_window(window);

        for y in window.y0..window.y1 {
            for x in window.x0..window.x1 {
                let rx = (x - window.x0) / scale;
                let ry = (y - window.y0) / scale;
                if qr.get_module(rx.into(), ry.into()) {
                    pixeldata(DARK);
                } else {
                    pixeldata(LIGHT);
                };
            }
        }
        pixeldata_dirty();
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

    fn paint(&mut self) {
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
        let size = qr.size() as i16;

        let avail_space = self.area.width().min(self.area.height());
        let avail_space = avail_space - 2 * self.border;
        let scale = avail_space / size;
        assert!((1..=10).contains(&scale));

        let area = Rect::from_center_and_size(self.area.center(), Offset::uniform(size * scale));
        Self::draw(&qr, area, self.border, scale);
    }

    #[cfg(feature = "ui_bounds")]
    fn bounds(&self, sink: &mut dyn FnMut(Rect)) {
        sink(self.area)
    }
}

#[cfg(feature = "ui_debug")]
impl crate::trace::Trace for Qr {
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.component("Qr");
        t.string("text", self.text.as_ref());
    }
}
